"""
Bộ test đánh giá sản phẩm Discord AI Agent.

Chạy: python eval/run_tests.py
Kết quả lưu: eval/test_results.md
"""
import asyncio
import json
import os
import sys
import io
import traceback
from datetime import datetime, timezone
from pathlib import Path

# Fix Windows encoding
if sys.stdout.encoding != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")


# Thêm codebase vào path
sys.path.insert(0, str(Path(__file__).parent.parent / "codebase"))

import config
from storage.database import Database
from core import link_fetcher, embedder
from core.summarizer import summarize_and_tag, generate_rag_answer, _parse_response, _smart_fallback

# ═══════════════════════════════════════════════════════════
# BỘ CÂU THỬ
# ═══════════════════════════════════════════════════════════

RESULTS = []  # (test_id, name, passed, detail)


def record(test_id: str, name: str, passed: bool, detail: str = ""):
    RESULTS.append((test_id, name, passed, detail))
    status = "PASS" if passed else "FAIL"
    print(f"  [{status}] {test_id}: {name}")
    if detail and not passed:
        print(f"         -> {detail[:200]}")


async def run_all_tests():
    """Chạy tất cả test cases."""

    # ═══════════════════════════════════════════════════════
    # NHÓM 1: CONFIG — Cấu hình hệ thống
    # ═══════════════════════════════════════════════════════
    print("\n=== NHÓM 1: CONFIG ===")

    # T01: Config load đúng từ .env
    record("T01", "Config load DISCORD_BOT_TOKEN từ .env",
           len(config.DISCORD_BOT_TOKEN) > 10,
           f"Token length: {len(config.DISCORD_BOT_TOKEN)}")

    # T02: Config load API key
    record("T02", "Config load GOOGLE_API_KEY từ .env",
           len(config.GOOGLE_API_KEY) > 10,
           f"Key length: {len(config.GOOGLE_API_KEY)}")

    # T03: Config validate — thiếu token
    original_token = config.DISCORD_BOT_TOKEN
    config.DISCORD_BOT_TOKEN = ""
    errs = config.validate()
    config.DISCORD_BOT_TOKEN = original_token
    record("T03", "Config validate phát hiện thiếu token",
           any("DISCORD_BOT_TOKEN" in e for e in errs),
           f"Errors: {errs}")

    # T04: ALLOWED_TAGS parse đúng
    record("T04", "ALLOWED_TAGS parse từ .env",
           len(config.ALLOWED_TAGS) >= 4 and "AI" in config.ALLOWED_TAGS,
           f"Tags: {config.ALLOWED_TAGS}")

    # T05: TOPIC_ROLE_MAP parse đúng JSON
    record("T05", "TOPIC_ROLE_MAP parse JSON dict",
           isinstance(config.TOPIC_ROLE_MAP, dict) and len(config.TOPIC_ROLE_MAP) > 0,
           f"Map: {config.TOPIC_ROLE_MAP}")

    # ═══════════════════════════════════════════════════════
    # NHÓM 2: DATABASE — CRUD operations
    # ═══════════════════════════════════════════════════════
    print("\n=== NHÓM 2: DATABASE ===")

    db = Database(db_path=Path(__file__).parent / "test_bot.db")
    await db.connect()

    # T06: Database connect + schema creation
    record("T06", "Database connect và tạo schema",
           db._conn is not None, "")

    # T07: Save post
    post_id = await db.save_post(
        discord_msg_id="test_msg_001",
        channel_id="ch_001",
        author_id="user_001",
        author_name="TestUser",
        content="Bài test về AI và Machine Learning",
        fetched_content=None,
        summary="Tóm tắt test",
        tags=["AI", "Python"],
        embedding=None,
        jump_url="https://discord.com/test/001",
        created_at=datetime.now(timezone.utc),
    )
    record("T07", "Lưu bài mới vào DB",
           post_id is not None and post_id > 0,
           f"post_id={post_id}")

    # T08: Get post
    post = await db.get_post(post_id)
    record("T08", "Đọc bài từ DB",
           post is not None and post["author_name"] == "TestUser",
           f"author={post['author_name'] if post else 'None'}")

    # T09: Post exists check
    exists = await db.post_exists("test_msg_001")
    not_exists = await db.post_exists("nonexistent_msg")
    record("T09", "Kiểm tra bài đã tồn tại (chống trùng)",
           exists is True and not_exists is False,
           f"exists={exists}, not_exists={not_exists}")

    # T10: Save + get pending posts (batch mode)
    pending_post_id = await db.save_post(
        discord_msg_id="test_msg_002",
        channel_id="ch_001",
        author_id="user_002",
        author_name="PendingUser",
        content="Bài pending chưa xử lý",
        fetched_content=None,
        summary=None,  # Chưa tóm tắt
        tags=[],
        embedding=None,
        jump_url="https://discord.com/test/002",
        created_at=datetime.now(timezone.utc),
    )
    pending = await db.get_pending_posts()
    record("T10", "Lưu bài pending (batch) + lấy danh sách pending",
           len(pending) >= 1 and any(p["id"] == pending_post_id for p in pending),
           f"pending count={len(pending)}")

    # T11: Save reaction
    await db.save_reaction(user_id="user_001", post_id=post_id, reaction_type="like")
    reactions = await db.get_user_reactions("user_001")
    record("T11", "Lưu reaction (like) và đọc lại",
           len(reactions) >= 1 and reactions[0]["reaction_type"] == "like",
           f"reactions={len(reactions)}")

    # T12: User profile update
    await db.update_user_profile("user_001", "AI", 1.5)
    await db.update_user_profile("user_001", "Python", 1.0)
    profile = await db.get_user_profile("user_001")
    record("T12", "Cập nhật hồ sơ sở thích user",
           profile.get("AI", 0) == 1.5 and profile.get("Python", 0) == 1.0,
           f"profile={profile}")

    # T13: Reaction counts
    await db.save_reaction(user_id="user_002", post_id=post_id, reaction_type="like")
    await db.save_reaction(user_id="user_003", post_id=post_id, reaction_type="save")
    counts = await db.get_post_reaction_counts(post_id)
    record("T13", "Đếm reactions theo loại cho bài",
           counts.get("like", 0) >= 2 and counts.get("save", 0) >= 1,
           f"counts={counts}")

    # T14: Update AI results (batch mode)
    import numpy as np
    fake_emb = np.random.randn(768).astype(np.float32)
    await db.update_post_ai_results(
        post_id=pending_post_id,
        summary="Tóm tắt AI test",
        tags=["AI"],
        embedding=fake_emb,
    )
    updated = await db.get_post(pending_post_id)
    record("T14", "Cập nhật kết quả AI (summary, tags, embedding)",
           updated is not None and updated["summary"] == "Tóm tắt AI test",
           f"summary={updated['summary'] if updated else 'None'}")

    await db.close()
    # Cleanup
    try:
        os.remove(Path(__file__).parent / "test_bot.db")
    except Exception:
        pass

    # ═══════════════════════════════════════════════════════
    # NHÓM 3: LINK FETCHER — URL extraction + fetch
    # ═══════════════════════════════════════════════════════
    print("\n=== NHÓM 3: LINK FETCHER ===")

    # T15: Extract URLs from text
    urls = link_fetcher.extract_urls(
        "Check out https://example.com and http://test.org/page?q=1 xem nhé"
    )
    record("T15", "Trích xuất URLs từ text",
           len(urls) == 2 and "https://example.com" in urls,
           f"urls={urls}")

    # T16: No URLs in plain text
    urls_none = link_fetcher.extract_urls("Không có link gì ở đây")
    record("T16", "Text không có URL trả empty list",
           len(urls_none) == 0,
           f"urls={urls_none}")

    # T17: Fetch real URL
    fetched = await link_fetcher.fetch_url_content("https://example.com")
    record("T17", "Fetch nội dung từ URL thật (example.com)",
           fetched is not None and len(fetched) > 20,
           f"length={len(fetched) if fetched else 0}")

    # T18: Fetch invalid URL returns None
    bad = await link_fetcher.fetch_url_content("https://this-domain-does-not-exist-12345.com")
    record("T18", "URL không tồn tại trả về None",
           bad is None,
           f"result={'None' if bad is None else bad[:50]}")

    # ═══════════════════════════════════════════════════════
    # NHÓM 4: EMBEDDER — Vector operations
    # ═══════════════════════════════════════════════════════
    print("\n=== NHÓM 4: EMBEDDER ===")

    # T19: Create embedding
    emb = await embedder.create_embedding("Machine learning là một nhánh của trí tuệ nhân tạo")
    record("T19", "Tạo embedding vector từ text",
           emb is not None and len(emb) > 100,
           f"dims={len(emb) if emb is not None else 0}")

    # T20: Cosine similarity — similar texts
    emb1 = await embedder.create_embedding("Python là ngôn ngữ lập trình phổ biến")
    emb2 = await embedder.create_embedding("Python programming language rất được ưa chuộng")
    emb3 = await embedder.create_embedding("Công thức nấu phở bò Hà Nội ngon nhất")
    if emb1 is not None and emb2 is not None and emb3 is not None:
        sim_related = embedder.cosine_similarity(emb1, emb2)
        sim_unrelated = embedder.cosine_similarity(emb1, emb3)
        record("T20", "Cosine similarity: text liên quan > text không liên quan",
               sim_related > sim_unrelated,
               f"related={sim_related:.3f}, unrelated={sim_unrelated:.3f}")
    else:
        record("T20", "Cosine similarity (embedding API fail)",
               False, "Không tạo được embedding")

    # T21: find_similar
    if emb is not None:
        posts_mock = [
            {"id": 1, "embedding": emb, "summary": "AI post"},
            {"id": 2, "embedding": np.random.randn(len(emb)).astype(np.float32), "summary": "Random"},
        ]
        results = embedder.find_similar(emb, posts_mock, top_k=2)
        record("T21", "find_similar trả kết quả đúng thứ tự (post giống nhất đầu tiên)",
               len(results) == 2 and results[0][0]["id"] == 1 and results[0][1] > results[1][1],
               f"top score={results[0][1]:.3f}")
    else:
        record("T21", "find_similar (embedding API fail)", False, "Không có embedding")

    # ═══════════════════════════════════════════════════════
    # NHÓM 5: SUMMARIZER — AI tóm tắt
    # ═══════════════════════════════════════════════════════
    print("\n=== NHÓM 5: SUMMARIZER ===")

    # T22: Parse JSON response
    parsed = _parse_response('{"summary": "Bài về AI", "tags": ["AI"]}')
    record("T22", "Parse JSON response chuẩn",
           parsed is not None and parsed["summary"] == "Bài về AI",
           f"parsed={parsed}")

    # T23: Parse JSON with markdown code block
    parsed_md = _parse_response('```json\n{"summary": "Test", "tags": ["Web"]}\n```')
    record("T23", "Parse JSON bọc trong markdown code block",
           parsed_md is not None and parsed_md["summary"] == "Test",
           f"parsed={parsed_md}")

    # T24: Parse invalid JSON returns None
    parsed_bad = _parse_response("This is not JSON at all")
    record("T24", "Parse text không phải JSON trả None",
           parsed_bad is None,
           f"result={parsed_bad}")

    # T25: Smart fallback
    fallback = _smart_fallback("Đây là câu đầu tiên khá dài để test. Và đây là câu thứ hai cũng khá dài. Câu thứ ba nữa.")
    record("T25", "Smart fallback tạo tóm tắt khi AI fail",
           "[AI tạm nghỉ]" in fallback and len(fallback) > 20,
           f"fallback={fallback[:100]}")

    # T26: Summarize empty content
    result_empty = await summarize_and_tag("", "TestUser")
    record("T26", "Xử lý nội dung rỗng trả mặc định",
           result_empty["summary"] == "Nội dung chưa đủ để tóm tắt." and result_empty["tags"] == ["Khác"],
           f"result={result_empty}")

    # T27: Summarize real content (API call)
    test_content = """
    Hướng dẫn sử dụng Docker cho người mới bắt đầu.
    Docker là một nền tảng container hóa giúp đóng gói ứng dụng cùng với
    tất cả dependencies. Bài viết hướng dẫn cài đặt Docker, tạo Dockerfile,
    build image, và chạy container. Docker giúp deploy ứng dụng nhanh hơn
    và đồng nhất giữa các môi trường dev, staging, production.
    """
    result_real = await summarize_and_tag(test_content, "DevUser")
    # Nếu AI hoạt động: summary khác content gốc (tóm tắt thật)
    # Nếu AI fail: summary có "[AI tạm nghỉ]" prefix
    is_summarized = (
        result_real["summary"] != test_content.strip()
        and len(result_real["summary"]) > 10
    )
    record("T27", "Tóm tắt nội dung thực (API hoặc fallback)",
           is_summarized,
           f"summary={result_real['summary'][:100]}")

    # T28: Tags validation — invalid tags filtered
    parsed_invalid_tags = _parse_response('{"summary": "Test", "tags": ["InvalidTag", "AI", "FakeTag"]}')
    record("T28", "Lọc tag không hợp lệ, chỉ giữ tag trong ALLOWED_TAGS",
           parsed_invalid_tags is not None and "InvalidTag" not in parsed_invalid_tags["tags"] and "AI" in parsed_invalid_tags["tags"],
           f"tags={parsed_invalid_tags['tags'] if parsed_invalid_tags else 'None'}")

    # ═══════════════════════════════════════════════════════
    # NHÓM 6: INTEGRATION — End-to-end pipeline
    # ═══════════════════════════════════════════════════════
    print("\n=== NHÓM 6: INTEGRATION ===")

    # T29: Full pipeline — save pending + retrieve
    db2 = Database(db_path=Path(__file__).parent / "test_integration.db")
    await db2.connect()

    pid = await db2.save_post(
        discord_msg_id="integration_001",
        channel_id="ch_int",
        author_id="user_int",
        author_name="IntegrationUser",
        content="Tổng hợp các framework Python tốt nhất 2024: Django, FastAPI, Flask",
        fetched_content=None,
        summary=None,
        tags=[],
        embedding=None,
        jump_url="https://discord.com/integration/001",
        created_at=datetime.now(timezone.utc),
    )
    pending = await db2.get_pending_posts()
    record("T29", "Pipeline: save bài pending → đọc pending list",
           len(pending) >= 1,
           f"pending={len(pending)}")

    # T30: Full pipeline — update AI results + search
    if emb is not None:
        await db2.update_post_ai_results(pid, "Tổng hợp framework Python", ["Python", "Web"], emb)
        posts_with_emb = await db2.get_all_posts_with_embeddings()
        record("T30", "Pipeline: update AI → search posts with embeddings",
               len(posts_with_emb) >= 1 and posts_with_emb[0]["summary"] == "Tổng hợp framework Python",
               f"found={len(posts_with_emb)}")
    else:
        record("T30", "Pipeline: update + search (embedding API fail)", False, "")

    await db2.close()
    try:
        os.remove(Path(__file__).parent / "test_integration.db")
    except Exception:
        pass


