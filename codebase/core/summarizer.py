"""
Gọi Gemini API để tóm tắt bài đăng + gắn tag chủ đề.

Có rate limiting (delay giữa các lần gọi) để tránh 429.
Fallback qua nhiều model nếu một model hết quota.
"""
import json
import logging
import asyncio

from google import genai
from google.genai import types

import config

log = logging.getLogger(__name__)

# Khởi tạo client
_client = genai.Client(api_key=config.GOOGLE_API_KEY)

# Danh sách model fallback — thử lần lượt nếu model chính hết quota
_FALLBACK_MODELS = [
    config.GEMINI_MODEL,       # gemini-2.0-flash
    "gemini-2.0-flash-lite",
    "gemini-2.5-flash",
]

# ── Prompt ───────────────────────────────────────────────

_SYSTEM_PROMPT = f"""\
Bạn là trợ lý AI cho server Discord cộng đồng học viên công nghệ.
Nhiệm vụ: TÓM TẮT bài chia sẻ và gắn tag chủ đề.

QUY TẮC QUAN TRỌNG:
1. PHẢI TÓM TẮT — KHÔNG copy nguyên văn mấy câu đầu. Hãy đọc toàn bộ nội dung rồi viết lại ý chính bằng cách diễn đạt mới, ngắn gọn.
2. Tóm tắt trong 2-3 câu bằng tiếng Việt. Nêu ý chính và giá trị/lợi ích của bài.
3. Gắn 1-3 tag từ danh sách: {', '.join(config.ALLOWED_TAGS)}
4. Nếu nội dung quá ngắn hoặc không rõ ràng, ghi summary là "Nội dung chưa đủ để tóm tắt" và tag là ["Khác"].
5. KHÔNG bịa thông tin. Chỉ tóm tắt những gì có trong nội dung.
6. Trả về ĐÚNG JSON format, không markdown, không giải thích thêm.

FORMAT OUTPUT (JSON thuần, không code block):
{{"summary": "tóm tắt 2-3 câu bằng lời của bạn", "tags": ["tag1", "tag2"]}}
"""


async def summarize_and_tag(content: str, author_name: str = "") -> dict:
    """
    Tóm tắt nội dung + gắn tag.

    Có delay giữa các lần gọi API và fallback qua nhiều model.
    """
    if not content or len(content.strip()) < 10:
        return {
            "summary": "Nội dung chưa đủ để tóm tắt.",
            "tags": ["Khác"],
        }

    user_prompt = f"Người đăng: {author_name}\n\nNội dung bài:\n{content[:5000]}"

    # Thử từng model
    for model_name in _FALLBACK_MODELS:
        for attempt in range(3):
            try:
                # Rate limiting — delay trước mỗi lần gọi
                await asyncio.sleep(config.API_CALL_DELAY)

                response = await asyncio.to_thread(
                    _client.models.generate_content,
                    model=model_name,
                    contents=user_prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=_SYSTEM_PROMPT,
                        temperature=0.3,
                        max_output_tokens=512,
                    ),
                )

                if not response.text:
                    log.warning("Gemini tra ve rong (%s, attempt %d)", model_name, attempt + 1)
                    continue

                result = _parse_response(response.text)
                if result:
                    log.info("Summarize OK voi model %s", model_name)
                    return result

            except Exception as e:
                error_str = str(e)
                if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str:
                    log.warning("Model %s het quota, thu model tiep theo", model_name)
                    # Chờ retry delay nếu API trả về
                    await asyncio.sleep(5)
                    break  # Chuyển sang model tiếp
                elif "503" in error_str or "UNAVAILABLE" in error_str:
                    log.warning("Model %s dang qua tai, doi...", model_name)
                    await asyncio.sleep(10)
                    continue
                else:
                    log.error("Loi Gemini (%s, attempt %d): %s", model_name, attempt + 1, e)
                    if attempt < 2:
                        await asyncio.sleep(3 * (attempt + 1))

    # Fallback khi tất cả model fail
    log.error("TAT CA model Gemini fail, dung fallback")
    return {
        "summary": _smart_fallback(content),
        "tags": ["Khác"],
    }


def _smart_fallback(content: str) -> str:
    """Fallback tóm tắt khi Gemini fail — lấy câu đầu + cắt gọn."""
    # Tách câu
    sentences = [s.strip() for s in content.replace("\n", ". ").split(".") if s.strip() and len(s.strip()) > 10]
    if sentences:
        # Lấy 2 câu đầu có ý nghĩa
        summary = ". ".join(sentences[:2])
        if len(summary) > 250:
            summary = summary[:250] + "..."
        return f"[AI tạm nghỉ] {summary}"
    return f"[AI tạm nghỉ] {content[:200]}..."


def _parse_response(text: str) -> dict | None:
    """Parse JSON từ response Gemini."""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        lines = cleaned.split("\n")
        cleaned = "\n".join(
            line for line in lines
            if not line.strip().startswith("```")
        )

    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        log.warning("Khong parse duoc JSON: %s", text[:200])
        return None

    summary = data.get("summary", "")
    tags = data.get("tags", [])

    valid_tags = [t for t in tags if t in config.ALLOWED_TAGS]
    if not valid_tags:
        valid_tags = ["Khác"]

    return {"summary": summary, "tags": valid_tags}


async def generate_rag_answer(question: str, context: str) -> str | None:
    """Gọi Gemini để tổng hợp câu trả lời RAG."""
    prompt = f"""\
Dựa trên các bài chia sẻ sau đây, hãy trả lời câu hỏi của người dùng.
Trả lời ngắn gọn (3-5 câu), bằng tiếng Việt, có trích dẫn [Bài N].

CÁC BÀI CHIA SẺ:
{context}

CÂU HỎI: {question}

TRẢ LỜI:"""

    for model_name in _FALLBACK_MODELS:
        try:
            await asyncio.sleep(config.API_CALL_DELAY)
            response = await asyncio.to_thread(
                _client.models.generate_content,
                model=model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.4,
                    max_output_tokens=512,
                ),
            )
            if response.text:
                return response.text
        except Exception as e:
            log.warning("RAG voi %s fail: %s", model_name, e)
            continue

    return None
