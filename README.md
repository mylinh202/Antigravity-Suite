# Antigravity Suite

Bộ công cụ tiêu chuẩn và toàn diện dành cho Antigravity IDE, bao gồm: **Bộ quy tắc toàn cục (Global Rules)**, **Hệ thống Hook tự động hóa (Lifecycle Hooks)** và **2 Tiện ích mở rộng cốt lõi (Voice Selector & Context Monitor)**.

---

## 📁 Cấu trúc kho lưu trữ

```text
antigravity-suite/
├── .gitignore                          # Tệp loại trừ rác, tệp tạm và nhật ký phát sinh
├── README.md                           # Tài liệu tổng quan và hướng dẫn sử dụng
│
├── install.ps1                         # Kịch bản cài đặt tổng hợp (Menu chọn hoặc tham số -Type)
├── install_rules.ps1                   # Kịch bản cài đặt RIÊNG phần Quy tắc (Windows)
├── install_voice.ps1                   # Kịch bản cài đặt RIÊNG phần Giọng đọc AI (Windows)
│
├── install.sh                          # Kịch bản cài đặt tổng hợp cho macOS & Linux
├── install_rules.sh                    # Kịch bản cài đặt RIÊNG phần Quy tắc (macOS/Linux)
├── install_voice.sh                    # Kịch bản cài đặt RIÊNG phần Giọng đọc AI (macOS/Linux)
│
├── global/                             # Cấu hình quy chuẩn toàn cục của hệ thống
│   ├── GEMINI.md                       # 9 luật cốt lõi và nguyên tắc làm việc chung
│   ├── config/
│   │   └── hooks.json                  # Cấu hình kích hoạt Hook (PreInvocation & Stop)
│   └── scripts/
│       ├── enforce_rules.js            # Nhắc nhở quy tắc & quản lý tiến trình độc lập
│       ├── voice_daemon.py             # Dịch vụ phát giọng đọc thường trực trong RAM (Piper TTS)
│       └── voice_notify.py             # Bộ kích hoạt âm thanh thông báo tiếng Việt
│
└── extensions/                         # 2 Tiện ích mở rộng cần thiết
    ├── antigravity-voice-selector/     # Tiện ích chọn & tải giọng đọc AI trên Status Bar
    └── antigravity-context-monitor/    # Tiện ích theo dõi dung lượng ngữ cảnh & token
```

---

## 🌟 Tổng quan các thành phần

### 1. Gói Quy tắc toàn cục & Giám sát ngữ cảnh (`Rules`)
- **`GEMINI.md`**: File luật làm việc cốt lõi nạp vào mọi phiên làm việc:
  - 9 luật thép: Kiểm chứng trước khi khẳng định, kiểm chứng đúng lớp, đọc lại thiết kế đã duyệt, tóm tắt và lên kế hoạch trước khi sửa code, mockup trước code sau, tạm dừng là thu thập, an toàn dữ liệu, chất lượng hơn tốc độ, kiểm soát tiến trình nền.
  - Văn phong trao đổi thuần Việt tự nhiên, khối trích dẫn mở đầu, cấm công thức toán gây vỡ giao diện.
- **`enforce_rules.js`**: Hook PreInvocation tự động nhắc nhở AI tuân thủ 9 luật và hủy tác vụ dở dang khi có yêu cầu mới.
- **`antigravity-context-monitor`**: Extension giám sát token và dung lượng ngữ cảnh (Context Window) theo thời gian thực trên thanh trạng thái.

### 2. Gói Giọng đọc thông báo AI (`Voice`)
- **`voice_daemon.py`**: Dịch vụ nền thường trú trong RAM (LRU Cache tối đa 3 giọng đọc) phát âm thanh siêu tốc trong 0.18 giây.
  - Tích hợp hàng đợi tuần tự (FIFO Queue): các workspace đọc lần lượt theo lượt, không bao giờ phát đè âm thanh.
  - Tích hợp WinRT SMTC: Tự động quét và tạm dừng chính xác video YouTube/Spotify khi có thông báo, sau đó tự động phát tiếp từ đúng giây đã dừng dở.
  - Hiệu ứng âm lượng êm ái: Lướt giảm âm lượng trong 350ms trước khi dừng và tăng dần âm lượng khi phát tiếp.
- **`voice_notify.py`**: Hook Stop tự động trích xuất nội dung hoàn thành và gửi tới Voice Daemon.
- **`antigravity-voice-selector`**: Extension chọn giọng đọc và tải thêm các mô hình ONNX chất lượng cao từ Hugging Face.

---

## 🚀 Hướng dẫn cài đặt

### Cách 1: Sử dụng bộ cài đặt riêng lẻ (Khuyên dùng)

#### Chỉ cài đặt Quy tắc (Rules Only):
- **Windows (PowerShell)**:
  ```powershell
  powershell -ExecutionPolicy Bypass -File .\install_rules.ps1
  ```
- **macOS / Linux**:
  ```bash
  chmod +x install_rules.sh && ./install_rules.sh
  ```

#### Chỉ cài đặt Giọng đọc AI (Voice Only):
- **Windows (PowerShell)**:
  ```powershell
  powershell -ExecutionPolicy Bypass -File .\install_voice.ps1
  ```
- **macOS / Linux**:
  ```bash
  chmod +x install_voice.sh && ./install_voice.sh
  ```

---

### Cách 2: Sử dụng bộ cài đặt tổng hợp (Menu tương tác hoặc tham số)

- **Chạy menu lựa chọn trực quan**:
  ```powershell
  powershell -ExecutionPolicy Bypass -File .\install.ps1
  ```
- **Chạy nhanh bằng tham số dòng lệnh**:
  ```powershell
  # Cài đặt toàn bộ
  powershell -ExecutionPolicy Bypass -File .\install.ps1 -Type All

  # Chỉ cài đặt Quy tắc
  powershell -ExecutionPolicy Bypass -File .\install.ps1 -Type Rules

  # Chỉ cài đặt Giọng đọc
  powershell -ExecutionPolicy Bypass -File .\install.ps1 -Type Voice
  ```
