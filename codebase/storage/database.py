"""
SQLite database — lưu bài đăng, phản hồi, và hồ sơ người dùng.

Dùng aiosqlite cho async. Schema tự tạo khi khởi động.
"""
import json
import pickle
from datetime import datetime, timezone
from pathlib import Path

import aiosqlite
import numpy as np

import config

# ── Schema ───────────────────────────────────────────────

_SCHEMA = """
CREATE TABLE IF NOT EXISTS posts (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    discord_msg_id  TEXT UNIQUE NOT NULL,
    channel_id      TEXT NOT NULL,
    author_id       TEXT NOT NULL,
    author_name     TEXT,
    title           TEXT,           -- Tiêu đề thread forum
    content         TEXT,
    fetched_content TEXT,
    summary         TEXT,
    tags            TEXT,           -- JSON array, e.g. '["AI","Python"]'
    embedding       BLOB,           -- pickled numpy array
    digest_msg_id   TEXT,           -- ID của tin nhắn digest đã đăng
    jump_url        TEXT,           -- link nhảy tới tin gốc
    created_at      TEXT NOT NULL,
    processed_at    TEXT
);

CREATE TABLE IF NOT EXISTS reactions (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         TEXT NOT NULL,
    post_id         INTEGER NOT NULL REFERENCES posts(id),
    reaction_type   TEXT NOT NULL,  -- 'like' | 'save' | 'skip'
    created_at      TEXT NOT NULL,
    UNIQUE(user_id, post_id, reaction_type)
);

CREATE TABLE IF NOT EXISTS user_profiles (
    user_id         TEXT PRIMARY KEY,
    interest_tags   TEXT NOT NULL DEFAULT '{}',  -- JSON: {"tag": score}
    total_reactions INTEGER NOT NULL DEFAULT 0,
    updated_at      TEXT
);

CREATE INDEX IF NOT EXISTS idx_posts_discord_msg ON posts(discord_msg_id);
CREATE INDEX IF NOT EXISTS idx_reactions_user    ON reactions(user_id);
CREATE INDEX IF NOT EXISTS idx_reactions_post    ON reactions(post_id);
"""


