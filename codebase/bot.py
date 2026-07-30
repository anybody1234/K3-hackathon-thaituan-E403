"""
Discord AI Agent — Gợi ý bài đăng cho server Discord.

CHẾ ĐỘ BATCH:
  - Bài mới → collect vào DB (không xử lý AI ngay)
  - Mỗi 5h → flush: xử lý AI + đăng batch digest
  - Lệnh /flush: admin flush thủ công (test/demo)
"""
import asyncio
import json
import logging
import sys

import discord
from discord.ext import commands, tasks

import config
from storage.database import Database
from features import digest, role_ping
from features.ask_bot import setup_ask_command
from features.foryou import setup_foryou_command
from ui.feedback_view import PersistentFeedbackView, set_database

# ── Logging ──────────────────────────────────────────────
import io
if sys.stdout.encoding != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
    datefmt="%H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("bot.log", encoding="utf-8"),
    ],
)
log = logging.getLogger("bot")

# ── Validate ─────────────────────────────────────────────
errors = config.validate()
if errors:
    for e in errors:
        log.error("Config error: %s", e)
    sys.exit(1)

# ── Intents ──────────────────────────────────────────────
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.guild_messages = True

# ── Bot ──────────────────────────────────────────────────
bot = commands.Bot(command_prefix="!", intents=intents)
db = Database()

_source_channel = None
_source_is_forum: bool = False
_digest_channel: discord.TextChannel | None = None


# ── Batch Digest Loop ────────────────────────────────────

@tasks.loop(hours=config.DIGEST_INTERVAL_HOURS)
async def batch_digest_loop():
    """Chạy mỗi DIGEST_INTERVAL_HOURS giờ — flush pending posts."""
    if _digest_channel is None:
        return

    guild = _digest_channel.guild
    log.info("=== BATCH DIGEST bat dau ===")

    try:
        count = await digest.flush_pending_digests(
            db=db,
            digest_channel=_digest_channel,
            guild=guild,
        )
        log.info("=== BATCH DIGEST xong: %d bai ===", count)
    except Exception as e:
        log.error("Loi batch digest: %s", e, exc_info=True)


@batch_digest_loop.before_loop
async def before_batch():
    """Chờ bot sẵn sàng trước khi bắt đầu loop."""
    await bot.wait_until_ready()
    log.info("Batch digest loop san sang (moi %sh)", config.DIGEST_INTERVAL_HOURS)


# ── Events ───────────────────────────────────────────────

