# Antigravity Suite

Bộ công cụ tiêu chuẩn và toàn diện dành cho Antigravity IDE, bao gồm: **Bộ quy tắc toàn cục (Global Rules)**, **Hệ thống Hook tự động hóa (Lifecycle Hooks)** và **2 Tiện ích mở rộng cốt lõi (Voice Selector & Context Monitor)**.

---

## 📁 Cấu trúc kho lưu trữ

```text
antigravity-suite/
├── .gitignore                          # Tệp loại trừ rác, tệp tạm và nhật ký phát sinh
├── README.md                           # Tài liệu tổng quan và hướng dẫn sử dụng
├── install.ps1                         # Kịch bản cài đặt tự động một click cho Windows
│
├── global/                             # Cấu hình quy chuẩn toàn cục của hệ thống
│   ├── GEMINI.md                       # 9 luật cốt lõi và nguyên tắc làm việc chung
│   ├── config/
│   │   └── hooks.json                  # Cấu hình kích hoạt Hook (PreInvocation & Stop)
│   └── scripts/
│       ├── enforce_rules.js            # Nhắc nhở quy tắc & quản lý tiến trình độc lập
│       └── voice_notify.js             # Bộ máy phát âm thanh thông báo tiếng Việt
│
└── extensions/                         # 2 Tiện ích mở rộng cần thiết
    ├── antigravity-voice-selector/     # Tiện ích chọn & tải giọng đọc AI trên Status Bar
    │   ├── package.json
    │   ├── extension.js
    │   └── README.md
    └── antigravity-context-monitor/    # Tiện ích theo dõi dung lượng ngữ cảnh & token
        ├── package.json
        ├── extension.js
        └── README.md
```

---

## 🌟 Tổng quan các thành phần

### 1. Quy tắc toàn cục & Tự động hóa (`global/`)
- **`GEMINI.md`**: File luật làm việc cốt lõi nạp vào mọi phiên làm việc:
  - 9 luật thép: Kiểm chứng trước khi khẳng định, kiểm chứng đúng lớp, đọc lại thiết kế đã duyệt, tóm tắt và lên kế hoạch trước khi sửa code, mockup trước code sau, tạm dừng là thu thập, an toàn dữ liệu, chất lượng hơn tốc độ, kiểm soát tiến trình nền.
  - Văn phong trao đổi thuần Việt tự nhiên, khối trích dẫn mở đầu, cấm công thức toán gây vỡ giao diện.
- **`hooks.json`**: Cấu hình 2 điểm chặn tự động hóa:
  - **`PreInvocation`**: Tự động nhắc nhở AI tuân thủ 9 luật và ngắt luồng đọc giọng nói dở dang khi người dùng gửi lệnh mới.
  - **`Stop`**: Tự động trích xuất kết quả hoàn thành công việc và phát âm thanh thông báo bằng giọng đọc tiếng Việt theo từng dự án.
- **`enforce_rules.js` & `voice_notify.js`**:
  - Hỗ trợ chạy đa cửa sổ làm việc song song không bị xung đột âm thanh.
  - Tự động dọn dẹp sạch sẽ toàn bộ tệp tạm (`.wav`, `.pid`) ngay khi đọc xong, không để lại rác trên ổ đĩa.

### 2. Tiện ích chọn giọng đọc (`antigravity-voice-selector`)
- Hiển thị tên giọng đọc tiếng Việt đang được gán cho dự án ngay trên thanh trạng thái (Status Bar).
- Bấm vào nút để mở danh sách chọn nhanh giọng đọc hoặc bấm **`➕ Tải thêm giọng đọc mới...`**.
- Hỗ trợ tải trực tiếp các mô hình giọng đọc ONNX chất lượng cao từ kho lưu trữ đám mây Hugging Face kèm thanh hiển thị tiến trình phần trăm thực tế (`0% -> 100%`).

### 3. Tiện ích theo dõi ngữ cảnh (`antigravity-context-monitor`)
- Giám sát mức độ tiêu thụ token và dung lượng ngữ cảnh (Context Window) theo thời gian thực.
- Cảnh báo trực quan khi dung lượng chạm ngưỡng 75% để nhắc nhở người dùng chủ động nén ngữ cảnh hoặc mở phiên mới, tránh hiện tượng quá tải bộ nhớ AI.

---

## 🚀 Hướng dẫn cài đặt

### Cách 1: Cài đặt tự động bằng PowerShell (Khuyên dùng)
Chỉ cần mở PowerShell tại thư mục dự án và chạy:

```powershell
.\install.ps1
```

Script sẽ tự động:
1. Sao chép và cấu hình chuẩn đường dẫn cho `GEMINI.md`, `hooks.json` và các script vào `~/.gemini/`.
2. Cài đặt cả 2 extension vào thư mục `~/.antigravity-ide/extensions/` và `~/.vscode/extensions/`.
3. Hoàn tất trong vài giây mà không cần thao tác thủ công.

---

## 📤 Hướng dẫn đưa lên Git (GitHub / GitLab)

Để đưa kho lưu trữ này lên GitHub hoặc GitLab cá nhân:

1. **Khởi tạo và commit mã nguồn** (đã được tạo sẵn):
   ```bash
   git status
   ```

2. **Tạo một Repository mới** trên GitHub / GitLab (ví dụ: `antigravity-suite`).

3. **Gắn liên kết từ xa (Remote) và đẩy mã lên**:
   ```bash
   git remote add origin https://github.com/<tai-khoan-cua-dai-ca>/antigravity-suite.git
   git branch -M main
   git push -u origin main
   ```
