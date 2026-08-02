# Feedback Log — Vong User Test CP5

Ngay: 31/07/2026
So nguoi thu: 5 (ngoai nhom)
Phuong phap: Moi dung thu bot tren Discord that, quan sat, hoi phan hoi sau khi dung

## Danh sach nguoi thu

| # | Ho ten | Ghi chu |
|---|--------|---------|
| 1 | Nguyen Van Dai | Hoc vien khoa AI Thuc Chien |
| 2 | Truong Cong Thai Duc | Hoc vien khoa AI Thuc Chien |
| 3 | Do Quang Huy | Hoc vien khoa AI Thuc Chien |
| 4 | Le Nguyen Minh Duc | Hoc vien khoa AI Thuc Chien |
| 5 | Nguyen Quang Vinh | Hoc vien khoa AI Thuc Chien |

## Phan hoi chi tiet

### 1. Nguyen Van Dai

> "Tom tat doc nhanh hon nhieu so voi mo tung bai, nhung may bai ngan kieu chi co link thi tom tat khong noi duoc gi, doc xong van phai bam vao bai goc."

- Tinh nang lien quan: Digest (tom tat tu dong)
- Van de: Bai chi co link, khong co text -> tom tat khong co gia tri
- Muc do: Han che da biet (spec S5 kich ban so 4)

### 2. Truong Cong Thai Duc

> "Minh thu /ask hoi ve Docker thi ra dung bai lien quan, nhung tag hien Khac thay vi DevOps, hoi kho loc theo chu de."

- Tinh nang lien quan: /ask (semantic search), Tag
- Van de: Tag sai chu de (Docker nen la DevOps nhung hien Khac)
- Muc do: Van de da biet (spec S5 kich ban so 7, nguong confidence 0.6)

### 3. Do Quang Huy

> "Nut Hay voi Luu bam xong biet ngay la da ghi nhan, nhung minh khong hieu Luu khac Hay cho nao."

- Tinh nang lien quan: Feedback buttons
- Van de: Khong phan biet duoc Hay va Luu
- Muc do: UX chua ro rang

### 4. Le Nguyen Minh Duc

> "Digest gom lai doc 1 lan thay tien, khong bi ngap nhu cuon kenh chia se. Ma cho 5 tieng hoi lau, bai moi dang ma phai doi."

- Tinh nang lien quan: Digest (batch cycle)
- Van de: Chu ky 5 gio qua lau
- Muc do: Trade-off da biet (giam xuong se dinh rate limit Gemini free tier)

### 5. Nguyen Quang Vinh

> "Thu /foryou thi ra may bai moi nhat chu chua thay ca nhan hoa gi, chac do minh moi bam feedback co 1-2 lan."

- Tinh nang lien quan: /foryou (goi y ca nhan)
- Van de: Cold start — chua du du lieu de ca nhan hoa
- Muc do: Han che da biet (spec S6 duong di cold start, fallback ve bai moi nhat)

## Thay doi sau phan hoi

| # | Phan hoi | Hanh dong | Trang thai |
|---|----------|-----------|------------|
| 1 | Khong phan biet Hay va Luu (Huy) | Them dong giai thich trong ephemeral: Hay = bai huu ich, Luu = muon doc lai sau | Da sua |
| 2 | Chu ky 5h qua lau (Duc) | Giu nguyen 5h vi rate limit free tier. Ghi backlog: giam 1-2h khi co API tra phi | Giu nguyen |
| 3 | Tag sai chu de (Thai Duc) | Da ghi trong spec S5. Can tune prompt cho AI phan loai chinh xac hon | Backlog |
| 4 | Bai chi co link tom tat khong co gia tri (Dai) | Han che da biet. Bot van hien link goc de user tu doc | Giu nguyen |
| 5 | Cold start /foryou (Vinh) | Hoat dong dung thiet ke: fallback bai moi nhat khi chua du profile | Giu nguyen |

## Tong ket

- 5/5 nguoi dung duoc bot, khong ai gap crash hay loi nghiem trong
- Tinh nang duoc danh gia cao nhat: Digest tom tat (tiet kiem thoi gian doc)
- Van de chinh: tag chua chinh xac, UX nut feedback chua ro nghia
- 1 thay doi da ap dung ngay: giai thich Hay vs Luu trong ephemeral message
- 2 van de ghi backlog: tune prompt tag, giam chu ky batch khi co API tra phi
