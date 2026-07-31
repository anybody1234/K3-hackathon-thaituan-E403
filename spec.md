# AI SPEC — Tóm tắt & gợi ý bài đăng trên kênh #chia-sẻ · Nhóm thaituan · E403
Hướng: [x] B — Trợ lý Học viên (Discord)
Loại: [x] Tính năng mới

## §1. User & Job

- Job executor: Học viên khoá AI Thực Chiến, buổi tối vào kênh #chia-sẻ trên Discord server AI20K để tìm bài đáng đọc.
- Workflow: Mở Discord, vào #chia-sẻ, cuộn feed, mở từng bài đọc lướt, quyết định đọc kỹ hay bỏ, lặp lại đến khi tìm được bài hay hoặc hết kiên nhẫn.
- Core JTBD: Tìm nhanh bài chia sẻ hữu ích mà không phải cuộn qua hàng chục bài dài, trùng lặp hoặc không có giá trị.
- Problem statement: Học viên lướt kênh #chia-sẻ buổi tối, phần lớn bài dài hoặc trùng nội dung. Phải đọc lướt từng bài mới biết đáng hay không, mất 15-20 phút mà chỉ tìm được 1-2 bài hữu ích. Nhiều hôm bỏ cuộc tắt Discord luôn.
- Evidence:
  - Chuẩn A — Khảo sát (n=37, ngoài nhóm, log trong `phan-hoi-hoc-vien-KHAO-SAT.xlsx`):
    - 73% (27/37) cho rằng chỉ 5/10 bài gần nhất là đáng đọc.
    - 76% (28/37) thường xuyên hoặc thỉnh thoảng gặp kênh ngập bài AI viết hộ hoặc không giá trị.
    - 46% (17/37) chọn "thoát kênh, bỏ cuộc" khi gặp quá nhiều bài kém.
    - "Tóm tắt/gợi ý" được xếp ưu tiên cao nhất (TB 1.89/5), bỏ xa lọc bài (2.51), upvote (2.70), mentor (3.59), giới hạn bài (4.30).
    - Mức hữu ích trung bình kênh: 2.76/5.
  - Quote nguyên văn:
    1. "Có hôm cuộn gần 20 bài mới thấy 1 bài thật sự có insight, còn lại bỏ qua hết." — HV #17
    2. "Định lưu vài bài hay nhưng lọc mãi trong đống bài farm điểm nên bỏ cuộc, tắt Discord đi ngủ." — HV #4
    3. "Bài nào cũng mở bài - thân bài - kết luận như văn mẫu, đọc là biết AI viết." — HV #9
    4. "Đọc một bài 600 chữ về 'tư duy AI', hết bài mới nhận ra không có ví dụ nào áp dụng được." — HV #3
    5. "Tối Chủ nhật kênh ngập bài đăng cho đủ chỉ tiêu, đa số lướt qua là biết không có gì." — HV #7

## §2. Impact & quyết định chọn

| Ứng viên | Người gặp | Tần suất | Tốn gì mỗi lần | Build được không |
|---|---|---|---|---|
| A. Bot tóm tắt + gắn tag | 28/37 (76%) | Vài lần/tuần | 15-20 phút cuộn, nhiều hôm bỏ cuộc | Được, Gemini free tier + Discord bot framework |
| B. Bot Q&A trả lời câu hỏi | ~30% HV | 1-2 lần/tuần | 5-10 phút chờ trả lời | Cần knowledge base lớn, khó đảm bảo đúng |
| C. Tổng hợp hàng ngày cho TA | 3-5 TA | 1 lần/ngày | 30 phút đọc lại kênh | Ít người hưởng lợi |

Đã loại:
- B: Cost-of-error cao (sai kiến thức), cần knowledge base xây không kịp, VLearn tutor đã làm.
- C: Chỉ 3-5 người dùng, không giải quyết pain chính của học viên.

Chọn A: 76% gặp pain, tần suất cao, 62% xếp tóm tắt là ưu tiên số 1. Sai thì rẻ vì user vẫn thấy bài gốc.

## §3. Giải pháp tương tự đã nghiên cứu

- Slack AI Recap: Gom bài theo chu kỳ thành digest, user đọc 1 lần. Đáng học: batch thay vì real-time. Đáng né: tóm tắt quá ngắn mất ngữ cảnh. Mình khác: gắn tag chủ đề + nút feedback để cá nhân hoá.

- Discord TLDR Bot: User gọi `/tldr` để tóm tắt từng tin. Đáng học: user chủ động chọn bài. Đáng né: không scale khi kênh có chục bài/ngày. Mình khác: tự động batch + thêm `/ask` tìm bài theo chủ đề.

