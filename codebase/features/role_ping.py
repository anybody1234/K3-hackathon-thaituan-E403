"""
Role ping — ping interest role khớp tag bài đăng.

Khi digest được đăng, bot ping các role tương ứng
để thông báo cho người quan tâm chủ đề đó.
"""
import logging

import discord

import config

log = logging.getLogger(__name__)


async def ping_matching_roles(
    *,
    tags: list[str],
    digest_channel: discord.TextChannel,
    guild: discord.Guild,
):
    """
    Ping các role khớp với tags của bài đăng.

    Nguyên tắc push: thà bỏ sót còn hơn ping nhầm.
    Chỉ ping role có trong TOPIC_ROLE_MAP.
    """
    role_names_to_ping = []

    for tag in tags:
        role_name = config.TOPIC_ROLE_MAP.get(tag)
        if role_name:
            role_names_to_ping.append(role_name)

    if not role_names_to_ping:
        return

    # Tìm role objects theo tên
    mentions = []
    for role_name in role_names_to_ping:
        role = discord.utils.get(guild.roles, name=role_name)
        if role:
            mentions.append(role.mention)
        else:
            log.warning("Không tìm thấy role '%s' trên server", role_name)

    if mentions:
        mention_text = " ".join(mentions)
        await digest_channel.send(
            f"📢 Bài mới liên quan: {mention_text}",
            allowed_mentions=discord.AllowedMentions(roles=True),
        )
        log.info("Đã ping roles: %s", role_names_to_ping)
