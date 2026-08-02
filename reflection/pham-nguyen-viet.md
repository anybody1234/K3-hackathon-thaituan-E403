# Reflection — Phạm Nguyên Việt
Role: Coding, testing

## Tôi đã làm gì

- Xây dựng toàn bộ codebase Discord bot bằng Python (discord.py)
- Thiết kế pipeline: collect bài -> batch flush mỗi 5h -> AI tóm tắt + tag -> đăng digest card
- Viết system prompt cho Gemini/OpenRouter để tóm tắt + gắn tag chính xác
- Xây dựng hệ thống fallback: khi API fail -> smart_fallback lấy 2 câu đầu + "[AI tạm nghỉ]"
- Implement RAG search cho /ask: embedding + cosine similarity + ngưỡng 0.3
- Implement /foryou: ranking theo tag_match x recency x popularity
- Thiết kế feedback loop: 3 nút Hay/Lưu/Bỏ qua cập nhật user profile trong SQLite
- Xử lý edge case: bài quá ngắn, link hỏng, rate limit, cold start user mới
- Chuyển từ Google Gemini trực tiếp sang OpenRouter để tránh rate limit
- Viết unit test và product eval script để kiểm tra chất lượng

## Thách thức gặp phải

- Rate limit Gemini free tier: chạy 25 bài liên tục là bị chặn. Phải thiết kế fallback chain và delay giữa các call
- Encoding UTF-8 trên Windows: log tiếng Việt bị lỗi, phải wrap stdout/stderr
- Discord forum channel khác text channel: cần xử lý riêng on_thread_create và backfill
- Persistent view: khi bot restart, buttons cũ mất callback. Phải dùng PersistentFeedbackView với custom_id cố định

## Tôi đã học được gì

- Thiết kế automation level phù hợp: digest (automate), /ask (conditional), /foryou (augment)
- Fallback không chỉ là try-catch, mà phải đảm bảo user vẫn nhận được giá trị (dù là 2 câu đầu)
- Prompt engineering cho summarize: cần giới hạn độ dài, cấm bịa, yêu cầu JSON thuần
- Batch processing tiết kiệm API call và tốt hơn cho UX so với real-time

## Nếu làm lại tôi sẽ

- Dùng OpenRouter từ đầu thay vì Gemini trực tiếp để tránh vấn đề rate limit
- Viết unit test song song với code thay vì viết sau
- Thiết kế database schema kỹ hơn từ đầu, tránh migration giữa chừng
