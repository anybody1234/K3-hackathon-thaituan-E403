"""
Cấu hình trung tâm — load từ .env, dùng xuyên suốt bot.
"""
import json
import os
from pathlib import Path

from dotenv import load_dotenv

# Load .env từ thư mục chứa file này
load_dotenv(Path(__file__).parent / ".env")


# ── Discord ──────────────────────────────────────────────
DISCORD_BOT_TOKEN: str = os.getenv("DISCORD_BOT_TOKEN", "")
SOURCE_CHANNEL_NAME: str = os.getenv("SOURCE_CHANNEL_NAME", "chia-sẻ")
DIGEST_CHANNEL_NAME: str = os.getenv("DIGEST_CHANNEL_NAME", "tóm-tắt-chia-sẻ")

# ── Google Gemini ────────────────────────────────────────
GOOGLE_API_KEY: str = os.getenv("GOOGLE_API_KEY", "")
GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "gemini-embedding-001")

# ── Tags & Roles ─────────────────────────────────────────
ALLOWED_TAGS: list[str] = [
    t.strip()
    for t in os.getenv("ALLOWED_TAGS", "AI,Web,Backend,Data").split(",")
    if t.strip()
]

# Mapping: tag name → role name trên server Discord
# Bot sẽ tự tìm role object theo tên
_role_map_raw = os.getenv("TOPIC_ROLE_MAP", "{}")
TOPIC_ROLE_MAP: dict[str, str] = json.loads(_role_map_raw)

# ── Paths ────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent
DB_PATH = BASE_DIR / "data" / "bot.db"

# ── Tuning ───────────────────────────────────────────────
# Độ dài tối đa nội dung fetch từ link (chars)
MAX_FETCH_CONTENT_LENGTH: int = 4000
# Timeout fetch link (seconds)
FETCH_TIMEOUT: int = 8
# Số bài tối đa trả về cho /ask và /foryou
TOP_K_RESULTS: int = 5
# Cosine similarity threshold cho role ping (tránh ping nhầm)
TAG_CONFIDENCE_THRESHOLD: float = 0.6
# Chu kỳ batch digest (giờ) — bot tích lũy bài rồi đăng hàng loạt
DIGEST_INTERVAL_HOURS: float = float(os.getenv("DIGEST_INTERVAL_HOURS", "5"))
# Delay giữa các lần gọi Gemini API (giây) — tránh rate limit
API_CALL_DELAY: float = float(os.getenv("API_CALL_DELAY", "2"))


def validate() -> list[str]:
    """Kiểm tra config thiếu gì, trả danh sách lỗi."""
    errors = []
    if not DISCORD_BOT_TOKEN:
        errors.append("Thiếu DISCORD_BOT_TOKEN trong .env")
    if not GOOGLE_API_KEY:
        errors.append("Thiếu GOOGLE_API_KEY trong .env")
    return errors