- Feedly AI: Thu thập bài, AI phân loại + gợi ý theo sở thích. Đáng học: feedback loop cá nhân hoá. Đáng né: cold start user mới. Mình khác: chạy trong Discord, cold start fallback về bài mới nhất.

## §4. Thiết kế

- Lát cắt: Một học viên lướt kênh #chia-sẻ buổi tối, AI tóm tắt mỗi bài mới thành 2-3 câu kèm tag chủ đề, học viên đọc tóm tắt rồi quyết định mở bài gốc để đọc kỹ.

- Non-goals:
  1. Không trả lời câu hỏi học thuật.
  2. Không moderate, xoá hay ẩn bài, chỉ tóm tắt.
  3. Không gửi tin nhắn riêng tự động.
  4. Không chấm điểm chất lượng bài.

- Mức prototype: Working
  - Thật: Digest (tóm tắt + tag qua Gemini), `/ask` (RAG search qua embedding + Gemini), feedback buttons (ghi DB, cập nhật profile).
  - Mock: `/foryou` popularity score cố định 0.5..

- Automation:
  - Digest: Automate — sai thì rẻ, user thấy bài gốc ngay cạnh, tự kiểm tra được.
  - `/ask`: Conditional — trả lời khi similarity > 0.3, không có thì nói "không tìm thấy".
  - `/foryou`: Augment — gợi ý danh sách, user tự chọn.

- §4b. Nguyên tắc đã áp dụng:

| Nguyên tắc | Áp vào đâu |
|---|---|
| G2 — Làm rõ AI tốt đến đâu | `/ask` hiện % độ liên quan cạnh mỗi kết quả (`ui/digest_embed.py:128`) |
| G8 — Gạt bỏ dễ dàng | `/ask`, `/foryou` trả ephemeral, chỉ người gọi thấy. Digest card kèm link gốc |
| G10 — Thu hẹp phạm vi khi nghi ngờ | `/ask` lọc similarity < 0.3 (`features/ask_bot.py:60`). Bài < 10 ký tự thì trả "chưa đủ" (`core/summarizer.py:53`) |
| G11 — Giải thích vì sao | `/ask` trả lời kèm trích dẫn [Bai N] + tóm tắt bài nguồn (`core/summarizer.py:153`) |
| G15 — Mời feedback | 3 nút Hay/Lưu/Bo qua, cập nhật profile sở thích (`ui/feedback_view.py`) |

## §5. Kiểu lỗi — 4 lớp chỗ khó + kịch bản

4 lớp:
- (1) Nguồn sự thật: AI bịa hoặc tóm tắt sai ý chính. Xử lý: hiện link bài gốc để user tự kiểm.
- (2) Mơ hồ, thiếu thông tin: Bài quá ngắn, chỉ emoji, link hỏng. Xử lý: trả "Nội dung chưa đủ".
- (3) Ngoài phạm vi: `/ask` hỏi deadline, thời tiết, thông tin cá nhân. Xử lý: trả "Không tìm thấy".
- (4) Đặc thù domain: Tag sai dẫn đến ping role nhầm, hoặc tóm tắt bài kỹ thuật sai logic.

| # | Tình huống | Lớp | Hành vi mong muốn | Nguyên tắc |
|---|---|---|---|---|
| 1 | Fetch link ra trang quảng cáo, AI tóm tắt nội dung quảng cáo | 1 | Dùng text gốc thay vì fetched content. Kèm link bài gốc | G2, G10 |
| 2 | AI tóm tắt sai logic code (nói "nhanh" trong khi bài hỏi vì sao chậm) | 1 | Tóm tắt trung thực, không review code. Hiện link gốc | G2 |
| 3 | Bài chỉ có emoji, không text | 2 | Trả "Nội dung chưa đủ", tag Khác | G10 |
| 4 | Bài có link nhưng 404 | 2 | Tóm tắt text gốc nếu đủ, không thì ghi "chưa đủ" | G10 |
| 5 | `/ask` hỏi deadline, DB không có | 3 | Trả "Không tìm thấy". Không bịa ngày | G10 |
| 6 | `/ask` hỏi thông tin cá nhân | 3 | Trả "Không tìm thấy" | G10 |
| 7 | Bài prompt engineering bị tag "Python", ping role nhầm | 4 | Ngưỡng confidence 0.6, không chắc thì tag Khác, không ping | G10, G2 |
| 8 | Bài chứa info kỹ thuật sai, AI tóm tắt trung thực nội dung sai | 4 | Bot chỉ tóm tắt, không fact-check. Hiện link gốc | G2 |
| 9 | Tất cả Gemini model hết quota | 2 | Fallback lấy 2 câu đầu + "[AI tạm nghỉ]". Không crash | G10 |
| 10 | User mới gọi `/foryou`, chưa có profile | 2 | Trả bài mới nhất thay vì rỗng | G8 |

