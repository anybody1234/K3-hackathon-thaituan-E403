"""
Tạo Discord Embed đẹp cho thẻ digest.

Mỗi bài chia sẻ được hiển thị dưới dạng embed card
với tóm tắt, tags, link gốc, và author.
"""
import discord

# ── Màu theo tag chính ───────────────────────────────────
TAG_COLORS: dict[str, int] = {
    "AI":       0x8B5CF6,   # Tím
    "LLM":      0x7C3AED,   # Tím đậm
    "Prompt":   0xA78BFA,   # Tím nhạt
    "Python":   0x3B82F6,   # Xanh dương
    "Web":      0x06B6D4,   # Cyan
    "Backend":  0x10B981,   # Xanh lá
    "Data":     0xF59E0B,   # Vàng
    "DevOps":   0xEF4444,   # Đỏ
    "Mobile":   0xEC4899,   # Hồng
    "Design":   0xF97316,   # Cam
    "Career":   0x6366F1,   # Indigo
    "Product":  0x14B8A6,   # Teal
    "Khác":     0x6B7280,   # Xám
}

DEFAULT_COLOR = 0x5865F2  # Discord blurple


def create_digest_embed(
    *,
    summary: str,
    tags: list[str],
    author_name: str,
    jump_url: str,
    post_id: int,
    title: str = "",
    original_content: str | None = None,
) -> discord.Embed:
    """
    Tạo embed card cho digest channel.

    Returns:
        discord.Embed đã format đẹp
    """
    # Màu theo tag đầu tiên
    primary_tag = tags[0] if tags else "Khác"
    color = TAG_COLORS.get(primary_tag, DEFAULT_COLOR)

    embed = discord.Embed(
        title=title or None,
        description=summary,
        color=color,
        url=jump_url if title else None,
    )

    # Tags dạng badge
    tag_display = "  ".join(f"`{tag}`" for tag in tags)
    embed.add_field(name="🏷️ Chủ đề", value=tag_display, inline=True)

    # Link gốc
    embed.add_field(
        name="🔗 Bài gốc",
        value=f"[Xem bài đăng]({jump_url})",
        inline=True,
    )

    # Author
    embed.set_author(name=f"📝 Chia sẻ bởi {author_name}")

    # Footer với post ID (để feedback buttons trỏ đúng bài)
    embed.set_footer(text=f"ID: {post_id} • Bấm nút bên dưới để đánh giá")

    return embed


def create_foryou_embed(
    posts: list[dict],
    user_name: str,
) -> discord.Embed:
    """
    Tạo embed cho /foryou — danh sách gợi ý cá nhân.
    """
    embed = discord.Embed(
        title="🎯 Gợi ý cho bạn",
        description=f"Dựa trên sở thích của **{user_name}**, đây là những bài chia sẻ phù hợp nhất:",
        color=0x8B5CF6,
    )

    for i, post in enumerate(posts, 1):
        tags_str = ", ".join(f"`{t}`" for t in post.get("tags", []))
        summary = post.get("summary", "Không có tóm tắt")
        jump_url = post.get("jump_url", "")
        author = post.get("author_name", "Ẩn danh")

        value = f"{summary}\n{tags_str} • bởi {author}"
        if jump_url:
            value += f" • [xem]({jump_url})"

        embed.add_field(
            name=f"{i}. Bài chia sẻ",
            value=value,
            inline=False,
        )

    embed.set_footer(text="Bấm nút bên dưới để phản hồi • Dữ liệu giúp cải thiện gợi ý")
    return embed


def create_search_result_embed(
    query: str,
    results: list[tuple[dict, float]],
    answer: str | None = None,
) -> discord.Embed:
    """
    Tạo embed cho /ask — kết quả tìm kiếm.
    """
    embed = discord.Embed(
        title="🔍 Kết quả tìm kiếm",
        color=0x3B82F6,
    )

    if answer:
        embed.description = answer

    for i, (post, score) in enumerate(results[:5], 1):
        tags_str = ", ".join(f"`{t}`" for t in post.get("tags", []))
        summary = post.get("summary", "")[:150]
        jump_url = post.get("jump_url", "")
        relevance = f"{score:.0%}"

        value = f"{summary}\n{tags_str} • Độ liên quan: {relevance}"
        if jump_url:
            value += f" • [xem]({jump_url})"

        embed.add_field(
            name=f"{i}. Kết quả",
            value=value,
            inline=False,
        )

    embed.set_footer(text=f"Tìm kiếm: \"{query}\"")
    return embed
