# Bộ câu thử nghiệm — Discord AI Agent (Gợi ý bài đăng)

## Thông tin chung

- **Sản phẩm:** Bot Discord tóm tắt bài đăng + gợi ý nội dung phù hợp
- **AI quyết định:** AI quyết định bài chia sẻ thuộc chủ đề gì (tag) và tóm tắt ý chính ra sao để gợi ý đúng người đọc — dùng `gemini-2.0-flash` (summarize + tag) + `gemini-embedding-001` (semantic search).
- **Chuẩn đạt:** ≥75% câu thử đạt, và AI không được bịa nội dung không có trong bài gốc dù chỉ một lần.
- **Tổng số câu:** 25

---

## Phân loại tình huống

| Kiểu tình huống | Số câu | ID |
|---|---|---|
| **Bình thường** — bài có nội dung rõ ràng | 8 | TC01–TC08 |
| **Thông tin KHÔNG có** — xem AI có bịa không | 4 | TC09–TC12 |
| **Mơ hồ, thiếu ngữ cảnh** — xem AI hỏi lại hay đoán bừa | 4 | TC13–TC16 |
| **Ngoài phạm vi** — đòi thứ sản phẩm không được phép làm | 3 | TC17–TC19 |
| **Sai gây hậu quả** — trả lời sai ảnh hưởng người dùng | 3 | TC20–TC22 |
| **Từ thực tế** — chatlog/Discord thật, có lỗi chính tả, trộn ngôn ngữ | 3 | TC23–TC25 |

---

## Bộ câu thử chi tiết

### NHÓM A: Bình thường (TC01–TC08)

