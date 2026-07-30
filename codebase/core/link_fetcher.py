"""
Fetch nội dung từ URL trong bài đăng.

Khi bài chỉ có link (không kèm text giải thích),
bot cần fetch nội dung trang web rồi mới tóm tắt được.
"""
import logging
import re

import httpx
from bs4 import BeautifulSoup

import config

log = logging.getLogger(__name__)

# Regex bắt URL trong text
_URL_RE = re.compile(r"https?://[^\s<>\"']+")


def extract_urls(text: str) -> list[str]:
    """Trích tất cả URL từ đoạn text."""
    return _URL_RE.findall(text)


async def fetch_url_content(url: str) -> str | None:
    """
    Fetch một URL, trả về text nội dung chính (title + body).
    Trả None nếu thất bại.
    """
    try:
        async with httpx.AsyncClient(
            timeout=config.FETCH_TIMEOUT,
            follow_redirects=True,
            headers={"User-Agent": "DiscordBot (hackathon-digest-bot)"},
        ) as client:
            resp = await client.get(url)
            resp.raise_for_status()

            content_type = resp.headers.get("content-type", "")
            if "text/html" not in content_type and "text/plain" not in content_type:
                log.info("Bỏ qua URL không phải HTML: %s (%s)", url, content_type)
                return None

            return _extract_text_from_html(resp.text, url)

    except httpx.TimeoutException:
        log.warning("Timeout khi fetch %s", url)
    except httpx.HTTPStatusError as e:
        log.warning("HTTP %d khi fetch %s", e.response.status_code, url)
    except Exception as e:
        log.warning("Lỗi fetch %s: %s", url, e)
    return None


def _extract_text_from_html(html: str, url: str) -> str:
    """Rút nội dung chính từ HTML, bỏ nav/footer/script."""
    soup = BeautifulSoup(html, "html.parser")

    # Loại bỏ các phần tử không cần
    for tag in soup(["script", "style", "nav", "footer", "header", "aside", "form"]):
        tag.decompose()

    # Lấy title
    title = soup.title.string.strip() if soup.title and soup.title.string else ""

    # Ưu tiên thẻ article/main nếu có
    main = soup.find("article") or soup.find("main") or soup.find("body")
    if main is None:
        main = soup

    # Lấy text, gộp whitespace
    text = main.get_text(separator="\n", strip=True)

    # Cắt cho gọn
    if len(text) > config.MAX_FETCH_CONTENT_LENGTH:
        text = text[: config.MAX_FETCH_CONTENT_LENGTH] + "\n[...cắt bớt...]"

    result = f"Tiêu đề: {title}\nNguồn: {url}\n\n{text}" if title else text
    return result


async def fetch_content_for_message(message_text: str) -> str | None:
    """
    Nhận text tin nhắn, tìm URL đầu tiên và fetch nội dung.
    Trả None nếu không có URL hoặc fetch thất bại.
    """
    urls = extract_urls(message_text)
    if not urls:
        return None

    # Fetch URL đầu tiên (thường là link chính)
    for url in urls[:2]:  # Thử tối đa 2 URL
        content = await fetch_url_content(url)
        if content:
            return content

    return None
