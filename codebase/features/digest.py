"""
Digest — xử lý bài mới theo chế độ BATCH.

Chế độ batch (5h/lần):
  1. Khi có bài mới → collect: lưu DB với digest_msg_id = NULL (chưa đăng)
  2. Theo chu kỳ → flush: lấy tất cả bài chưa đăng, tóm tắt + embed + đăng
"""
import logging
from datetime import datetime, timezone, timedelta

import discord

from core import link_fetcher, summarizer, embedder
from storage.database import Database
from ui.digest_embed import create_digest_embed
from ui.feedback_view import FeedbackView
import config

log = logging.getLogger(__name__)


async def collect_new_post(
    message: discord.Message,
    db: Database,
) -> int | None:
    """
    Bước 1 — Thu thập bài mới: lưu vào DB CHƯA xử lý AI.
    Trả về post_id hoặc None nếu skip.
    """
    msg_id = str(message.id)

    # Chống trùng
    if await db.post_exists(msg_id):
        return None

    content = message.content or ""
    author_name = message.author.display_name

    # Bỏ qua tin quá ngắn không có link
    urls = link_fetcher.extract_urls(content)
    if len(content.strip()) < 15 and not urls:
        return None

    log.info("Thu thap bai tu %s: %s...", author_name, content[:80])

    # Fetch nội dung link ngay (không cần AI)
    fetched = None
    if urls:
        fetched = await link_fetcher.fetch_content_for_message(content)

    # Lưu vào DB — chưa có summary/tags/embedding (sẽ xử lý lúc flush)
    post_id = await db.save_post(
        discord_msg_id=msg_id,
        channel_id=str(message.channel.id),
        author_id=str(message.author.id),
        author_name=author_name,
        content=content,
        fetched_content=fetched,
        summary=None,    # Chưa tóm tắt
        tags=[],
        embedding=None,  # Chưa embed
        jump_url=message.jump_url,
        created_at=message.created_at.replace(tzinfo=timezone.utc),
    )

    log.info("Da luu bai #%d (chua xu ly AI)", post_id)
    return post_id


async def flush_pending_digests(
    db: Database,
    digest_channel: discord.TextChannel,
    guild: discord.Guild,
) -> int:
    """
    Bước 2 — Flush batch: lấy bài chưa đăng, xử lý AI, đăng digest.

    Chỉ xử lý bài trong vòng DIGEST_INTERVAL_HOURS giờ gần nhất.
    Trả về số bài đã đăng.
    """
    # Lấy bài chưa đăng digest (digest_msg_id IS NULL, summary IS NULL)
    pending = await db.get_pending_posts()

    if not pending:
        log.info("Khong co bai moi can xu ly")
        return 0

    # Lọc bài quá cũ (> DIGEST_INTERVAL_HOURS)
    cutoff = datetime.now(timezone.utc) - timedelta(hours=config.DIGEST_INTERVAL_HOURS)
    valid_posts = []
    skipped = 0
    for post in pending:
        try:
            created = datetime.fromisoformat(post["created_at"])
            if created.tzinfo is None:
                created = created.replace(tzinfo=timezone.utc)
            if created >= cutoff:
                valid_posts.append(post)
            else:
                skipped += 1
                # Đánh dấu bài cũ là đã bỏ qua
                await db.mark_skipped(post["id"])
        except (ValueError, KeyError):
            valid_posts.append(post)  # Không parse được time → vẫn xử lý

    if skipped > 0:
        log.info("Bo qua %d bai qua cu (> %dh)", skipped, config.DIGEST_INTERVAL_HOURS)

    if not valid_posts:
        log.info("Khong co bai moi trong %dh qua", config.DIGEST_INTERVAL_HOURS)
        return 0

    # Header message cho batch
    count = len(valid_posts)
    header = await digest_channel.send(
        f"📋 **Tổng hợp {count} bài chia sẻ mới** (cập nhật mỗi {int(config.DIGEST_INTERVAL_HOURS)}h)\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    )

    posted = 0
    for post in valid_posts:
        try:
            content_for_ai = post.get("fetched_content") or post.get("content") or ""
            author_name = post.get("author_name", "")

            # Gọi Gemini: tóm tắt + tag
            result = await summarizer.summarize_and_tag(content_for_ai, author_name)
            summary = result["summary"]
            tags = result["tags"]

            # Sinh embedding
            embed_text = f"{summary}\n{content_for_ai[:2000]}"
            embedding = await embedder.create_embedding(embed_text)

            # Cập nhật DB
            await db.update_post_ai_results(
                post_id=post["id"],
                summary=summary,
                tags=tags,
                embedding=embedding,
            )

            # Đăng digest embed
            embed = create_digest_embed(
                summary=summary,
                tags=tags,
                author_name=author_name,
                jump_url=post.get("jump_url", ""),
                post_id=post["id"],
            )
            view = FeedbackView(post_id=post["id"])
            digest_msg = await digest_channel.send(embed=embed, view=view)

            # Ghi digest_msg_id
            await db.set_digest_msg_id(post["id"], str(digest_msg.id))

            posted += 1
            log.info("Da dang digest #%d: %s | %s", post["id"], summary[:50], tags)

        except Exception as e:
            log.error("Loi xu ly bai #%d: %s", post["id"], e)

    log.info("=== Batch xong: %d/%d bai ===", posted, count)
    return posted
