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
    """
    all_reactions = existing_reactions | {new_reaction}

    # BẮT BUỘC dùng PersistentFeedbackView để giữ lại các callbacks (nếu ko click lần 2 sẽ bị lỗi không phản hồi)
    view = PersistentFeedbackView()

    for child in view.children:
        if not isinstance(child, Button):
            continue
        
        # custom_id ban đầu là feedback:like, feedback:save, feedback:skip
        action = child.custom_id.replace("feedback:", "")

        # Nếu bấm "Bỏ qua" → disable tất cả
        if "skip" in all_reactions:
            if action in all_reactions:
                child.label = f"✓ {child.label}"
                child.style = discord.ButtonStyle.danger
            child.disabled = True
            child.custom_id = f"done:{action}"
            continue

        # Nếu đã có cả Hay + Lưu → disable tất cả
        if "like" in all_reactions and "save" in all_reactions:
            if action in all_reactions:
                child.label = f"✓ {child.label}"
            child.disabled = True
            child.custom_id = f"done:{action}"
            continue

        # Chỉ có Hay hoặc chỉ có Lưu
        if action in all_reactions:
            child.label = f"✓ {child.label}"
            child.disabled = True
            child.custom_id = f"done:{action}"
        elif action == "skip":
            child.disabled = True
            child.custom_id = f"done:{action}"
        else:
            # Nút tương thích chưa bấm → giữ nguyên
            child.disabled = False

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

    # Tránh timeout bằng cách defer ngay lập tức
    await interaction.response.defer(ephemeral=True)

    user_id = str(interaction.user.id)

    try:
        post_id = _extract_post_id(interaction.message)
        if post_id is None:
            await interaction.followup.send(
                "Khong xac dinh duoc bai viet.", ephemeral=True
            )
            return

        # Lấy reactions hiện tại của user cho post này
        existing = await _get_user_reactions_for_post(user_id, post_id)

        # Kiểm tra logic tương thích
        if reaction_type == "skip" and ("like" in existing or "save" in existing):
            await interaction.followup.send(
                "Bạn đã đánh giá bài này rồi, không thể bỏ qua.", ephemeral=True
            )
            return

        if reaction_type in ("like", "save") and "skip" in existing:
            await interaction.followup.send(
                "Bạn đã bỏ qua bài này rồi.", ephemeral=True
            )
            return

        if reaction_type in existing:
            await interaction.followup.send(
                "Bạn đã thực hiện hành động này rồi.", ephemeral=True
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
        await interaction.followup.send(
            messages[reaction_type], ephemeral=True
        )
        log.info(
            "Reaction %s tu user %s cho post %d (total: %s)",
            reaction_type, user_id, post_id, new_existing,
        )

    except Exception as e:
        log.error("Loi xu ly reaction: %s", e)
        try:
            await interaction.followup.send(
                "Co loi xay ra, thu lai sau.", ephemeral=True
            )
        except Exception:
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
