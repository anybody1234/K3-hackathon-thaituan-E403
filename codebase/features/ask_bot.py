"""
Hỏi bot (RAG) — /ask <câu hỏi>

Người dùng hỏi bằng ngôn ngữ tự nhiên, bot tìm bài liên quan
qua semantic search (cosine similarity trên embeddings),
rồi gọi Gemini để tổng hợp câu trả lời có trích dẫn.
"""
import logging

import discord
from discord import app_commands

import config
from core import embedder
from core.summarizer import generate_rag_answer
from storage.database import Database
from ui.digest_embed import create_search_result_embed

log = logging.getLogger(__name__)


def setup_ask_command(tree: app_commands.CommandTree, db: Database):
    """Đăng ký slash command /ask."""

    @tree.command(
        name="ask",
        description="Hỏi bot tìm bài chia sẻ liên quan đến câu hỏi của bạn",
    )
    @app_commands.describe(question="Câu hỏi hoặc chủ đề bạn muốn tìm")
    async def ask_command(interaction: discord.Interaction, question: str):
        # Defer vì xử lý mất vài giây
        await interaction.response.defer(ephemeral=True)

        try:
            # 1. Embed câu hỏi
            query_emb = await embedder.create_embedding(
                question, task_type="RETRIEVAL_QUERY"
            )
            if query_emb is None:
                await interaction.followup.send(
                    "Khong the xu ly cau hoi. Thu lai sau.", ephemeral=True
                )
                return

            # 2. Lấy tất cả bài có embedding
            posts = await db.get_all_posts_with_embeddings()
            if not posts:
                await interaction.followup.send(
                    "Chua co bai nao trong kho. Hay chia se bai dau tien!",
                    ephemeral=True,
                )
                return

            # 3. Tìm top_k bài liên quan nhất
            results = embedder.find_similar(
                query_emb, posts, top_k=config.TOP_K_RESULTS
            )

            # Lọc bài có similarity quá thấp
            results = [(p, s) for p, s in results if s > 0.3]

            if not results:
                await interaction.followup.send(
                    f"Khong tim thay bai nao lien quan den \"{question}\".",
                    ephemeral=True,
                )
                return

            # 4. Gọi Gemini tổng hợp câu trả lời (RAG)
            context_parts = []
            for i, (post, score) in enumerate(results, 1):
                tags = ", ".join(post.get("tags", []))
                context_parts.append(
                    f"[Bài {i}] (Độ liên quan: {score:.0%})\n"
                    f"Tóm tắt: {post.get('summary', 'N/A')}\n"
                    f"Tags: {tags}\n"
                    f"Link: {post.get('jump_url', 'N/A')}"
                )
            context = "\n\n".join(context_parts)

            answer = await generate_rag_answer(question, context)

            # 5. Tạo embed kết quả
            embed = create_search_result_embed(
                query=question,
                results=results,
                answer=answer,
            )

            await interaction.followup.send(embed=embed, ephemeral=True)
            log.info(
                "Tra loi /ask tu %s: '%s' -> %d ket qua",
                interaction.user.display_name, question, len(results),
            )

        except Exception as e:
            log.error("Loi /ask: %s", e)
            await interaction.followup.send(
                "Co loi xay ra khi tim kiem. Thu lai sau.", ephemeral=True
            )
