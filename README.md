# Hệ Thống Biên Tập Video Phóng Sự Địa Phương

> 🏛️ **Chủ quyền ứng dụng**: Bản quyền thuộc về **CÔNG TY TNHH MTV GIẢI PHÁP THANH TOÁN TRỰC TUYẾN SÓC TRĂNG**

Ứng dụng tự động hóa sản xuất bản tin thời sự, nội dung phát thanh và video phóng sự địa phương bằng **DeepSeek AI**, **Edge-TTS** và **FFmpeg**.

---

## ✨ Tính Năng Nổi Bật

- 🤖 **DeepSeek AI (`deepseek-chat` / `deepseek-reasoner`)**: Tự động phân tích số liệu địa phương và biên soạn bài phát thanh, lời bình phóng sự chuẩn văn phong báo nói.
- 🎙️ **Chuẩn Hóa SSML & Giọng Đọc BTV**: Tự động ngắt nghỉ câu chuẩn phát thanh viên Nam Bộ (Nam/Nữ) qua công nghệ Edge-TTS.
- 📻 **Xuất File Âm Thanh Loa Phát Thanh (.mp3)**: Tải nhanh bản tin âm thanh phục vụ truyền thanh cơ sở / loa phường xã.
- 🎬 **Render Video Phóng Sự Truyền Hình (.mp4)**:
  - Tự động ghép chuỗi Album ảnh hoặc Video tư liệu hiện trường.
  - ✨ **Hiệu Ứng Hình Ảnh Video Chuyên Nghiệp (VFX)**: Chuyển cảnh mờ chồng hòa tan mượt mà (Smooth Crossfade Dissolve) và cân chỉnh tone màu truyền hình sắc nét (Cinematic Broadcast Look).
  - 🎵 **Studio Nhạc Nền Phóng Sự (BGM)**: Đa dạng phong cách truyền hình (Thời sự chính luận, Nông thôn mới, Phóng sự truyền cảm), hỗ trợ tải lên file nhạc riêng (.mp3, .wav) từ điện thoại/máy tính, nghe thử trực tiếp và tùy chỉnh mức Audio Ducking.
  - Tự động chèn đồ họa **Lower-Third** sang trọng và gắn Logo đài/đơn vị.
- 🧹 **Nhập Liệu Thực Tế 100% (Không Dữ Liệu Giả Lập)**: Loại bỏ toàn bộ mockup cứng, hỗ trợ placeholder thông minh để cán bộ cơ sở nhập liệu trực tiếp mọi hoạt động, sự kiện tại địa phương.
- 📱 **Giao Diện Mobile-First Đa Nền Tảng**: Thiết kế tối ưu cho điện thoại di động (iOS & Android) với quy trình 3 bước chạm (Tabs), chống phóng to màn hình, thao tác bằng một tay.
- 📲 **Xuất Bản Đa Kênh 1-Chạm (Zalo, Facebook, YouTube, TikTok)**:
  - Mở trực tiếp **Zalo** để gửi nhanh file âm thanh phát thanh viên (.mp3) hoặc video phóng sự (.mp4) vào các nhóm chỉ đạo, nhóm công tác ấp/xã, hội đoàn thể cơ sở.
  - Hỗ trợ đăng tải lên Facebook Meta Business, YouTube Studio và TikTok Creator Studio kèm tiêu đề & hashtags tự động tạo.

---

## 🚀 Hướng Dẫn Triển Khai Lên Streamlit Community Cloud (Miễn Phí 100%)

Nền tảng chính thức và tối ưu nhất cho Streamlit, hỗ trợ đầy đủ WebSocket và FFmpeg.

### Bước 1: Đẩy mã nguồn lên GitHub
Nếu bạn chưa đưa dự án lên GitHub, hãy mở Terminal trong thư mục dự án và chạy các lệnh:

```bash
git init
git add .
git commit -m "Khoi tao du an Local AI Reporter"
# Tao mot repository moi tren github.com (vi du: truyen-hinh-so)
git branch -M main
git remote add origin https://github.com/<tai-khoan-github-cua-ban>/truyen-hinh-so.git
git push -u origin main
```

### Bước 2: Deploy trên Streamlit Cloud
1. Truy cập: **[share.streamlit.io](https://share.streamlit.io)** và đăng nhập bằng tài khoản GitHub.
2. Nhấn nút **New app**.
3. Điền thông tin:
   - **Repository**: `<tai-khoan-github-cua-ban>/truyen-hinh-so`
   - **Branch**: `main`
   - **Main file path**: `app.py`
4. Nhấn **Deploy!**

Sau 1-2 phút, ứng dụng của bạn sẽ có một đường link công khai (ví dụ: `https://truyen-hinh-so.streamlit.app`) để sử dụng mọi lúc, mọi nơi trên máy tính và điện thoại.

---

## 💻 Chạy Trực Tiếp Tại Local (Máy tính cá nhân)

```bash
# Cài đặt thư viện
pip install -r requirements.txt

# Khởi chạy ứng dụng
streamlit run app.py
```

Ứng dụng sẽ tự động mở tại: `http://localhost:8501`
