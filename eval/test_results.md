# Kết quả chạy thử — Discord AI Agent

**Ngày chạy:** 2026-07-31 00:26:17

## Tổng kết: 30/30

- ✅ Đạt: 30
- ❌ Fail: 0

---

## Bảng kết quả chi tiết

| # | Test ID | Tên câu thử | Kết quả | Chi tiết |
|---|---------|-------------|---------|----------|
| 1 | T01 | Config load DISCORD_BOT_TOKEN từ .env | ✅ PASS | Token length: 72 |
| 2 | T02 | Config load GOOGLE_API_KEY từ .env | ✅ PASS | Key length: 53 |
| 3 | T03 | Config validate phát hiện thiếu token | ✅ PASS | Errors: ['Thiếu DISCORD_BOT_TOKEN trong .env'] |
| 4 | T04 | ALLOWED_TAGS parse từ .env | ✅ PASS | Tags: ['AI', 'Web', 'Backend', 'Data', 'DevOps', 'Mobile', 'Design', 'Career', 'Python', 'LLM', 'Prompt', 'Product'] |
| 5 | T05 | TOPIC_ROLE_MAP parse JSON dict | ✅ PASS | Map: {'AI': 'AI', 'Web': 'Web', 'Backend': 'Backend', 'Data': 'Data', 'DevOps': 'DevOps', 'LLM': 'LLM'} |
| 6 | T06 | Database connect và tạo schema | ✅ PASS |  |
| 7 | T07 | Lưu bài mới vào DB | ✅ PASS | post_id=1 |
| 8 | T08 | Đọc bài từ DB | ✅ PASS | author=TestUser |
| 9 | T09 | Kiểm tra bài đã tồn tại (chống trùng) | ✅ PASS | exists=True, not_exists=False |
| 10 | T10 | Lưu bài pending (batch) + lấy danh sách pending | ✅ PASS | pending count=2 |
| 11 | T11 | Lưu reaction (like) và đọc lại | ✅ PASS | reactions=1 |
| 12 | T12 | Cập nhật hồ sơ sở thích user | ✅ PASS | profile={'AI': 1.5, 'Python': 1.0} |
| 13 | T13 | Đếm reactions theo loại cho bài | ✅ PASS | counts={'like': 2, 'save': 1} |
| 14 | T14 | Cập nhật kết quả AI (summary, tags, embedding) | ✅ PASS | summary=Tóm tắt AI test |
| 15 | T15 | Trích xuất URLs từ text | ✅ PASS | urls=['https://example.com', 'http://test.org/page?q=1'] |
| 16 | T16 | Text không có URL trả empty list | ✅ PASS | urls=[] |
| 17 | T17 | Fetch nội dung từ URL thật (example.com) | ✅ PASS | length=179 |
| 18 | T18 | URL không tồn tại trả về None | ✅ PASS | result=None |
| 19 | T19 | Tạo embedding vector từ text | ✅ PASS | dims=3072 |
| 20 | T20 | Cosine similarity: text liên quan > text không liên quan | ✅ PASS | related=0.863, unrelated=0.553 |
| 21 | T21 | find_similar trả kết quả đúng thứ tự (post giống nhất đầu tiên) | ✅ PASS | top score=1.000 |
| 22 | T22 | Parse JSON response chuẩn | ✅ PASS | parsed={'summary': 'Bài về AI', 'tags': ['AI']} |
| 23 | T23 | Parse JSON bọc trong markdown code block | ✅ PASS | parsed={'summary': 'Test', 'tags': ['Web']} |
| 24 | T24 | Parse text không phải JSON trả None | ✅ PASS | result=None |
| 25 | T25 | Smart fallback tạo tóm tắt khi AI fail | ✅ PASS | fallback=[AI tạm nghỉ] Đây là câu đầu tiên khá dài để test. Và đây là câu thứ hai cũng khá dài |
| 26 | T26 | Xử lý nội dung rỗng trả mặc định | ✅ PASS | result={'summary': 'Nội dung chưa đủ để tóm tắt.', 'tags': ['Khác']} |
| 27 | T27 | Tóm tắt nội dung thực (API hoặc fallback) | ✅ PASS | summary=[AI tạm nghỉ] Hướng dẫn sử dụng Docker cho người mới bắt đầu. Docker là một nền tảng container hóa g |
| 28 | T28 | Lọc tag không hợp lệ, chỉ giữ tag trong ALLOWED_TAGS | ✅ PASS | tags=['AI'] |
| 29 | T29 | Pipeline: save bài pending → đọc pending list | ✅ PASS | pending=1 |
| 30 | T30 | Pipeline: update AI → search posts with embeddings | ✅ PASS | found=1 |

---

**Kết quả: 30/30**
