# Reflection — Phan Hoàng Long
Role: Thu thập dữ liệu khảo sát, chuẩn bị mock data

## Tôi đã làm gì

- Thu thập dữ liệu khảo sát từ học viên: phát form, theo dõi response, xác minh người trả lời ngoài nhóm
- Tổng hợp và làm sạch dữ liệu khảo sát (n=37): loại response trùng, chuẩn hoá format
- Chuẩn bị mock data cho testing: tạo các mẫu bài đăng mô phỏng tình huống thật (bài bình thường, bài chỉ có link, bài spam, bài emoji, bài tiếng Anh lẫn tiếng Việt)
- Thiết kế golden set 25 test case từ mock data, chia 6 nhóm: bình thường (8), thiếu info (4), mơ hồ (4), ngoài phạm vi (3), hậu quả (3), thực tế (3)
- Hỗ trợ tổ chức vòng user test CP5: liên hệ 5 người ngoài nhóm, hướng dẫn cách dùng bot
- Ghi chép feedback log từ vòng user test

## Thách thức gặp phải

- Thu thập khảo sát đủ 37 người ngoài nhóm mất thời gian, phải nhắn tin từng người và theo dõi ai đã trả lời
- Mock data phải đa dạng đủ để phủ 6 nhóm test case: bài bình thường, bài rỗng, bài mơ hồ, bài spam, bài sai kỹ thuật, bài thật từ Discord
- Làm sạch dữ liệu khảo sát: một số response điền thiếu hoặc format không nhất quán
- Liên hệ người thử user test: phải giải thích cách dùng bot và cho họ thời gian thử, sau đó thu thập phản hồi

## Tôi đã học được gì

- Dữ liệu khảo sát phải có log xác minh (ai trả lời, khi nào) để đạt chuẩn evidence A
- Mock data tốt phải sát thực tế: lấy từ chatlog thật, không tự nghĩ ra
- User test cho thấy những vấn đề mà test tự động không bắt được (VD: không hiểu Hay vs Lưu là gì)
- Feedback từ người dùng thật giá trị hơn giả định của nhóm

## Nếu làm lại tôi sẽ

- Thu thập dữ liệu khảo sát sớm hơn để có thời gian làm nhiều vòng
- Lấy nhiều mock data từ chatlog thật hơn (hiện 3/25 case từ data thật, nên >= 10)
- Chuẩn bị sẵn form phản hồi có cấu trúc cho vòng user test thay vì hỏi tự do