@bot.event
async def on_ready():
    global _source_channel, _source_is_forum, _digest_channel

    log.info("=" * 50)
    log.info("Bot online: %s (ID: %s)", bot.user.name, bot.user.id)
    log.info("=" * 50)

    await db.connect()
    log.info("[OK] Database: %s", config.DB_PATH)

    set_database(db)
    bot.add_view(PersistentFeedbackView())
    log.info("[OK] Persistent views")

    # Tìm channels
    for guild in bot.guilds:
        log.info("Server: %s (ID: %s)", guild.name, guild.id)

        forum_channels = [c for c in guild.channels if isinstance(c, discord.ForumChannel)]
        text_channels = guild.text_channels

        log.info("  Text: %s", [c.name for c in text_channels])
        log.info("  Forum: %s", [c.name for c in forum_channels])

        for channel in forum_channels:
            if channel.name == config.SOURCE_CHANNEL_NAME:
                _source_channel = channel
                _source_is_forum = True
                log.info("  [SOURCE] Forum: #%s", channel.name)
                break

        if _source_channel is None:
            for channel in text_channels:
                if channel.name == config.SOURCE_CHANNEL_NAME:
                    _source_channel = channel
                    _source_is_forum = False
                    log.info("  [SOURCE] Text: #%s", channel.name)
                    break

        for channel in text_channels:
            if channel.name == config.DIGEST_CHANNEL_NAME:
                _digest_channel = channel
                log.info("  [DIGEST] Text: #%s", channel.name)
                break

    if not _source_channel:
        log.warning("Khong tim thay kenh #%s!", config.SOURCE_CHANNEL_NAME)
    if not _digest_channel:
        log.warning("Khong tim thay kenh #%s!", config.DIGEST_CHANNEL_NAME)

    # Slash commands
    setup_ask_command(bot.tree, db)
    setup_foryou_command(bot.tree, db)

    # /flush — admin flush thủ công (chỉ 1 bài mới nhất cho nhanh)
    @bot.tree.command(
        name="flush",
        description="[Admin] Đăng ngay 1 bài digest mới nhất (không chờ chu kỳ)",
    )
    async def flush_command(interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        if _digest_channel is None:
            await interaction.followup.send("Chua co kenh digest.", ephemeral=True)
            return
        count = await digest.flush_pending_digests(
            db=db,
            digest_channel=_digest_channel,
            guild=interaction.guild,
            limit=1,  # Chỉ 1 bài cho nhanh
        )
        await interaction.followup.send(
            f"Da xu ly va dang {count} bai moi.", ephemeral=True
        )

    try:
        synced = await bot.tree.sync()
        log.info("[OK] Synced %d slash commands", len(synced))
    except Exception as e:
        log.error("Loi sync commands: %s", e)

    # Start batch loop
    if not batch_digest_loop.is_running():
        batch_digest_loop.start()

    log.info("=" * 50)
    log.info("Bot san sang! (batch mode: moi %sh)", config.DIGEST_INTERVAL_HOURS)
    log.info("=" * 50)

    # Backfill: quét lại bài đăng bị lỡ khi bot offline
    await _backfill_missed_posts()


async def _backfill_missed_posts():
    """Quét forum channel để thu thập bài đăng bị lỡ khi bot offline."""
    if not _source_is_forum or _source_channel is None:
        return

    log.info("=== BACKFILL: Quet lai bai bi lo ===")
    collected = 0

    try:
        # Lấy tất cả thread đang active + archived gần đây
        threads = _source_channel.threads  # active threads

        # Cũng lấy archived threads
        archived = []
        try:
            async for thread in _source_channel.archived_threads(limit=50):
                archived.append(thread)
        except Exception as e:
            log.warning("Khong lay duoc archived threads: %s", e)

        all_threads = list(threads) + archived
        log.info("Tim thay %d thread trong forum #%s", len(all_threads), _source_channel.name)

        for thread in all_threads:
            try:
                # Lấy starter message
                starter = None
                try:
                    starter = thread.starter_message
                    if starter is None:
                        starter = await thread.fetch_message(thread.id)
                except Exception:
                    try:
                        async for msg in thread.history(limit=1, oldest_first=True):
                            starter = msg
                            break
                    except Exception:
                        continue

                if starter and not starter.author.bot:
                    # Kiểm tra chưa có trong DB
                    if not await db.post_exists(str(starter.id)):
                        post_id = await digest.collect_new_post(message=starter, db=db)
                        if post_id is not None:
                            collected += 1
                            log.info("Backfill: collect bai #%d '%s'", post_id, thread.name[:50])
            except Exception as e:
                log.warning("Loi backfill thread '%s': %s", thread.name, e)

    except Exception as e:
        log.error("Loi backfill: %s", e, exc_info=True)

    log.info("=== BACKFILL xong: %d bai moi ===", collected)


async def _collect_post(message: discord.Message):
    """Thu thập bài mới vào DB (không xử lý AI ngay)."""
    if _source_channel is None:
        return
    try:
        post_id = await digest.collect_new_post(message=message, db=db)
        if post_id is not None:
            log.info("Da collect bai #%d tu %s (cho batch)", post_id, message.author.display_name)
    except Exception as e:
        log.error("Loi collect bai: %s", e, exc_info=True)


@bot.event
async def on_thread_create(thread: discord.Thread):
    """Forum post mới → collect."""
    if not _source_is_forum or _source_channel is None:
        return
    if thread.parent_id != _source_channel.id:
        return

    log.info("Forum post moi: '%s' boi %s", thread.name, thread.owner)
    await asyncio.sleep(2)

    starter = None
    try:
        starter = thread.starter_message
        if starter is None:
            starter = await thread.fetch_message(thread.id)
    except Exception:
        try:
            async for msg in thread.history(limit=1, oldest_first=True):
                starter = msg
                break
        except Exception as e:
            log.error("Khong lay duoc starter message: %s", e)
            return

    if starter and not starter.author.bot:
        await _collect_post(starter)


@bot.event
async def on_message(message: discord.Message):
    """Text channel hoặc forum reply → collect."""
    if message.author.bot:
        return

    if _source_channel is not None and not _source_is_forum:
        if message.channel.id == _source_channel.id:
            await _collect_post(message)

    if _source_is_forum and _source_channel is not None:
        if isinstance(message.channel, discord.Thread):
            if message.channel.parent_id == _source_channel.id:
                from core.link_fetcher import extract_urls
                if len(message.content) > 50 or extract_urls(message.content):
                    await _collect_post(message)

    await bot.process_commands(message)


@bot.event
async def on_close():
    await db.close()
    log.info("Bot da tat.")


async def main():
    try:
        async with bot:
            await bot.start(config.DISCORD_BOT_TOKEN)
    except KeyboardInterrupt:
        log.info("Bot dung bang Ctrl+C")
    except Exception as e:
        log.error("Bot crash: %s", e, exc_info=True)
    finally:
        batch_digest_loop.cancel()
        await db.close()


if __name__ == "__main__":
    asyncio.run(main())
