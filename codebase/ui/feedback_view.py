"""
Feedback buttons — thu phản hồi người dùng trên digest cards.

Persistent view (sống qua restart) với 3 nút:
  👍 Hay  |  📌 Lưu  |  ⏭️ Bỏ qua

Mỗi lần bấm:
  - Ghi vào DB + cập nhật hồ sơ sở thích
  - DISABLE tất cả nút + highlight nút đã chọn
  - Trả ephemeral thông báo
"""
import json
import logging

import discord
from discord.ui import View, Button, button

log = logging.getLogger(__name__)

# Reference tới database sẽ được set từ bot.py
_db = None


def set_database(db):
    """Inject database reference. Gọi một lần từ bot.py."""
    global _db
    _db = db


def _extract_post_id(message: discord.Message) -> int | None:
    """Lấy post_id từ footer text của embed: 'ID: 42 • ...'"""
    if not message.embeds:
        return None
    footer = message.embeds[0].footer
    if footer and footer.text:
        try:
            id_part = footer.text.split("•")[0].strip()
            return int(id_part.replace("ID:", "").strip())
        except (ValueError, IndexError):
            return None
    return None


async def _handle_reaction(
    interaction: discord.Interaction, reaction_type: str
):
    """Xử lý chung cho cả 3 nút — disable sau khi bấm."""
    if _db is None:
        await interaction.response.send_message(
            "Bot dang khoi dong, thu lai sau.", ephemeral=True
        )
        return

    user_id = str(interaction.user.id)

    try:
        post_id = _extract_post_id(interaction.message)
        if post_id is None:
            await interaction.response.send_message(
                "Khong xac dinh duoc bai viet.", ephemeral=True
            )
            return

        # Ghi reaction vào DB
        await _db.save_reaction(
            user_id=user_id,
            post_id=post_id,
            reaction_type=reaction_type,
        )

        # Cập nhật hồ sơ sở thích
        post = await _db.get_post(post_id)
        if post:
            tags = json.loads(post["tags"]) if isinstance(post["tags"], str) else post["tags"]
            delta = {"like": 1.0, "save": 1.5, "skip": -0.3}.get(reaction_type, 0)
            for tag in tags:
                await _db.update_user_profile(user_id, tag, delta)

        # ── Disable tất cả nút + highlight nút đã chọn ──
        new_view = View(timeout=None)
        button_configs = [
            ("Hay", "👍", discord.ButtonStyle.success, "like"),
            ("Lưu", "📌", discord.ButtonStyle.primary, "save"),
            ("Bỏ qua", "⏭️", discord.ButtonStyle.secondary, "skip"),
        ]
        for label, emoji, style, action in button_configs:
            btn = Button(
                label=label,
                emoji=emoji,
                style=style if action == reaction_type else discord.ButtonStyle.secondary,
                disabled=True,
                custom_id=f"done:{action}:{post_id}",
            )
            # Thêm checkmark cho nút đã chọn
            if action == reaction_type:
                btn.label = f"✓ {label}"
            new_view.add_item(btn)

        await interaction.message.edit(view=new_view)

        # Phản hồi ephemeral
        messages = {
            "like": "👍 Đã ghi nhận — bạn thấy bài này hay!",
            "save": "📌 Đã lưu — sẽ ưu tiên nội dung tương tự cho bạn.",
            "skip": "⏭️ Đã bỏ qua — sẽ giảm nội dung tương tự.",
        }
        await interaction.response.send_message(
            messages[reaction_type], ephemeral=True
        )
        log.info(
            "Reaction %s tu user %s cho post %d",
            reaction_type, user_id, post_id,
        )

    except discord.errors.InteractionResponded:
        pass
    except Exception as e:
        log.error("Loi xu ly reaction: %s", e)
        try:
            await interaction.response.send_message(
                "Co loi xay ra, thu lai sau.", ephemeral=True
            )
        except discord.errors.InteractionResponded:
            pass


class FeedbackView(View):
    """
    Persistent view gắn dưới mỗi digest embed.
    Sau khi bấm 1 nút → disable tất cả + highlight nút đã chọn.
    """

    def __init__(self, post_id: int):
        super().__init__(timeout=None)
        self.post_id = post_id

    @button(
        label="Hay",
        emoji="👍",
        style=discord.ButtonStyle.success,
        custom_id="feedback:like",
    )
    async def like_button(self, interaction: discord.Interaction, btn: Button):
        await _handle_reaction(interaction, "like")

    @button(
        label="Lưu",
        emoji="📌",
        style=discord.ButtonStyle.primary,
        custom_id="feedback:save",
    )
    async def save_button(self, interaction: discord.Interaction, btn: Button):
        await _handle_reaction(interaction, "save")

    @button(
        label="Bỏ qua",
        emoji="⏭️",
        style=discord.ButtonStyle.secondary,
        custom_id="feedback:skip",
    )
    async def skip_button(self, interaction: discord.Interaction, btn: Button):
        await _handle_reaction(interaction, "skip")


class PersistentFeedbackView(View):
    """
    View đăng ký lúc startup để xử lý buttons từ tin nhắn cũ.
    """

    def __init__(self):
        super().__init__(timeout=None)

    @button(
        label="Hay",
        emoji="👍",
        style=discord.ButtonStyle.success,
        custom_id="feedback:like",
    )
    async def like_button(self, interaction: discord.Interaction, btn: Button):
        await _handle_reaction(interaction, "like")

    @button(
        label="Lưu",
        emoji="📌",
        style=discord.ButtonStyle.primary,
        custom_id="feedback:save",
    )
    async def save_button(self, interaction: discord.Interaction, btn: Button):
        await _handle_reaction(interaction, "save")

    @button(
        label="Bỏ qua",
        emoji="⏭️",
        style=discord.ButtonStyle.secondary,
        custom_id="feedback:skip",
    )
    async def skip_button(self, interaction: discord.Interaction, btn: Button):
        await _handle_reaction(interaction, "skip")
