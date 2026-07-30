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
Nhiệm vụ: TÓM TẮT NGẮN GỌN bài chia sẻ và gắn tag chủ đề.

QUY TẮC:
1. PHẢI TÓM TẮT bằng lời mới — KHÔNG copy nguyên văn từ bài gốc.
2. Tóm tắt trong 2-3 câu NGẮN, tổng tối đa 150 ký tự. Chỉ nêu ý chính cốt lõi.
3. Gắn 1-3 tag từ danh sách: {', '.join(config.ALLOWED_TAGS)}
4. Nếu nội dung quá ngắn/không rõ, summary = "Nội dung chưa đủ để tóm tắt", tags = ["Khác"].
5. KHÔNG bịa thông tin.
6. Trả về JSON thuần, không markdown.

VÍ DỤ:
{{"summary": "Chia sẻ 6 nguyên tắc AI có trách nhiệm của Google. Hữu ích cho ai đang xây sản phẩm AI.", "tags": ["AI"]}}

FORMAT:
{{"summary": "tóm tắt ngắn gọn", "tags": ["tag1"]}}
"""


async def summarize_and_tag(content: str, author_name: str = "") -> dict:
    """
    Tóm tắt nội dung + gắn tag.

    Retry thông minh: 2 vòng qua tất cả model, exponential backoff khi bị 429.
    """
    if not content or len(content.strip()) < 10:
        return {
            "summary": "Nội dung chưa đủ để tóm tắt.",
            "tags": ["Khác"],
        }

    user_prompt = f"Người đăng: {author_name}\n\nNội dung bài:\n{content[:5000]}"

    # 2 vòng — nếu vòng 1 tất cả bị 429, chờ lâu rồi thử lại vòng 2
    for round_num in range(2):
        if round_num > 0:
            wait_time = 30
            log.info("Tat ca model bi rate limit, cho %ds roi thu lai (vong %d)...", wait_time, round_num + 1)
            await asyncio.sleep(wait_time)

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
                            max_output_tokens=200,
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
                        # Exponential backoff: 15s, 30s, 60s
                        backoff = 15 * (2 ** attempt)
                        log.warning("Model %s bi rate limit (attempt %d), cho %ds...",
                                    model_name, attempt + 1, backoff)
                        await asyncio.sleep(backoff)
                        if attempt >= 1:
                            break  # Chuyển sang model tiếp sau 2 lần thử
                    elif "503" in error_str or "UNAVAILABLE" in error_str:
                        log.warning("Model %s dang qua tai, doi 15s...", model_name)
                        await asyncio.sleep(15)
                        continue
                    else:
                        log.error("Loi Gemini (%s, attempt %d): %s", model_name, attempt + 1, e)
                        if attempt < 2:
                            await asyncio.sleep(3 * (attempt + 1))

    # Fallback khi tất cả model fail sau 2 vòng
    log.error("TAT CA model Gemini fail sau 2 vong, dung fallback")
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
    """Parse JSON từ response Gemini, bao gồm xử lý JSON bị cắt cụt."""
    cleaned = text.strip()
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
        # Thử sửa JSON bị cắt cụt (thiếu đóng ngoặc)
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
    """Thử sửa JSON bị cắt cụt từ Gemini (thiếu đóng ngoặc/quote)."""
    cleaned = text.strip()

    # Đảm bảo bắt đầu bằng {
    if not cleaned.startswith("{"):
        idx = cleaned.find("{")
        if idx == -1:
            return None
        cleaned = cleaned[idx:]

    # Thử thêm dần các ký tự đóng
    repairs = [
        '',           # nguyên bản
        '"}',         # thiếu đóng quote + brace
        '"]}'  ,      # thiếu đóng array + brace
        '"}]}',       # thiếu nhiều
        '"]}',        # thiếu đóng quote + array + brace
        '}',          # chỉ thiếu brace
    ]

    for suffix in repairs:
        try:
            data = json.loads(cleaned + suffix)
            if isinstance(data, dict) and "summary" in data:
                log.info("Da sua JSON bi cat cut thanh cong")
                return data
        except json.JSONDecodeError:
            continue

    # Fallback: regex extract summary
    import re
    match = re.search(r'"summary"\s*:\s*"((?:[^"\\]|\\.)*)"', cleaned)
    if match:
        summary = match.group(1)
        # Thử tìm tags
        tags_match = re.search(r'"tags"\s*:\s*\[(.*?)\]', cleaned)
        tags = []
        if tags_match:
            tags = [t.strip().strip('"') for t in tags_match.group(1).split(",")]
        log.info("Da extract summary bang regex fallback")
        return {"summary": summary, "tags": tags}

    return None


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