class Database:
    """Async wrapper quanh SQLite."""

    def __init__(self, db_path: Path | None = None):
        self.db_path = db_path or config.DB_PATH
        self._conn: aiosqlite.Connection | None = None

    async def connect(self):
        """Mở kết nối và tạo schema nếu chưa có."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = await aiosqlite.connect(str(self.db_path))
        self._conn.row_factory = aiosqlite.Row
        await self._conn.executescript(_SCHEMA)
        # Migration: thêm cột title nếu DB cũ chưa có
        try:
            await self._conn.execute("ALTER TABLE posts ADD COLUMN title TEXT")
        except Exception:
            pass  # Đã có rồi
        await self._conn.commit()

    async def close(self):
        if self._conn:
            await self._conn.close()

    # ── Posts ─────────────────────────────────────────────

    async def post_exists(self, discord_msg_id: str) -> bool:
        """Chống trùng: đã xử lý bài này chưa?"""
        async with self._conn.execute(
            "SELECT 1 FROM posts WHERE discord_msg_id = ?", (discord_msg_id,)
        ) as cur:
            return await cur.fetchone() is not None

    async def save_post(
        self,
        *,
        discord_msg_id: str,
        channel_id: str,
        author_id: str,
        author_name: str,
        content: str,
        fetched_content: str | None,
        summary: str | None,
        tags: list[str],
        embedding: np.ndarray | None,
        jump_url: str,
        created_at: datetime,
        title: str = "",
    ) -> int:
        """Lưu bài mới, trả về post ID. summary có thể None (batch mode)."""
        emb_blob = pickle.dumps(embedding) if embedding is not None else None
        async with self._conn.execute(
            """INSERT INTO posts
               (discord_msg_id, channel_id, author_id, author_name, title,
                content, fetched_content, summary, tags, embedding,
                jump_url, created_at, processed_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                discord_msg_id,
                channel_id,
                author_id,
                author_name,
                title,
                content,
                fetched_content,
                summary,
                json.dumps(tags, ensure_ascii=False) if tags else '[]',
                emb_blob,
                jump_url,
                created_at.isoformat(),
                None,  # processed_at = None — chưa xử lý AI
            ),
        ) as cur:
            post_id = cur.lastrowid
        await self._conn.commit()
        return post_id

    async def set_digest_msg_id(self, post_id: int, digest_msg_id: str):
        """Ghi lại ID tin nhắn digest đã đăng."""
        await self._conn.execute(
            "UPDATE posts SET digest_msg_id = ? WHERE id = ?",
            (digest_msg_id, post_id),
        )
        await self._conn.commit()

    async def get_pending_posts(self) -> list[dict]:
        """Lấy bài chưa đăng digest (digest_msg_id IS NULL, processed_at IS NULL)."""
        async with self._conn.execute(
            "SELECT * FROM posts WHERE digest_msg_id IS NULL "
            "AND processed_at IS NULL ORDER BY created_at ASC"
        ) as cur:
            rows = await cur.fetchall()
        return [dict(r) for r in rows]

    async def update_post_ai_results(
        self, post_id: int, summary: str, tags: list[str],
        embedding: np.ndarray | None,
    ):
        """Cập nhật kết quả AI (summary, tags, embedding) cho bài đã collect."""
        emb_blob = pickle.dumps(embedding) if embedding is not None else None
        await self._conn.execute(
            "UPDATE posts SET summary = ?, tags = ?, embedding = ?, "
            "processed_at = ? WHERE id = ?",
            (
                summary,
                json.dumps(tags, ensure_ascii=False),
                emb_blob,
                datetime.now(timezone.utc).isoformat(),
                post_id,
            ),
        )
        await self._conn.commit()

    async def mark_skipped(self, post_id: int):
        """\u0110\u00e1nh d\u1ea5u b\u00e0i \u0111\u00e3 b\u1ecf qua (qu\u00e1 c\u0169)."""
        await self._conn.execute(
            "UPDATE posts SET processed_at = ?, summary = ? WHERE id = ?",
            (datetime.now(timezone.utc).isoformat(), '[Bo qua - qua cu]', post_id),
        )
        await self._conn.commit()

    async def get_post(self, post_id: int) -> dict | None:
        async with self._conn.execute(
            "SELECT * FROM posts WHERE id = ?", (post_id,)
        ) as cur:
            row = await cur.fetchone()
            return dict(row) if row else None

    async def get_all_posts_with_embeddings(self) -> list[dict]:
        """Lấy tất cả bài có embedding (cho semantic search)."""
        async with self._conn.execute(
            "SELECT id, summary, tags, embedding, jump_url, author_name, created_at "
            "FROM posts WHERE embedding IS NOT NULL ORDER BY created_at DESC"
        ) as cur:
            rows = await cur.fetchall()
        results = []
        for row in rows:
            d = dict(row)
            d["embedding"] = pickle.loads(d["embedding"])
            d["tags"] = json.loads(d["tags"])
            results.append(d)
        return results

    async def get_recent_posts(self, limit: int = 50) -> list[dict]:
        """Lấy bài gần nhất (chỉ bài đã xử lý AI)."""
        async with self._conn.execute(
            "SELECT id, title, content, summary, tags, jump_url, author_name, created_at "
            "FROM posts WHERE summary IS NOT NULL "
            "ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ) as cur:
            rows = await cur.fetchall()
        return [dict(r) | {"tags": json.loads(dict(r)["tags"])} for r in rows]

    # ── Reactions ────────────────────────────────────────

    async def save_reaction(
        self, *, user_id: str, post_id: int, reaction_type: str
    ):
        """Lưu phản hồi (upsert)."""
        await self._conn.execute(
            """INSERT INTO reactions (user_id, post_id, reaction_type, created_at)
               VALUES (?, ?, ?, ?)
               ON CONFLICT(user_id, post_id, reaction_type) DO UPDATE
               SET created_at = excluded.created_at""",
            (user_id, post_id, reaction_type, datetime.now(timezone.utc).isoformat()),
        )
        await self._conn.commit()

    async def get_user_reactions(self, user_id: str) -> list[dict]:
        async with self._conn.execute(
            """SELECT r.*, COALESCE(p.tags, '[]') as tags FROM reactions r
               LEFT JOIN posts p ON r.post_id = p.id
               WHERE r.user_id = ?
               ORDER BY r.created_at DESC""",
            (user_id,),
        ) as cur:
            rows = await cur.fetchall()
        return [dict(r) | {"tags": json.loads(dict(r)["tags"])} for r in rows]

    async def get_post_reaction_counts(self, post_id: int) -> dict[str, int]:
        """Đếm reactions theo loại cho một bài."""
        async with self._conn.execute(
            "SELECT reaction_type, COUNT(*) as cnt FROM reactions "
            "WHERE post_id = ? GROUP BY reaction_type",
            (post_id,),
        ) as cur:
            rows = await cur.fetchall()
        return {row["reaction_type"]: row["cnt"] for row in rows}

    async def get_user_skipped_post_ids(self, user_id: str) -> set[int]:
        """Lấy danh sách post_id mà user đã bấm 'Bỏ qua'."""
        async with self._conn.execute(
            "SELECT post_id FROM reactions WHERE user_id = ? AND reaction_type = 'skip'",
            (user_id,),
        ) as cur:
            rows = await cur.fetchall()
        return {row["post_id"] for row in rows}

    # ── User Profiles ────────────────────────────────────

    async def get_user_profile(self, user_id: str) -> dict[str, float]:
        """Lấy interest tags scores, trả {} nếu chưa có."""
        async with self._conn.execute(
            "SELECT interest_tags FROM user_profiles WHERE user_id = ?",
            (user_id,),
        ) as cur:
            row = await cur.fetchone()
        if row:
            return json.loads(row["interest_tags"])
        return {}

    async def update_user_profile(
        self, user_id: str, tag: str, delta: float
    ):
        """Cập nhật score cho một tag trong hồ sơ."""
        profile = await self.get_user_profile(user_id)
        profile[tag] = profile.get(tag, 0.0) + delta
        now = datetime.now(timezone.utc).isoformat()
        await self._conn.execute(
            """INSERT INTO user_profiles (user_id, interest_tags, total_reactions, updated_at)
               VALUES (?, ?, 1, ?)
               ON CONFLICT(user_id) DO UPDATE SET
                   interest_tags = excluded.interest_tags,
                   total_reactions = total_reactions + 1,
                   updated_at = excluded.updated_at""",
            (user_id, json.dumps(profile, ensure_ascii=False), now),
        )
        await self._conn.commit()