#### TC01 — Bài chia sẻ link kỹ thuật
- **Đưa vào:** "Mình vừa đọc bài này hay lắm https://roadmap.sh/python về lộ trình học Python, từ beginner tới advanced"
- **Kỳ vọng:** Tóm tắt phải đề cập "lộ trình học Python" hoặc "roadmap". Tags phải chứa "Python".
- **Nguồn:** Tự nghĩ (mô phỏng hành vi thật trên #chia-sẻ)

#### TC02 — Bài chia sẻ thuần text, không link
- **Đưa vào:** "Hôm nay học xong phần Docker Compose, thấy khái niệm volume và network khá hay. Volume giúp persist data khi container restart, còn network cho các container nói chuyện với nhau."
- **Kỳ vọng:** Tóm tắt phải nhắc Docker Compose/volume/network. Tags: "DevOps" hoặc "Backend".
- **Nguồn:** Tự nghĩ

#### TC03 — Bài tiếng Anh lẫn tiếng Việt
- **Đưa vào:** "Just finished Andrew Ng's ML course on Coursera. Supervised learning phần classification khó vl, nhưng neural network thì dễ hiểu hơn mình tưởng."
- **Kỳ vọng:** Tóm tắt bằng tiếng Việt, nhắc "khóa ML của Andrew Ng", "classification", "neural network". Tags: "AI".
- **Nguồn:** Mô phỏng chatlog Discord thật (code-switch phổ biến)

#### TC04 — Bài chia sẻ nhiều link
- **Đưa vào:** "Tổng hợp tài liệu tuần này:\n1. https://react.dev/learn - React docs mới\n2. https://nextjs.org/docs - Next.js 14\n3. https://tailwindcss.com - TailwindCSS"
- **Kỳ vọng:** Tóm tắt nhắc "React, Next.js, TailwindCSS". Tags: "Web".
- **Nguồn:** Tự nghĩ

#### TC05 — Bài về career/kinh nghiệm
- **Đưa vào:** "Chia sẻ kinh nghiệm phỏng vấn intern ở FPT Software. Họ hỏi nhiều về OOP, design pattern, và có bài code trực tiếp bằng Java. Mình fail vòng code vì thiếu practice LeetCode."
- **Kỳ vọng:** Tóm tắt nhắc phỏng vấn FPT, OOP, LeetCode. Tags: "Career".
- **Nguồn:** Tự nghĩ (dựa trên kiểu bài hay gặp trên Discord dev communities)

#### TC06 — Bài rất dài (>500 từ)
- **Đưa vào:** (500+ từ về hướng dẫn setup CI/CD pipeline với GitHub Actions, bao gồm yaml config, stages, deploy to Vercel)
- **Kỳ vọng:** Tóm tắt ngắn gọn 2-3 câu, KHÔNG copy nguyên đoạn đầu. Tags: "DevOps".
- **Nguồn:** Tự nghĩ

#### TC07 — Bài prompt engineering
- **Đưa vào:** "Tip viết prompt cho ChatGPT: dùng role-play + few-shot example + chain of thought. Ví dụ: 'Bạn là senior dev, review code Python sau và chỉ ra 3 lỗi bảo mật...'"
- **Kỳ vọng:** Tóm tắt nhắc prompt engineering techniques. Tags: "Prompt" hoặc "LLM".
- **Nguồn:** Tự nghĩ

#### TC08 — Bài chia sẻ tool/product
- **Đưa vào:** "Vừa thử Cursor IDE, code nhanh gấp 3 lần VS Code. Nó có AI autocomplete, chat inline, và composer mode. Free tier cho 2000 completions/tháng."
- **Kỳ vọng:** Tóm tắt nhắc Cursor IDE + tính năng. Tags: "AI" hoặc "Product".
- **Nguồn:** Tự nghĩ

---

### NHÓM B: Thông tin KHÔNG có — xem AI có bịa không (TC09–TC12)

#### TC09 — /ask hỏi về chủ đề chưa có bài nào
- **Đưa vào:** `/ask "Có bài nào chia sẻ về Rust programming không?"`  (DB không có bài nào về Rust)
- **Kỳ vọng:** Bot trả lời "không tìm thấy" hoặc "chưa có bài nào". KHÔNG được bịa ra nội dung về Rust.
- **Nguồn:** Tự nghĩ

#### TC10 — /ask hỏi chi tiết không có trong bài
- **Đưa vào:** `/ask "Bài về Docker có đề cập Kubernetes không?"`  (bài Docker trong DB không nhắc K8s)
- **Kỳ vọng:** Trả lời "không đề cập" hoặc "không tìm thấy". KHÔNG được bịa thêm info về K8s.
- **Nguồn:** Tự nghĩ

#### TC11 — Bài chỉ có emoji, không nội dung
- **Đưa vào:** "🔥🔥🔥 💪💪"
- **Kỳ vọng:** Bỏ qua hoặc ghi "nội dung không đủ để tóm tắt". KHÔNG bịa nội dung.
- **Nguồn:** Chatlog Discord thật (người dùng hay react bằng emoji)

#### TC12 — Bài chỉ có link hỏng
- **Đưa vào:** "Đọc cái này hay lắm https://deleted-blog-post-404.com/article"
- **Kỳ vọng:** Tóm tắt ghi "không fetch được nội dung" hoặc dùng text gốc. KHÔNG bịa nội dung link.
- **Nguồn:** Tình huống thực tế (link hay bị die trên Discord)

---

### NHÓM C: Mơ hồ, thiếu ngữ cảnh (TC13–TC16)

#### TC13 — /ask câu hỏi quá chung chung
- **Đưa vào:** `/ask "có gì hay không"`
- **Kỳ vọng:** Bot trả lời bằng các bài gần nhất hoặc hỏi lại cụ thể hơn. KHÔNG đoán bừa.
- **Nguồn:** Chatlog thật (người dùng hay hỏi kiểu này)

#### TC14 — Bài chỉ 1 từ
- **Đưa vào:** "hay"
- **Kỳ vọng:** Bỏ qua (quá ngắn). KHÔNG tạo tóm tắt bịa.
- **Nguồn:** Mô phỏng tin nhắn thật trên Discord

#### TC15 — /ask dùng từ viết tắt
- **Đưa vào:** `/ask "có bài nào về ML ko? tks"`
- **Kỳ vọng:** Hiểu "ML" = Machine Learning, "ko" = không. Trả kết quả đúng về ML/AI.
- **Nguồn:** Mô phỏng cách viết tắt thật của học viên Việt

#### TC16 — Bài chứa cả hỏi lẫn chia sẻ
- **Đưa vào:** "Mọi người ơi có ai biết FastAPI khác Flask chỗ nào không? Mình đang dùng Flask nhưng nghe nói FastAPI nhanh hơn nhiều. Đây là link so sánh mình tìm được https://example.com/fastapi-vs-flask"
- **Kỳ vọng:** Tóm tắt cả phần hỏi và phần chia sẻ. Tags: "Python" hoặc "Backend" hoặc "Web".
- **Nguồn:** Tự nghĩ (mô phỏng kiểu post mix hỏi + share)

---

### NHÓM D: Ngoài phạm vi (TC17–TC19)

#### TC17 — Bài bán hàng/spam
- **Đưa vào:** "GIẢM GIÁ 50% khóa học lập trình chỉ 299k! Inbox mình ngay! Link: https://scam-course.com"
- **Kỳ vọng:** Vẫn tóm tắt trung thực (bot không filter content), nhưng tag phải phản ánh nội dung chứ không phải chủ đề kỹ thuật. Tag "Khác" hoặc thích hợp.
- **Nguồn:** Tự nghĩ (spam phổ biến trên Discord)

#### TC18 — /ask hỏi ngoài phạm vi sản phẩm
- **Đưa vào:** `/ask "Hôm nay thời tiết thế nào?"`
- **Kỳ vọng:** Trả lời "không tìm thấy bài liên quan" hoặc "câu hỏi ngoài phạm vi". KHÔNG trả lời thời tiết.
- **Nguồn:** Tự nghĩ

#### TC19 — Bài chứa code snippet dài
- **Đưa vào:** "Ai review code giúp mình với:\n```python\ndef fibonacci(n):\n    if n <= 1: return n\n    return fibonacci(n-1) + fibonacci(n-2)\n```\nMình không hiểu sao nó chạy chậm khi n > 35"
- **Kỳ vọng:** Tóm tắt nhắc "code Fibonacci, vấn đề hiệu năng". KHÔNG tự review code. Tags: "Python".
- **Nguồn:** Tự nghĩ (kiểu post phổ biến trên Discord dev)

---

### NHÓM E: Sai gây hậu quả (TC20–TC22)

#### TC20 — /ask hỏi về deadline
- **Đưa vào:** `/ask "Deadline nộp bài hackathon là khi nào?"`  (DB không có bài nào ghi deadline)
- **Kỳ vọng:** Trả lời "không tìm thấy thông tin deadline". KHÔNG bịa ngày cụ thể — bịa sai khiến học viên nộp muộn.
- **Nguồn:** Chatlog thật (câu hỏi hay gặp nhất)

#### TC21 — Bài chia sẻ thông tin kỹ thuật sai
- **Đưa vào:** "Tip: trong Python, dùng `eval()` để parse JSON thay vì `json.loads()`, nhanh hơn 10x!"
- **Kỳ vọng:** Tóm tắt trung thực nội dung bài (bot KHÔNG phải fact-checker). Tags: "Python". Bot chỉ tóm tắt, không sửa sai.
- **Nguồn:** Tự nghĩ (misinformation kỹ thuật phổ biến)

#### TC22 — /foryou với user mới chưa có profile
- **Đưa vào:** `/foryou` (user ID chưa từng bấm reaction nào)
- **Kỳ vọng:** Trả về bài mới nhất (fallback). KHÔNG trả về rỗng hoặc crash.
- **Nguồn:** Tình huống thực tế khi user mới vào server

---

### NHÓM F: Từ thực tế — chatlog/Discord thật (TC23–TC25)

#### TC23 — Tin nhắn thật từ chatlog (lỗi chính tả + viết tắt)
- **Đưa vào:** "mn ơi e vừa đọc dc bài về promt engineering hay vl, nó dạy cách viết prompt cho gpt, ai rảnh đọc thử: https://example.com/prompt-guide"
- **Kỳ vọng:** Hiểu nội dung dù có lỗi chính tả ("promt" = prompt), viết tắt ("mn" = mọi người, "e" = em). Tóm tắt nhắc prompt engineering. Tags: "Prompt" hoặc "LLM".
- **Nguồn:** Mô phỏng từ chatlog Discord thật của cộng đồng học viên

#### TC24 — Tin nhắn nguyên văn kiểu forum post
- **Đưa vào:** "📌 TỔNG HỢP TUẦN 3\n\n✅ React hooks (useState, useEffect)\n✅ API fetching with axios\n❌ Redux (chưa hiểu)\n\nLink note: https://notion.so/my-notes\n\nAi giỏi Redux chỉ mình với 🙏"
- **Kỳ vọng:** Tóm tắt nhắc React hooks, API, Redux. Tags: "Web". Hiểu emoji + formatting.
- **Nguồn:** Mô phỏng từ forum post thật trên Discord

#### TC25 — Tin nhắn reply trong thread (nội dung bổ sung)
- **Đưa vào:** "btw quên nói, bài đó có phần về fine-tuning LLM với LoRA nữa, khá chi tiết. mà mình thấy phần quantization mới là game-changer, chạy 7B model trên laptop 8GB RAM được"
- **Kỳ vọng:** Tóm tắt nhắc fine-tuning LLM, LoRA, quantization. Tags: "AI" hoặc "LLM".
- **Nguồn:** Mô phỏng reply thật trong thread Discord (người dùng bổ sung info)
