"""
Sinh embedding cho bài đăng bằng Gemini Embedding API.

Dùng google.genai (SDK mới) — model text-embedding-004 (768 dims).
Cosine similarity để so sánh — phục vụ RAG và /foryou.
"""
import asyncio
import logging

from google import genai

import numpy as np

import config

log = logging.getLogger(__name__)

# Khởi tạo client
_client = genai.Client(api_key=config.GOOGLE_API_KEY)


async def create_embedding(
    text: str, task_type: str = "RETRIEVAL_DOCUMENT"
) -> np.ndarray | None:
    """
    Sinh embedding vector cho một đoạn text.

    Args:
        text: nội dung cần embed
        task_type: "RETRIEVAL_DOCUMENT" cho bài đăng,
                   "RETRIEVAL_QUERY" cho câu hỏi search

    Returns:
        numpy array 768 dims, hoặc None nếu lỗi
    """
    if not text or len(text.strip()) < 5:
        return None

    # Cắt text quá dài (Gemini embedding giới hạn ~2048 tokens)
    truncated = text[:8000]

    for attempt in range(3):
        try:
            result = await asyncio.to_thread(
                _client.models.embed_content,
                model=config.EMBEDDING_MODEL,
                contents=truncated,
            )
            # result.embeddings là list, lấy phần tử đầu
            if result.embeddings:
                return np.array(result.embeddings[0].values, dtype=np.float32)
            return None

        except Exception as e:
            log.error("Lỗi embedding (attempt %d): %s", attempt + 1, e)
            if attempt < 2:
                await asyncio.sleep(2 ** attempt)

    return None


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Cosine similarity giữa hai vector."""
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(a, b) / (norm_a * norm_b))


def find_similar(
    query_emb: np.ndarray,
    posts: list[dict],
    top_k: int = 5,
) -> list[tuple[dict, float]]:
    """
    Tìm top_k bài giống nhất với query embedding.

    Args:
        query_emb: embedding của câu hỏi
        posts: list dict, mỗi dict có key "embedding" (np.ndarray)
        top_k: số kết quả trả về

    Returns:
        list of (post_dict, similarity_score), sắp xếp giảm dần
    """
    scored = []
    for post in posts:
        emb = post.get("embedding")
        if emb is None:
            continue
        sim = cosine_similarity(query_emb, emb)
        scored.append((post, sim))

    scored.sort(key=lambda x: x[1], reverse=True)
    return scored[:top_k]
