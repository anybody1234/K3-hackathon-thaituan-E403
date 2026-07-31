"""
/foryou — gợi ý bài cá nhân hóa (ephemeral).

Xếp hạng bài theo: tag_match × recency × popularity.
Kết quả chỉ người gọi lệnh mới thấy (ephemeral message).
Kèm buttons để thu phản hồi.
"""
import json
import logging
from datetime import datetime, timezone

import discord
from discord import app_commands

import config
from storage.database import Database
from ui.digest_embed import create_foryou_embed

log = logging.getLogger(__name__)

# ── Trọng số ranking ────────────────────────────────────
WEIGHT_TAG_MATCH = 0.5
WEIGHT_RECENCY = 0.3
WEIGHT_POPULARITY = 0.2
FORYOU_LIMIT = 3  # Chỉ hiển thị 3 bài gợi ý


def setup_foryou_command(tree: app_commands.CommandTree, db: Database):
    """Đăng ký slash command /foryou."""

    @tree.command(
        name="foryou",
        description="Xem danh sách bài chia sẻ được gợi ý riêng cho bạn",
    )
    async def foryou_command(interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        try:
            user_id = str(interaction.user.id)
            user_name = interaction.user.display_name

            # ① Lấy hồ sơ sở thích
            profile = await db.get_user_profile(user_id)

            # ② Lấy bài gần đây
            posts = await db.get_recent_posts(limit=20)
            if not posts:
                await interaction.followup.send(
                    "📭 Chưa có bài nào. Hãy chia sẻ bài đầu tiên!",
                    ephemeral=True,
                )
                return

            # ② b. Lọc bỏ bài user đã skip
            skipped_ids = await db.get_user_skipped_post_ids(user_id)
            if skipped_ids:
                posts = [p for p in posts if p["id"] not in skipped_ids]
                log.info("Loai %d bai da skip cho user %s", len(skipped_ids), user_id)

            if not posts:
                await interaction.followup.send(
                    "📭 Bạn đã bỏ qua hết bài rồi! Hãy chờ bài mới.",
                    ephemeral=True,
                )
                return

            # ③ Xếp hạng
            if profile:
                ranked = _rank_posts(posts, profile)
            else:
                # Cold start: chưa có profile → trả bài mới nhất
                ranked = posts[:FORYOU_LIMIT]
                log.info("User %s chưa có profile, dùng fallback mới nhất", user_id)

            if not ranked:
                await interaction.followup.send(
                    "🤷 Không tìm được bài phù hợp. Hãy tương tác thêm để bot hiểu sở thích của bạn!",
                    ephemeral=True,
                )
                return

            # ④ Tạo embed
            embed = create_foryou_embed(ranked[:FORYOU_LIMIT], user_name)

            await interaction.followup.send(embed=embed, ephemeral=True)
            log.info(
                "/foryou cho %s: %d bài, profile %d tags",
                user_name, len(ranked[:FORYOU_LIMIT]), len(profile),
            )

        except Exception as e:
            log.error("Lỗi /foryou: %s", e)
            await interaction.followup.send(
                "⚠️ Có lỗi xảy ra. Thử lại sau.", ephemeral=True
            )


def _rank_posts(
    posts: list[dict],
    profile: dict[str, float],
) -> list[dict]:
    """
    Xếp hạng bài theo hồ sơ sở thích.

    Score = α × tag_match + β × recency + γ × popularity
    """
    if not profile:
        return posts

    now = datetime.now(timezone.utc)
    scored = []

    for post in posts:
        tags = post.get("tags", [])

        # Tag match: tổng score của các tag khớp
        tag_score = sum(profile.get(tag, 0) for tag in tags)
        # Normalize
        max_possible = max(profile.values()) * len(tags) if profile else 1
        tag_score_norm = tag_score / max_possible if max_possible > 0 else 0

        # Recency: bài mới hơn → score cao hơn (decay theo ngày)
        try:
            created = datetime.fromisoformat(post["created_at"])
            if created.tzinfo is None:
                created = created.replace(tzinfo=timezone.utc)
            days_old = (now - created).total_seconds() / 86400
            recency_score = 1.0 / (1.0 + days_old)  # Decay function
        except (ValueError, KeyError):
            recency_score = 0.5

        # Popularity: placeholder — có thể thêm reaction count sau
        popularity_score = 0.5

        # Tổng hợp
        final_score = (
            WEIGHT_TAG_MATCH * tag_score_norm
            + WEIGHT_RECENCY * recency_score
            + WEIGHT_POPULARITY * popularity_score
        )

        scored.append((post, final_score))

    # Sắp xếp giảm dần
    scored.sort(key=lambda x: x[1], reverse=True)
    return [post for post, _ in scored]