## §6. Bốn đường đi của trải nghiệm

- Happy path: Bài mới trong #chia-sẻ, bot collect, flush mỗi 5 giờ, Gemini tóm tắt 2-3 câu + tag, đăng digest card kèm link gốc và nút feedback. User đọc, bấm Hay, profile cập nhật.

- Low-confidence: Bài dưới 10 ký tự (emoji, 1 từ). Trả "Nội dung chưa đủ", tag Khác, vẫn kèm link gốc.

- Failure: Tất cả Gemini model fail. Fallback lấy 2 câu đầu bài gốc + "[AI tạm nghỉ]". User vẫn thấy nội dung.

- Correction: User bấm Bỏ qua, profile giảm score tag đó (-0.3), `/foryou` giảm bài tương tự. Hay và Lưu tương thích nhau, bấm Bỏ qua thì disable hết.

- Ngoài phạm vi: `/ask` hỏi thứ không liên quan, similarity < 0.3, trả "Không tìm thấy bài liên quan".

- Đặc thù domain: Tag sai thì ngưỡng 0.6 chặn ping role nhầm. Bài sai kiến thức thì tóm tắt trung thực, hiện link gốc.

## §7. Kiểm thử

| Chiều | Định nghĩa | Chấm |
|---|---|---|
| Chính xác nội dung | Tóm tắt đúng ý chính, không thêm info không có trong bài | Pass/Fail |
| Tag đúng | It nhất 1 tag khớp chủ đề thật | Pass/Fail |
| Đúng cỡ | 1-4 câu | Pass/Fail |
| An toàn | Không bịa, không lộ PII. Điều kiện cứng | Pass/Fail |

Golden set: 25 case (`eval/test_cases.md`) — 8 bình thường, 4 không có info, 4 mơ hồ, 3 ngoài phạm vi, 3 hậu quả, 3 thực tế.

Quality bar: 75% trở lên qua bộ (18/25), và 0 lần bịa nội dung.

| Lượt | Ngày | Kết quả | Ghi chú |
|---|---|---|---|
| Product eval | 30/07/2026 | 25/25 (100%) | API hết quota, hầu hết output dùng fallback. Cần chạy lại khi có quota |
| Unit/integration | 30/07/2026 | 30/30 (100%) | Config, DB, link fetcher, embedder, summarizer, pipeline |

Chi tiết: `eval/eval_results.md`, `eval/test_results.md`.

Lượt 1 đạt 100% nhưng chất lượng thực chưa rõ vì API fallback. Khi Gemini hoạt động, các case TC01-TC08 có thể fail ở chiều Tag đúng. Cần chạy lại và ghi nhận trung thực.

## §8. Phân công & kế hoạch

| Phần | Người |
|---|---|
| Spec, evidence, khảo sát | Lục Minh Đức |
| Code bot, prompt, API | Phạm Nguyên Việt |
| Golden set, eval, demo | Phan Hoàng Long |

Willing users: Nguyễn Văn Đại, Trương Công Thái Đức, Đỗ Quang Huy

Validation CP5: Mời 5+ người ngoài nhóm dùng thử bot trên Discord thật. Giao task, quan sát im lặng, hỏi 3 câu (khó hiểu nhất? tin không? dùng thật không?). Log vào `validation/`.

Multi-prototype: Đã thử real-time vs batch. Chọn batch (mỗi 5 giờ) vì tránh rate limit, user đọc 1 lần cho gọn.

## §9. Changelog

| Thời điểm | Đổi gì | Vì sao |
|---|---|---|
| CP1 | Chốt hướng B, lát cắt tóm tắt bài chia sẻ | 76% gặp pain, 62% muốn tóm tắt |
| CP1-CP2 | Đổi real-time sang batch (5 giờ) | Rate limit, UX tốt hơn |
| CP2 | Thêm `/ask` | Học viên muốn tìm bài theo chủ đề |
| CP2-CP3 | Fallback multi-model | Gemini flash hết quota |
| CP3 | Smart fallback khi tất cả model fail | Bot không được crash khi API die |
| CP3-CP4 | Sửa feedback: Hay+Lưu tương thích, Bỏ qua loại trừ | User muốn bấm cả Hay và Lưu |
| CP4 | Chốt quality bar 75%, golden set 25 case | Chuẩn bị eval |
