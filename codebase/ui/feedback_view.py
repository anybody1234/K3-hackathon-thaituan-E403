"""
Feedback buttons — thu phản hồi người dùng trên digest cards.

Logic nút:
  - Hay + Lưu: tương thích, bấm cả 2 được
  - Bỏ qua: loại trừ tất cả, bấm xong disable hết
  - Sau khi bấm cả Hay + Lưu → disable hết
"""
import json
import logging

import discord
from discord.ui import View, Button, button

log = logging.getLogger(__name__)

_db = None


def set_database(db):
    global _db
    _db = db


def _extract_post_id(message: discord.Message) -> int | None:
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


async def _get_user_reactions_for_post(user_id: str, post_id: int) -> set[str]:
    """Lấy set reaction types mà user đã bấm cho post này."""
    if _db is None:
        return set()
    reactions = await _db.get_user_reactions(user_id)
    return {r["reaction_type"] for r in reactions if r["post_id"] == post_id}


def _build_updated_view(existing_reactions: set[str], new_reaction: str) -> View:
    """
    Tạo view mới dựa trên trạng thái reactions hiện tại.

    Rules:
      - Hay + Lưu tương thích → cả 2 có thể cùng active
      - Bỏ qua → loại trừ tất cả
      - Khi đã có cả Hay + Lưu → disable hết
    """
    all_reactions = existing_reactions | {new_reaction}

    # Nếu bấm "Bỏ qua" → disable tất cả
    if "skip" in all_reactions:
        view = View(timeout=None)
        for label, emoji, style, action in [
            ("Hay", "👍", discord.ButtonStyle.secondary, "like"),
            ("Lưu", "📌", discord.ButtonStyle.secondary, "save"),
            ("Bỏ qua", "⏭️", discord.ButtonStyle.secondary, "skip"),
        ]:
            btn_label = f"✓ {label}" if action in all_reactions else label
            btn_style = style
            if action == "skip" and action in all_reactions:
                btn_style = discord.ButtonStyle.danger
            view.add_item(Button(
                label=btn_label, emoji=emoji, style=btn_style,
                disabled=True, custom_id=f"done:{action}",
            ))
        return view

    # Nếu đã có cả Hay + Lưu → disable tất cả
    if "like" in all_reactions and "save" in all_reactions:
        view = View(timeout=None)
        for label, emoji, style, action in [
            ("Hay", "👍", discord.ButtonStyle.success, "like"),
            ("Lưu", "📌", discord.ButtonStyle.primary, "save"),
            ("Bỏ qua", "⏭️", discord.ButtonStyle.secondary, "skip"),
        ]:
            btn_label = f"✓ {label}" if action in all_reactions else label
            view.add_item(Button(
                label=btn_label, emoji=emoji, style=style,
                disabled=True, custom_id=f"done:{action}",
            ))
        return view

    # Chỉ có Hay hoặc chỉ có Lưu → disable Bỏ qua, cho phép bấm nút còn lại
    view = View(timeout=None)
    for label, emoji, style, action, cid in [
        ("Hay", "👍", discord.ButtonStyle.success, "like", "feedback:like"),
        ("Lưu", "📌", discord.ButtonStyle.primary, "save", "feedback:save"),
        ("Bỏ qua", "⏭️", discord.ButtonStyle.secondary, "skip", "feedback:skip"),
    ]:
        if action in all_reactions:
            # Nút đã bấm → disable + checkmark
            view.add_item(Button(
                label=f"✓ {label}", emoji=emoji, style=style,
                disabled=True, custom_id=f"done:{action}",
            ))
        elif action == "skip":
            # Bỏ qua → disable (không tương thích với Hay/Lưu)
            view.add_item(Button(
                label=label, emoji=emoji, style=style,
                disabled=True, custom_id=f"done:{action}",
            ))
        else:
            # Nút chưa bấm + tương thích → vẫn enabled
            view.add_item(Button(
                label=label, emoji=emoji, style=style,
                disabled=False, custom_id=cid,
            ))

    return view


async def _handle_reaction(
    interaction: discord.Interaction, reaction_type: str
):
    """Xử lý chung cho cả 3 nút."""
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

        # Lấy reactions hiện tại của user cho post này
        existing = await _get_user_reactions_for_post(user_id, post_id)

        # Kiểm tra logic tương thích
        if reaction_type == "skip" and ("like" in existing or "save" in existing):
            await interaction.response.send_message(
                "Bạn đã đánh giá bài này rồi, không thể bỏ qua.", ephemeral=True
            )
            return

        if reaction_type in ("like", "save") and "skip" in existing:
            await interaction.response.send_message(
                "Bạn đã bỏ qua bài này rồi.", ephemeral=True
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

        # Cập nhật buttons trên message
        new_existing = existing | {reaction_type}
        new_view = _build_updated_view(existing, reaction_type)
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
            "Reaction %s tu user %s cho post %d (total: %s)",
            reaction_type, user_id, post_id, new_existing,
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
    def __init__(self, post_id: int):
        super().__init__(timeout=None)
        self.post_id = post_id

    @button(label="Hay", emoji="👍", style=discord.ButtonStyle.success, custom_id="feedback:like")
    async def like_button(self, interaction: discord.Interaction, btn: Button):
        await _handle_reaction(interaction, "like")

    @button(label="Lưu", emoji="📌", style=discord.ButtonStyle.primary, custom_id="feedback:save")
    async def save_button(self, interaction: discord.Interaction, btn: Button):
        await _handle_reaction(interaction, "save")

    @button(label="Bỏ qua", emoji="⏭️", style=discord.ButtonStyle.secondary, custom_id="feedback:skip")
    async def skip_button(self, interaction: discord.Interaction, btn: Button):
        await _handle_reaction(interaction, "skip")


class PersistentFeedbackView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @button(label="Hay", emoji="👍", style=discord.ButtonStyle.success, custom_id="feedback:like")
    async def like_button(self, interaction: discord.Interaction, btn: Button):
        await _handle_reaction(interaction, "like")

    @button(label="Lưu", emoji="📌", style=discord.ButtonStyle.primary, custom_id="feedback:save")
    async def save_button(self, interaction: discord.Interaction, btn: Button):
        await _handle_reaction(interaction, "save")

    @button(label="Bỏ qua", emoji="⏭️", style=discord.ButtonStyle.secondary, custom_id="feedback:skip")
    async def skip_button(self, interaction: discord.Interaction, btn: Button):
        await _handle_reaction(interaction, "skip")