def write_results():
    """Ghi kết quả ra file markdown."""
    total = len(RESULTS)
    passed = sum(1 for _, _, p, _ in RESULTS if p)
    failed = total - passed

    output_path = Path(__file__).parent / "test_results.md"

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("# Kết quả chạy thử — Discord AI Agent\n\n")
        f.write(f"**Ngày chạy:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write(f"## Tổng kết: {passed}/{total}\n\n")
        f.write(f"- ✅ Đạt: {passed}\n")
        f.write(f"- ❌ Fail: {failed}\n\n")
        f.write("---\n\n")
        f.write("## Bảng kết quả chi tiết\n\n")
        f.write("| # | Test ID | Tên câu thử | Kết quả | Chi tiết |\n")
        f.write("|---|---------|-------------|---------|----------|\n")

        for i, (tid, name, is_pass, detail) in enumerate(RESULTS, 1):
            status = "✅ PASS" if is_pass else "❌ FAIL"
            detail_clean = detail.replace("|", "\\|").replace("\n", " ")[:120]
            f.write(f"| {i} | {tid} | {name} | {status} | {detail_clean} |\n")

        f.write(f"\n---\n\n**Kết quả: {passed}/{total}**\n")

    print(f"\n{'='*50}")
    print(f"KET QUA: {passed}/{total}")
    print(f"{'='*50}")
    print(f"Chi tiet luu tai: {output_path}")

    return passed, total


if __name__ == "__main__":
    print("=" * 50)
    print("CHAY BO TEST — Discord AI Agent")
    print("=" * 50)

    asyncio.run(run_all_tests())
    write_results()
