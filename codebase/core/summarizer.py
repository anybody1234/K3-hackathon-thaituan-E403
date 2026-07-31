"""
Gọi OpenRouter API (OpenAI-compatible) để tóm tắt bài đăng + gắn tag chủ đề.

OpenRouter ưu điểm:
- Không bị rate limit như Google API trực tiếp
- Hỗ trợ nhiều model qua 1 endpoint
- Tự động fallback nếu model chính bận
"""
import json
import logging
import asyncio

from openai import AsyncOpenAI

import config

log = logging.getLogger(__name__)

# ── OpenRouter client ────────────────────────────────────
_openrouter = AsyncOpenAI(
    api_key=config.OPENROUTER_API_KEY,
    base_url="https://openrouter.ai/api/v1",
)

# ── Prompt ───────────────────────────────────────────────

_SYSTEM_PROMPT = f"""\
Bạn là trợ lý AI cho server Discord cộng đồng học viên công nghệ.
Nhiệm vụ: TÓM TẮT NGẮN GỌN bài chia sẻ và gắn tag chủ đề.

QUY TẮC:
1. PHẢI TÓM TẮT bằng lời mới — KHÔNG copy nguyên văn từ bài gốc.
2. Tóm tắt trong 2-3 câu NGẮN, tổng tối đa 150 ký tự. Chỉ nêu ý chính cốt lõi.
3. Gắn 1-3 tag từ danh sách: {', '.join(config.ALLOWED_TAGS)}
4. Nếu nội dung quá ngắn/không rõ, summary = "Nội dung chưa đủ để tóm tắt", tags = ["Khác"].
5. KHÔNG bịa thông tin.
6. Trả về JSON thuần, không markdown, không code block.

VÍ DỤ:
{{"summary": "Chia sẻ 6 nguyên tắc AI có trách nhiệm của Google. Hữu ích cho ai đang xây sản phẩm AI.", "tags": ["AI"]}}

FORMAT:
{{"summary": "tóm tắt ngắn gọn", "tags": ["tag1"]}}
"""


async def summarize_and_tag(content: str, author_name: str = "") -> dict:
    """
    Tóm tắt nội dung + gắn tag qua OpenRouter.

    Nhanh, đơn giản, không bị rate limit.
    """
    if not content or len(content.strip()) < 10:
        return {
            "summary": "Nội dung chưa đủ để tóm tắt.",
            "tags": ["Khác"],
        }

    user_prompt = f"Người đăng: {author_name}\n\nNội dung bài:\n{content[:3000]}"

    # Thử tối đa 2 lần
    for attempt in range(2):
        try:
            if attempt > 0:
                await asyncio.sleep(3)

            log.info("Goi OpenRouter %s (lan %d)...", config.OPENROUTER_MODEL, attempt + 1)

            response = await _openrouter.chat.completions.create(
                model=config.OPENROUTER_MODEL,
                messages=[
                    {"role": "system", "content": _SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.3,
                max_tokens=400,
            )

            text = response.choices[0].message.content
            if not text:
                log.warning("OpenRouter tra ve rong")
                continue

            result = _parse_response(text)
            if result and len(result["summary"]) > 15:
                log.info("Summarize OK: %s | %s", result["summary"][:60], result["tags"])
                return result
            else:
                log.warning("Summary qua ngan hoac parse fail: %s",
                           result.get("summary", "") if result else "None")

        except Exception as e:
            log.error("Loi OpenRouter (lan %d): %s", attempt + 1, e)

    # Fallback
    log.error("OpenRouter fail, dung fallback")
    return {
        "summary": _smart_fallback(content),
        "tags": ["Khác"],
    }


def _smart_fallback(content: str) -> str:
    """Fallback tóm tắt khi API fail — lấy câu đầu + cắt gọn."""
    sentences = [s.strip() for s in content.replace("\n", ". ").split(".") if s.strip() and len(s.strip()) > 10]
    if sentences:
        summary = ". ".join(sentences[:2])
        if len(summary) > 250:
            summary = summary[:250] + "..."
        return f"[AI tạm nghỉ] {summary}"
    return f"[AI tạm nghỉ] {content[:200]}..."


def _parse_response(text: str) -> dict | None:
    """Parse JSON từ response, bao gồm xử lý JSON bị cắt cụt."""
    cleaned = text.strip()

    # Bỏ code block nếu có
    if cleaned.startswith("```"):
        lines = cleaned.split("\n")
        cleaned = "\n".join(
            line for line in lines
            if not line.strip().startswith("```")
        )

    # Thử parse trực tiếp
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        data = _try_repair_json(cleaned)
        if data is None:
            log.warning("Khong parse duoc JSON: %s", text[:200])
            return None

    summary = data.get("summary", "")
    tags = data.get("tags", [])

    valid_tags = [t for t in tags if t in config.ALLOWED_TAGS]
    if not valid_tags:
        valid_tags = ["Khác"]

    return {"summary": summary, "tags": valid_tags}


def _try_repair_json(text: str) -> dict | None:
    """Thử sửa JSON bị cắt cụt (thiếu đóng ngoặc/quote)."""
    import re

    cleaned = text.strip()

    # Tìm JSON bắt đầu
    if not cleaned.startswith("{"):
        idx = cleaned.find("{")
        if idx == -1:
            return None
        cleaned = cleaned[idx:]

    # Thử thêm ký tự đóng
    for suffix in ['', '"}', '"]}', '"}]}', '"]}', '}']:
        try:
            data = json.loads(cleaned + suffix)
            if isinstance(data, dict) and "summary" in data:
                log.info("Da sua JSON bi cat cut thanh cong")
                return data
        except json.JSONDecodeError:
            continue

    # Regex fallback
    match = re.search(r'"summary"\s*:\s*"((?:[^"\\]|\\.)*)"', cleaned)
    if match:
        summary = match.group(1)
        tags_match = re.search(r'"tags"\s*:\s*\[(.*?)\]', cleaned)
        tags = []
        if tags_match:
            tags = [t.strip().strip('"') for t in tags_match.group(1).split(",")]
        log.info("Da extract summary bang regex fallback")
        return {"summary": summary, "tags": tags}

    return None


async def generate_rag_answer(question: str, context: str) -> str | None:
    """Gọi OpenRouter để tổng hợp câu trả lời RAG."""
    prompt = f"""\
Dựa trên các bài chia sẻ sau đây, hãy trả lời câu hỏi của người dùng.
Trả lời ngắn gọn (3-5 câu), bằng tiếng Việt, có trích dẫn [Bài N].

CÁC BÀI CHIA SẺ:
{context}

CÂU HỎI: {question}

TRẢ LỜI:"""

    try:
        response = await _openrouter.chat.completions.create(
            model=config.OPENROUTER_MODEL,
            messages=[
                {"role": "user", "content": prompt},
            ],
            temperature=0.4,
            max_tokens=512,
        )
        text = response.choices[0].message.content
        if text:
            return text
    except Exception as e:
        log.warning("RAG fail: %s", e)

    return None
