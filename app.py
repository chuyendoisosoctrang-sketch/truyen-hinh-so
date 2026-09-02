import os
import sys
import json
import ssl
import urllib.request
import urllib.error
import asyncio
import tempfile
import subprocess
import re
import math
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import streamlit as st

# Cấu hình DeepSeek API Key an toàn từ Streamlit Secrets hoặc biến môi trường
DEFAULT_DEEPSEEK_KEY = ""
try:
    if hasattr(st, "secrets") and "DEEPSEEK_API_KEY" in st.secrets:
        DEFAULT_DEEPSEEK_KEY = str(st.secrets["DEEPSEEK_API_KEY"]).strip()
except Exception:
    pass
if not DEFAULT_DEEPSEEK_KEY:
    DEFAULT_DEEPSEEK_KEY = os.environ.get("DEEPSEEK_API_KEY", "").strip()

# Ensure audioop compatibility for Python 3.13 + pydub
try:
    import audioop
except ImportError:
    try:
        import audioop_lts as audioop
        sys.modules['audioop'] = audioop
    except ImportError:
        pass

from pydub import AudioSegment
import imageio_ffmpeg
import edge_tts

# Configure pydub to use imageio_ffmpeg binary
FFMPEG_BIN = imageio_ffmpeg.get_ffmpeg_exe()
AudioSegment.converter = FFMPEG_BIN

# Try importing google-genai
try:
    from google import genai
    from google.genai import types
    HAS_GENAI = True
except Exception:
    HAS_GENAI = False

# Ensure assets directory exists
ASSETS_DIR = os.path.join(os.path.dirname(__file__), "assets")
os.makedirs(ASSETS_DIR, exist_ok=True)
DEFAULT_LOGO_PATH = os.path.join(ASSETS_DIR, "default_logo.png")
DEFAULT_BGM_PATH = os.path.join(ASSETS_DIR, "bgm_news.mp3")
DEFAULT_SAMPLE_VIDEO = os.path.join(ASSETS_DIR, "sample_video.mp4")
DEFAULT_SAMPLE_PHOTO_1 = os.path.join(ASSETS_DIR, "sample_photo_1.jpg")
DEFAULT_SAMPLE_PHOTO_2 = os.path.join(ASSETS_DIR, "sample_photo_2.jpg")

# --- Streamlit Page Setup ---
st.set_page_config(
    page_title="Local AI Reporter - Biên tập Video Phóng sự Địa phương",
    page_icon="🎥",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom Styling - Professional Broadcast Theme (#003366)
st.markdown("""
<style>
    /* Main Background & Fonts */
    .main {
        background-color: #f4f7fa;
    }
    
    /* Header Container */
    .tv-header-container {
        background: linear-gradient(135deg, #001f3f 0%, #003366 50%, #004080 100%);
        border-bottom: 4px solid #FFB800;
        padding: 24px 32px;
        border-radius: 12px;
        color: #ffffff;
        box-shadow: 0 8px 24px rgba(0, 51, 102, 0.25);
        margin-bottom: 24px;
        display: flex;
        align-items: center;
        justify-content: space-between;
    }
    .tv-live-badge {
        background: #D90429;
        color: #ffffff;
        padding: 4px 14px;
        border-radius: 20px;
        font-weight: 800;
        font-size: 13px;
        letter-spacing: 1.5px;
        display: inline-block;
        animation: pulse 1.8s infinite;
        margin-bottom: 8px;
    }
    @keyframes pulse {
        0% { opacity: 1; transform: scale(1); }
        50% { opacity: 0.75; transform: scale(1.04); }
        100% { opacity: 1; transform: scale(1); }
    }
    .tv-header-title {
        font-size: 28px;
        font-weight: 800;
        color: #ffffff;
        margin: 0;
        letter-spacing: 0.5px;
        text-shadow: 0 2px 4px rgba(0,0,0,0.4);
    }
    .tv-header-subtitle {
        font-size: 16px;
        color: #FFD166;
        font-weight: 600;
        margin-top: 6px;
    }

    /* Card Panels */
    .broadcast-card {
        background-color: #ffffff;
        border: 1px solid #d9e2ec;
        border-top: 3px solid #003366;
        border-radius: 10px;
        padding: 22px;
        margin-bottom: 20px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.04);
    }
    .broadcast-card-header {
        font-size: 18px;
        font-weight: 700;
        color: #003366;
        margin-bottom: 16px;
        display: flex;
        align-items: center;
        gap: 8px;
        border-bottom: 2px solid #eef2f6;
        padding-bottom: 8px;
    }

    /* Buttons */
    .stButton>button {
        background: linear-gradient(135deg, #003366 0%, #004c99 100%);
        color: #ffffff;
        font-weight: 700;
        border: 1px solid #002244;
        border-radius: 8px;
        padding: 10px 24px;
        transition: all 0.25s ease;
        box-shadow: 0 4px 8px rgba(0, 51, 102, 0.2);
        width: 100%;
    }
    .stButton>button:hover {
        background: linear-gradient(135deg, #002244 0%, #003366 100%);
        border-color: #FFB800;
        color: #FFD166;
        box-shadow: 0 6px 14px rgba(0, 51, 102, 0.35);
        transform: translateY(-1px);
    }

    /* Status & Badges */
    .status-badge {
        padding: 6px 12px;
        border-radius: 6px;
        font-size: 13px;
        font-weight: 600;
        display: inline-block;
    }
    .status-ok {
        background-color: #d4edda;
        color: #155724;
        border: 1px solid #c3e6cb;
    }
</style>
""", unsafe_allow_html=True)


# --- Helper Functions ---

def generate_default_script(the_loai: str, co_quan: str, tieu_de: str, y_tuong: str) -> str:
    """Sinh kịch bản phóng sự chuẩn văn phong thời sự địa phương."""
    script = f"""Kính chào quý vị và các đồng bào! Trong không khí thi đua sôi nổi của toàn Đảng bộ, chính quyền và nhân dân địa phương, {the_loai} hôm nay trân trọng phản ánh những thành tựu nổi bật và tinh thần trách nhiệm của cán bộ, nhân dân trong công tác xây dựng quê hương.

Thời gian qua, dưới sự lãnh đạo sâu sát và chủ động của {co_quan}, công tác phối hợp thực hiện {tieu_de.lower()} đã gặt hái được những kết quả rất đỗi tự hào. {y_tuong.strip()}

Bà con nhân dân tại cơ sở đều bày tỏ sự phấn khởi, đồng thuận cao trước những đổi thay từng ngày của quê hương. Sự đoàn kết gắn bó keo sơn giữa chính quyền, mặt trận và nhân dân chính là cội nguồn sức mạnh để vượt qua mọi khó khăn.

Phát huy những kết quả đã đạt được, {co_quan} sẽ tiếp tục đồng hành cùng bà con, nhân rộng các mô hình hiệu quả, chung sức đồng lòng xây dựng quê hương ngày càng giàu đẹp, văn minh và ấm no hạnh phúc."""
    return script.strip()


def generate_gemini_script(api_key: str, the_loai: str, co_quan: str, tieu_de: str, y_tuong: str) -> str:
    """Sinh kịch bản bằng Gemini 2.5 Flash qua google-genai SDK."""
    if not HAS_GENAI or not api_key:
        return generate_default_script(the_loai, co_quan, tieu_de, y_tuong)
    try:
        client = genai.Client(api_key=api_key)
        prompt = f"""Bạn là Biên tập viên kỳ cựu của Đài Phát thanh và Truyền hình, chuyên sản xuất các chương trình thời sự chính luận và phóng sự cơ sở.
Hãy viết một Lời bình phóng sự truyền hình hoàn chỉnh, súc tích, trang trọng, mang tính cổ vũ và truyền cảm hứng cao theo thông tin sau:
- Thể loại chương trình: {the_loai}
- Cơ quan / Đơn vị thực hiện: {co_quan}
- Tiêu đề phóng sự: {tieu_de}
- Ý tưởng / Số liệu / Ghi chú sự kiện thực tế: {y_tuong}

Yêu cầu lời bình:
1. Độ dài khoảng 180 - 250 từ (thời lượng đọc khoảng 60 - 90 giây), chia làm 4 đoạn văn mạch lạc: Mở đầu ấn tượng, Thân bài nêu bật số liệu và kết quả thực tế, Phản hồi đồng thuận của nhân dân, Kết luận kêu gọi thi đua.
2. Giọng điệu chân thành, hào sảng, gắn liền với hơi thở đời sống của nhân dân và vai trò nòng cốt của {co_quan}.
3. Chỉ xuất ra nội dung lời bình để phát thanh viên đọc, không kèm tiêu đề phụ, không kèm ghi chú kịch bản hình ảnh cảnh quay."""
        
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt
        )
        return response.text.strip()
    except Exception as e:
        st.warning(f"Không thể kết nối Gemini API ({str(e)}), hệ thống tự động sử dụng kịch bản chuẩn hóa tối ưu.")
        return generate_default_script(the_loai, co_quan, tieu_de, y_tuong)


def generate_deepseek_script(api_key: str, the_loai: str, co_quan: str, tieu_de: str, y_tuong: str, model: str = "deepseek-chat") -> str:
    """Sinh kịch bản phát thanh & lời bình truyền hình tự động bằng DeepSeek AI API."""
    key = (api_key or "").strip()
    if not key:
        st.warning("Chưa cung cấp DeepSeek API Key. Hệ thống sử dụng kịch bản mẫu chuẩn hóa cơ sở.")
        return generate_default_script(the_loai, co_quan, tieu_de, y_tuong)
    
    url = "https://api.deepseek.com/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {key}",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    }
    system_prompt = (
        "Bạn là Biên tập viên kỳ cựu của Đài Phát thanh và Truyền hình, chuyên sản xuất các chương trình phát thanh, "
        "bản tin thời sự chính luận và phóng sự cơ sở. Phong cách viết chuẩn văn phong báo nói: câu từ gãy gọn, "
        "truyền cảm, giàu sức sống, nhịp điệu tự nhiên, từ ngữ chuẩn mực và gần gũi với quần chúng nhân dân địa phương."
    )
    user_prompt = f"""Hãy viết một Kịch bản lời bình phát thanh / phóng sự truyền hình hoàn chỉnh, súc tích, trang trọng, mang tính cổ vũ và truyền cảm hứng cao theo thông tin sau:
- Thể loại chương trình: {the_loai}
- Cơ quan / Đơn vị thực hiện: {co_quan}
- Tiêu đề bản tin / phóng sự: {tieu_de}
- Ý tưởng / Số liệu / Ghi chú sự kiện thực tế: {y_tuong}

Yêu cầu nội dung phát thanh:
1. Độ dài khoảng 180 - 250 từ (thời lượng phát thanh đọc khoảng 60 - 90 giây), chia làm 4 đoạn văn mạch lạc:
   - Đoạn 1: Mở đầu ấn tượng, nêu bật bối cảnh thi đua hoặc sự kiện nổi bật của địa phương.
   - Đoạn 2: Thân bài làm nổi bật các số liệu thực tế, việc làm cụ thể và vai trò chỉ đạo của {co_quan}.
   - Đoạn 3: Phản ánh không khí phấn khởi, sự đồng thuận và niềm tin của bà con nhân dân cơ sở.
   - Đoạn 4: Kết luận nêu bài học ý nghĩa, khơi dậy tinh thần đoàn kết và kêu gọi thi đua phát triển quê hương.
2. Ngôn từ báo nói: câu ngắn gọn, nhịp điệu phát thanh viên truyền cảm, ngắt nghỉ câu tự nhiên, dễ phát âm.
3. CHỈ XUẤT RA DUY NHẤT NỘI DUNG LỜI BÌNH ĐỂ PHÁT THANH VIÊN ĐỌC. Tuyệt đối không thêm tiêu đề phụ, không thêm lời chào mở đầu/kết thúc của AI, không chèn các chú thích như [Nhạc nền], [Cảnh quay], [MC], [Hình ảnh]."""

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": 0.7,
        "max_tokens": 1600
    }
    
    try:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers=headers, method="POST")
        ssl_ctx = ssl.create_default_context()
        try:
            resp_handle = urllib.request.urlopen(req, timeout=45, context=ssl_ctx)
        except ssl.SSLError:
            unverified_ctx = ssl._create_unverified_context()
            resp_handle = urllib.request.urlopen(req, timeout=45, context=unverified_ctx)
            
        with resp_handle as resp:
            resp_data = json.loads(resp.read().decode("utf-8"))
            content = resp_data["choices"][0]["message"]["content"].strip()
            # Loại bỏ các tag markdown ``` nếu có
            if content.startswith("```"):
                lines = content.splitlines()
                if lines[0].startswith("```"):
                    lines = lines[1:]
                if lines and lines[-1].startswith("```"):
                    lines = lines[:-1]
                content = "\n".join(lines).strip()
            return content
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="ignore")
        st.warning(f"Lỗi phản hồi từ DeepSeek API (HTTP {e.code}): {err_body}")
        return generate_default_script(the_loai, co_quan, tieu_de, y_tuong)
    except Exception as e:
        st.warning(f"Không thể kết nối DeepSeek API ({str(e)}). Hệ thống tự động sử dụng kịch bản chuẩn hóa.")
        return generate_default_script(the_loai, co_quan, tieu_de, y_tuong)


def text_to_ssml(text: str, voice_name: str) -> str:
    """Chuyển đổi lời bình thành SSML với ngắt nghỉ hơi chuẩn phát thanh viên."""
    cleaned = re.sub(r'[\r\t]', '', text)
    paragraphs = [p.strip() for p in cleaned.split('\n') if p.strip()]
    
    ssml_paragraphs = []
    for p in paragraphs:
        # Ngắt 300ms ở dấu phẩy, chấm phẩy
        p_ssml = re.sub(r'([,;])\s*', r'\1 <break time="300ms"/> ', p)
        # Ngắt 600ms ở dấu chấm, chấm than, hỏi, hai chấm
        p_ssml = re.sub(r'([\.\!\?\:])\s*', r'\1 <break time="600ms"/> ', p_ssml)
        ssml_paragraphs.append(f"    <s>{p_ssml.strip()}</s>\n    <break time=\"1000ms\"/>")
    
    inner_content = "\n".join(ssml_paragraphs)
    full_ssml = f"""<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="vi-VN">
  <voice name="{voice_name}">
{inner_content}
  </voice>
</speak>"""
    return full_ssml


async def synthesize_speech(ssml_content: str, output_path: str, voice_name: str):
    """Tổng hợp giọng đọc BTV bằng edge-tts."""
    communicate = edge_tts.Communicate(text=ssml_content, voice=voice_name)
    await communicate.save(output_path)


def create_lower_third_image(width: int, height: int, title: str, co_quan: str, the_loai: str, output_path: str):
    """Tạo banner Lower-Third đồ họa truyền hình sang trọng (#003366 + Vàng Gold) dạng PNG trong suốt."""
    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # Kích thước thanh thông tin
    lt_w = min(1140, width - 60)
    lt_h = 114
    lt_x = (width - lt_w) // 2
    lt_y = height - lt_h - 28
    
    # Lớp đổ bóng mờ (Drop Shadow)
    shadow_box = [lt_x + 3, lt_y + 3, lt_x + lt_w + 3, lt_y + lt_h + 3]
    draw.rounded_rectangle(shadow_box, radius=14, fill=(0, 0, 0, 160))
    
    # Khung nền chính: Gradient Xanh truyền hình (#002244 -> #003366)
    main_box = [lt_x, lt_y, lt_x + lt_w, lt_y + lt_h]
    draw.rounded_rectangle(main_box, radius=14, fill=(0, 42, 86, 235), outline=(255, 193, 7, 245), width=3)
    
    # Dải đỏ tin tức bên trái (News Accent Bar)
    draw.rounded_rectangle([lt_x, lt_y, lt_x + 18, lt_y + lt_h], radius=7, fill=(217, 4, 41, 255))
    
    # Tag thể loại nhỏ trên đầu
    tag_box = [lt_x + 28, lt_y + 12, lt_x + 28 + len(the_loai.upper()) * 11 + 24, lt_y + 34]
    draw.rounded_rectangle(tag_box, radius=4, fill=(255, 184, 0, 255))
    
    # Nạp font tiếng Việt tương thích cả Windows và Linux (Streamlit Cloud)
    candidate_bold_fonts = [
        "C:/Windows/Fonts/arialbd.ttf",
        "C:/Windows/Fonts/segoeuib.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf"
    ]
    candidate_reg_fonts = [
        "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/segoeui.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSans.ttf"
    ]
    font_path_bold = next((p for p in candidate_bold_fonts if os.path.exists(p)), None)
    font_path_reg = next((p for p in candidate_reg_fonts if os.path.exists(p)), None)
    
    font_tag = ImageFont.truetype(font_path_bold, 13) if font_path_bold else ImageFont.load_default()
    font_title = ImageFont.truetype(font_path_bold, 24) if font_path_bold else ImageFont.load_default()
    font_sub = ImageFont.truetype(font_path_reg, 19) if font_path_reg else ImageFont.load_default()
    
    # Vẽ chữ thể loại
    draw.text((lt_x + 36, lt_y + 23), the_loai.upper(), fill=(0, 32, 64), font=font_tag, anchor="lm")
    
    # Cắt gọn tiêu đề nếu quá dài
    display_title = title if len(title) <= 65 else title[:62] + "..."
    # Vẽ Tiêu đề phóng sự (Chữ trắng nổi bật)
    draw.text((lt_x + 28, lt_y + 54), display_title, fill=(255, 255, 255), font=font_title, anchor="lm")
    
    # Vẽ Cơ quan thực hiện (Màu vàng kim tươi sáng)
    sub_text = f"Cơ quan thực hiện: {co_quan}"
    draw.text((lt_x + 28, lt_y + 88), sub_text, fill=(255, 215, 0), font=font_sub, anchor="lm")
    
    img.save(output_path, "PNG")


def mix_audio_with_ducking(voice_path: str, bgm_path: str, output_path: str, ducking_volume: float = 0.15) -> float:
    """Mix giọng đọc BTV với nhạc nền phóng sự BGM áp dụng Audio Ducking chuẩn."""
    voice = AudioSegment.from_file(voice_path)
    # Tăng nhẹ âm lượng giọng đọc để rõ ràng, truyền cảm
    voice = voice + 3.0
    
    voice_duration_ms = len(voice)
    # Thêm 2.5 giây nhạc nền outro sau khi lời bình kết thúc
    total_duration_ms = voice_duration_ms + 2500
    
    bgm = AudioSegment.from_file(bgm_path)
    # Vòng lặp nhạc nền nếu BGM ngắn hơn video
    while len(bgm) < total_duration_ms:
        bgm = bgm + bgm
    bgm = bgm[:total_duration_ms]
    
    # Tính toán mức giảm dB theo tỉ lệ ducking (15% ~ -16.5 dB)
    duck_reduction_db = 20 * math.log10(max(ducking_volume, 0.05)) # ~ -16.5 dB
    
    # Cấu trúc BGM:
    # 0 -> 0.8s: Khúc dạo đầu (BGM ở mức -4 dB)
    # 0.8s -> voice_duration_ms: Khi BTV đọc, BGM tự hạ xuống 15% (ducking)
    # voice_duration_ms -> hết: Khúc kết thúc BGM dâng nhẹ lên (-5 dB) rồi fade out
    intro_dur = min(800, len(bgm))
    intro_bgm = bgm[:intro_dur] - 5.0
    
    voice_part_bgm = (bgm[intro_dur:voice_duration_ms] - 5.0) + duck_reduction_db
    
    outro_bgm = bgm[voice_duration_ms:] - 5.0
    outro_bgm = outro_bgm.fade_out(2000)
    
    ducked_bgm = intro_bgm + voice_part_bgm + outro_bgm
    
    # Ghép giọng BTV vào BGM tại thời điểm 800ms
    final_mix = ducked_bgm.overlay(voice, position=800)
    
    # Xuất ra file MP3 chất lượng cao
    final_mix.export(output_path, format="mp3", bitrate="192k")
    return total_duration_ms / 1000.0


def render_full_report_video(
    source_type: str,
    source_files: list,
    voice_path: str,
    bgm_path: str,
    logo_path: str,
    logo_position: str,
    title: str,
    co_quan: str,
    the_loai: str,
    output_video_path: str,
    progress_bar = None,
    status_text = None
):
    """Quy trình Render Video Phóng sự Hoàn Chỉnh Out-of-the-Box."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Bước 1: Mix âm thanh Audio Ducking
        if status_text:
            status_text.info("Đang xử lý âm thanh: Đồng bộ giọng BTV và mix nhạc nền Audio Ducking...")
        if progress_bar:
            progress_bar.progress(20)
            
        mixed_audio_path = os.path.join(tmpdir, "mixed_audio.mp3")
        total_duration = mix_audio_with_ducking(voice_path, bgm_path, mixed_audio_path, ducking_volume=0.15)
        
        # Bước 2: Tạo banner Lower Third đồ họa truyền hình
        if status_text:
            status_text.info("Đang khởi tạo đồ họa truyền hình: Lower Third và xử lý Logo...")
        if progress_bar:
            progress_bar.progress(40)
            
        lt_image_path = os.path.join(tmpdir, "lower_third.png")
        create_lower_third_image(1280, 720, title, co_quan, the_loai, lt_image_path)
        
        # Bước 3: Chuẩn bị nguồn hình ảnh/video
        if status_text:
            status_text.info("Đang xử lý tư liệu hình ảnh / video hiện trường...")
        if progress_bar:
            progress_bar.progress(60)
            
        video_inputs = []
        filter_complex_steps = []
        
        if source_type == "photo":
            # Xử lý nhiều ảnh tư liệu thành chuỗi Slideshow
            concat_list_path = os.path.join(tmpdir, "photos_concat.txt")
            num_photos = len(source_files)
            duration_per_photo = max(total_duration / max(num_photos, 1), 3.0)
            
            with open(concat_list_path, "w", encoding="utf-8") as f:
                for photo_p in source_files:
                    clean_p = os.path.abspath(photo_p).replace('\\', '/')
                    f.write(f"file '{clean_p}'\n")
                    f.write(f"duration {duration_per_photo:.2f}\n")
                # Thêm lặp ảnh cuối cho concat demuxer
                last_p = os.path.abspath(source_files[-1]).replace('\\', '/')
                f.write(f"file '{last_p}'\n")
                
            input_args = ["-f", "concat", "-safe", "0", "-i", concat_list_path]
        else:
            # Xử lý Video tư liệu hiện trường: loop video nếu video ngắn hơn audio
            input_video_path = source_files[0]
            input_args = ["-stream_loop", "-1", "-i", input_video_path]

        # Vị trí đặt Logo
        if logo_position == "Top-Left":
            logo_overlay = "overlay=28:28"
        else:
            logo_overlay = "overlay=W-w-28:28" # Top-Right mặc định

        # Ghép nối các lớp:
        # [0:v] Nguồn video/ảnh -> chuẩn 1280x720 16:9
        # [1:v] Lower-third PNG -> gắn chân trang
        # [2:v] Logo PNG -> resize rộng 180px -> gắn góc trên
        filter_complex = (
            "[0:v]scale=1280:720:force_original_aspect_ratio=decrease,pad=1280:720:(ow-iw)/2:(oh-ih)/2,format=yuv420p[base]; "
            "[1:v]scale=1280:720[lt]; "
            "[base][lt]overlay=0:0[v_lt]; "
            "[2:v]scale=180:-1[logo]; "
            f"[v_lt][logo]{logo_overlay}[vout]"
        )

        if status_text:
            status_text.info("Đang Render xuất bản video phóng sự chuẩn truyền hình MP4...")
        if progress_bar:
            progress_bar.progress(75)

        cmd = [
            FFMPEG_BIN, "-y"
        ] + input_args + [
            "-i", lt_image_path,
            "-i", logo_path,
            "-i", mixed_audio_path,
            "-filter_complex", filter_complex,
            "-map", "[vout]",
            "-map", "3:a",
            "-c:v", "libx264",
            "-preset", "veryfast",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            "-b:a", "192k",
            "-t", f"{total_duration:.2f}",
            output_video_path
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"Lỗi khi xử lý FFmpeg: {result.stderr}")

        if progress_bar:
            progress_bar.progress(100)
        if status_text:
            status_text.success("Hoàn tất xuất bản Video Phóng sự!")


# --- Session State Initialization ---
if "script_text" not in st.session_state:
    st.session_state.script_text = ""
if "text_area_script" not in st.session_state:
    st.session_state.text_area_script = ""
if "ssml_text" not in st.session_state:
    st.session_state.ssml_text = ""
if "text_area_ssml" not in st.session_state:
    st.session_state.text_area_ssml = ""
if "recorded_audio_path" not in st.session_state:
    st.session_state.recorded_audio_path = None
if "rendered_video_path" not in st.session_state:
    st.session_state.rendered_video_path = None


# --- APP INTERFACE ---

# 1. TV Dynamic Top Banner
the_loai_default = "Phóng sự địa phương"
co_quan_default = "UBMTTQVN Xã Lai Hòa"

# Layout: Cấu hình nhanh thông tin đơn vị ở Expandable / Top Bar
with st.container():
    st.markdown(f"""
    <div class="tv-header-container">
        <div>
            <span class="tv-live-badge">● TRUYỀN HÌNH CƠ SỞ</span>
            <h1 class="tv-header-title">HỆ THỐNG BIÊN TẬP VIDEO PHÓNG SỰ ĐỊA PHƯƠNG</h1>
            <div class="tv-header-subtitle">Local AI Reporter — Tự động hóa sản xuất bản tin & phóng sự thời sự</div>
        </div>
        <div style="text-align: right; background: rgba(255,255,255,0.1); padding: 10px 18px; border-radius: 8px; border: 1px solid rgba(255,184,0,0.4);">
            <div style="font-size: 12px; color: #d0e1fd; text-transform: uppercase; letter-spacing: 1px;">KÊNH TRUYỀN THÔNG</div>
            <div style="font-size: 16px; font-weight: 700; color: #FFB800;">HD 1080p / 720p Broadcast</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

# Top Bar Configuration: Thể loại & Cơ quan & Logo
with st.expander("⚙️ CẤU HÌNH NHẬN DIỆN ĐƠN VỊ & LOGO TRUYỀN HÌNH", expanded=True):
    cfg_col1, cfg_col2, cfg_col3, cfg_col4 = st.columns([1.2, 1.4, 1.2, 1.0])
    
    with cfg_col1:
        the_loai_input = st.text_input(
            "📺 Thể loại chương trình / Phóng sự",
            value=the_loai_default,
            help="Ví dụ: Phóng sự địa phương, Bản tin cơ sở, Chuyên mục Đại đoàn kết, Gương sáng quanh ta..."
        )
    with cfg_col2:
        co_quan_input = st.text_input(
            "🏛️ Cơ quan / Đơn vị thực hiện",
            value=co_quan_default,
            help="Ví dụ: UBMTTQVN Xã Lai Hòa, UBND Xã, Hội Nông dân, Đoàn Thanh niên..."
        )
    with cfg_col3:
        logo_file = st.file_uploader(
            "🏷️ Logo Đài / Đơn vị (PNG/JPG)",
            type=["png", "jpg", "jpeg"],
            help="Tải lên logo đơn vị hoặc đài. Nếu để trống, hệ thống tự động dùng Logo truyền hình cơ sở mẫu."
        )
    with cfg_col4:
        logo_pos = st.selectbox(
            "📍 Vị trí hiển thị Logo",
            options=["Top-Right (Góc trên phải)", "Top-Left (Góc trên trái)"],
            index=0
        )
        logo_pos_val = "Top-Left" if "Top-Left" in logo_pos else "Top-Right"

# Lưu Logo thực tế
if logo_file is not None:
    temp_logo_path = os.path.join(tempfile.gettempdir(), f"uploaded_logo_{logo_file.name}")
    with open(temp_logo_path, "wb") as f:
        f.write(logo_file.read())
    active_logo_path = temp_logo_path
else:
    active_logo_path = DEFAULT_LOGO_PATH

# Hiển thị dải băng thông tin động
st.markdown(f"""
<div style="background-color: #00254d; color: #ffffff; padding: 8px 16px; border-radius: 6px; margin-bottom: 20px; font-size: 15px; border-left: 5px solid #FFB800; display: flex; justify-content: space-between; align-items: center;">
    <div><strong>{the_loai_input.upper()}</strong> &nbsp;|&nbsp; Cơ quan thực hiện: <span style="color: #FFD166; font-weight: 700;">{co_quan_input}</span></div>
    <div style="font-size: 13px; color: #b3cce6;">Đồ họa Lower-Third & Logo tự động đồng bộ</div>
</div>
""", unsafe_allow_html=True)


# --- Hai Cột Chính: Cột 1 (Dữ liệu đầu vào) vs Cột 2 (Xử lý & Xuất bản) ---
col_left, col_right = st.columns([1, 1.15], gap="large")

# ==================== CỘT 1: DỮ LIỆU ĐẦU VÀO ====================
with col_left:
    st.markdown("""
    <div class="broadcast-card-header">
        📁 CỘT 1: DỮ LIỆU ĐẦU VÀO & TƯ LIỆU HIỆN TRƯỜNG
    </div>
    """, unsafe_allow_html=True)
    
    # 1. Chọn loại tư liệu: Video HOẶC Album Ảnh
    input_type = st.radio(
        "🎬 Chọn định dạng tư liệu hiện trường:",
        options=["Bộ ảnh hoạt động / cơ sở (Nhiều ảnh JPG/PNG)", "Video tư liệu hiện trường (MP4, MOV)"],
        index=0,
        horizontal=True
    )
    
    use_sample_media = st.checkbox("🎯 Sử dụng tư liệu mẫu có sẵn để trải nghiệm ngay out-of-the-box", value=True)
    
    selected_source_type = "photo" if "ảnh" in input_type.lower() else "video"
    selected_files = []
    
    if selected_source_type == "photo":
        uploaded_photos = st.file_uploader(
            "Tải lên các hình ảnh tư liệu (Chọn nhiều ảnh cùng lúc):",
            type=["jpg", "jpeg", "png"],
            accept_multiple_files=True,
            disabled=use_sample_media
        )
        if use_sample_media or not uploaded_photos:
            selected_files = [DEFAULT_SAMPLE_PHOTO_1, DEFAULT_SAMPLE_PHOTO_2]
            st.caption("ℹ️ Đang dùng 02 ảnh tư liệu mẫu: *Công trình Đại đoàn kết Nông thôn mới* & *Lễ trao quà an sinh xã hội*.")
        else:
            for up in uploaded_photos:
                t_path = os.path.join(tempfile.gettempdir(), f"upload_img_{up.name}")
                with open(t_path, "wb") as f:
                    f.write(up.read())
                selected_files.append(t_path)
            st.success(f"Đã nạp {len(selected_files)} ảnh tư liệu.")
    else:
        uploaded_video = st.file_uploader(
            "Tải lên video tư liệu hiện trường (MP4, MOV):",
            type=["mp4", "mov"],
            disabled=use_sample_media
        )
        if use_sample_media or not uploaded_video:
            selected_files = [DEFAULT_SAMPLE_VIDEO]
            st.caption("ℹ️ Đang dùng video tư liệu hiện trường mẫu của Xã Lai Hòa.")
        else:
            t_path = os.path.join(tempfile.gettempdir(), f"upload_vid_{uploaded_video.name}")
            with open(t_path, "wb") as f:
                f.write(uploaded_video.read())
            selected_files = [t_path]
            st.success("Đã nạp video tư liệu hiện trường.")

    st.markdown("---")

    # 2. Tiêu đề phóng sự
    title_input = st.text_input(
        "📝 Tiêu đề phóng sự / Bản tin:",
        value="Phát huy sức mạnh khối đại đoàn kết toàn dân tộc tại Xã Lai Hòa",
        help="Tiêu đề sẽ được biên tập vào lời bình và hiển thị nổi bật trên thanh Lower-Third của video."
    )

    # 3. Ý tưởng / Số liệu / Ghi chú sự kiện
    notes_default = (
        "Trong năm qua, Xã đã tổ chức thăm hỏi, trao tặng quà cho hơn 200 lượt gia đình chính sách; "
        "vận động các nhà hảo tâm hỗ trợ xây dựng 10 căn nhà Đại đoàn kết với tổng kinh phí 500 triệu đồng; "
        "huy động nhân dân tự nguyện hiến đất làm mới 3,5 km đường giao thông nông thôn, góp phần thay đổi diện mạo quê hương."
    )
    notes_input = st.text_area(
        "📊 Ý tưởng / Số liệu / Ghi chú sự kiện thực tế:",
        value=notes_default,
        height=130,
        help="Nhập các hoạt động thăm hỏi, số lượng nhà đại đoàn kết, công trình dân sinh..."
    )

    # 4. Chọn giọng đọc BTV
    st.markdown("🎙️ **Chọn giọng đọc Phát thanh viên:**")
    voice_choice = st.selectbox(
        "Giọng đọc phát thanh viên Nam Bộ:",
        options=[
            "Giọng Nam Nam Bộ (Trầm ấm, đĩnh đạc) - vi-VN-NamMinhNeural",
            "Giọng Nữ Nam Bộ (Truyền cảm, dịu dàng) - vi-VN-HoaiMyNeural"
        ],
        index=0
    )
    voice_name = "vi-VN-NamMinhNeural" if "Nam" in voice_choice else "vi-VN-HoaiMyNeural"

    # 5. Cấu hình Trí tuệ Nhân tạo AI
    st.markdown("🤖 **Cấu hình Trí tuệ nhân tạo (AI):**")
    ai_provider = st.radio(
        "Chọn giải pháp AI tự động tạo nội dung phát thanh:",
        options=[
            "DeepSeek AI (Khuyên dùng)",
            "Google Gemini (gemini-2.5-flash)",
            "Kịch bản Mẫu cơ sở (Không cần API)"
        ],
        index=0,
        help="Sử dụng DeepSeek AI để tự động biên soạn nội dung phát thanh chuẩn văn phong báo chí địa phương."
    )

    deepseek_model = "deepseek-chat"
    deepseek_api_key = DEFAULT_DEEPSEEK_KEY
    gemini_api_key = ""

    if "DeepSeek" in ai_provider:
        ds_col1, ds_col2 = st.columns([1.1, 1.3])
        with ds_col1:
            ds_model_choice = st.selectbox(
                "Mô hình DeepSeek:",
                options=[
                    "deepseek-chat (V3 - Nhanh, chuẩn phát thanh)",
                    "deepseek-reasoner (R1 - Suy luận & số liệu sâu)"
                ],
                index=0
            )
            deepseek_model = "deepseek-chat" if "chat" in ds_model_choice else "deepseek-reasoner"
        with ds_col2:
            deepseek_api_key = st.text_input(
                "DeepSeek API Key:",
                value=DEFAULT_DEEPSEEK_KEY,
                type="password",
                help="API Key DeepSeek đã được cấu hình sẵn."
            )
        st.caption("🟢 **Đã kết nối DeepSeek AI** — Sẵn sàng tự động biên soạn nội dung phát thanh & phóng sự.")
    elif "Gemini" in ai_provider:
        gemini_api_key = st.text_input(
            "Gemini API Key:",
            type="password",
            placeholder="AIzaSy...",
            help="Nhập Google Gemini API Key nếu muốn dùng Gemini."
        )
    else:
        st.caption("ℹ️ Hệ thống sử dụng bộ kịch bản mẫu cơ sở chuẩn hóa (không cần kết nối API).")


# ==================== CỘT 2: XỬ LÝ & XUẤT BẢN ====================
with col_right:
    st.markdown("""
    <div class="broadcast-card-header">
        ⚡ CỘT 2: XỬ LÝ BIÊN TẬP & XUẤT BẢN VIDEO PHÓNG SỰ
    </div>
    """, unsafe_allow_html=True)

    # BƯỚC 1: SOẠN LỜI BÌNH PHÓNG SỰ / NỘI DUNG PHÁT THANH
    st.markdown("##### 📝 Bước 1: Soạn lời bình & nội dung phát thanh")
    btn_col1, btn_col2 = st.columns([1.25, 1])
    with btn_col1:
        if "DeepSeek" in ai_provider:
            btn_label = "✨ Tạo Lời bình (DeepSeek AI)"
        elif "Gemini" in ai_provider:
            btn_label = "✨ Tạo Lời bình (Gemini AI)"
        else:
            btn_label = "✨ Tạo Kịch bản Nhanh"
            
        if st.button(btn_label, key="btn_gen_script", type="primary"):
            with st.spinner("DeepSeek AI đang phân tích số liệu và biên soạn nội dung phát thanh..." if "DeepSeek" in ai_provider else "AI đang biên soạn nội dung thời sự..."):
                if "DeepSeek" in ai_provider:
                    generated = generate_deepseek_script(
                        api_key=deepseek_api_key.strip() if deepseek_api_key else None,
                        the_loai=the_loai_input,
                        co_quan=co_quan_input,
                        tieu_de=title_input,
                        y_tuong=notes_input,
                        model=deepseek_model
                    )
                elif "Gemini" in ai_provider:
                    generated = generate_gemini_script(
                        api_key=gemini_api_key.strip() if gemini_api_key else None,
                        the_loai=the_loai_input,
                        co_quan=co_quan_input,
                        tieu_de=title_input,
                        y_tuong=notes_input
                    )
                else:
                    generated = generate_default_script(
                        the_loai=the_loai_input,
                        co_quan=co_quan_input,
                        tieu_de=title_input,
                        y_tuong=notes_input
                    )
                st.session_state.script_text = generated
                st.session_state.text_area_script = generated
                st.session_state.ssml_text = text_to_ssml(generated, voice_name)
                st.session_state.text_area_ssml = st.session_state.ssml_text
                st.rerun()

    with btn_col2:
        if st.button("📋 Nạp Kịch bản Mẫu cơ sở", key="btn_sample_script"):
            sampled = generate_default_script(
                the_loai=the_loai_input,
                co_quan=co_quan_input,
                tieu_de=title_input,
                y_tuong=notes_input
            )
            st.session_state.script_text = sampled
            st.session_state.text_area_script = sampled
            st.session_state.ssml_text = text_to_ssml(sampled, voice_name)
            st.session_state.text_area_ssml = st.session_state.ssml_text
            st.rerun()

    # Khởi tạo kịch bản ban đầu nếu chưa có
    if not st.session_state.script_text:
        st.session_state.script_text = generate_default_script(
            the_loai_input, co_quan_input, title_input, notes_input
        )
        st.session_state.text_area_script = st.session_state.script_text
        st.session_state.ssml_text = text_to_ssml(st.session_state.script_text, voice_name)
        st.session_state.text_area_ssml = st.session_state.ssml_text

    def on_script_change():
        st.session_state.script_text = st.session_state.text_area_script
        st.session_state.ssml_text = text_to_ssml(st.session_state.text_area_script, voice_name)
        st.session_state.text_area_ssml = st.session_state.ssml_text

    st.text_area(
        "Nội dung phát thanh / Lời bình phóng sự (Có thể chỉnh sửa trực tiếp):",
        height=160,
        key="text_area_script",
        on_change=on_script_change
    )

    # BƯỚC 2: CHUYỂN ĐỔI MÃ SSML PHÁT THANH
    st.markdown("##### ⏱️ Bước 2: Tự động chuẩn hóa SSML ngắt nghỉ hơi")
    def on_ssml_change():
        st.session_state.ssml_text = st.session_state.text_area_ssml

    with st.expander("Xem chi tiết cấu trúc SSML chuẩn phát thanh (300ms dấu phẩy, 600ms dấu chấm, 1000ms chuyển đoạn):", expanded=False):
        st.text_area(
            "Mã SSML:",
            height=130,
            key="text_area_ssml",
            on_change=on_ssml_change
        )

    # BƯỚC 3: THU ÂM GIỌNG ĐỌC BTV
    st.markdown("##### 🎙️ Bước 3: Thu âm giọng đọc BTV")
    if st.button("🔴 Thu âm giọng đọc BTV (Edge-TTS)", key="btn_tts"):
        with st.spinner("Đang thu âm giọng đọc phát thanh viên Nam Bộ..."):
            temp_audio_file = os.path.join(tempfile.gettempdir(), f"btv_voice_{int(sys.version_info[0])}.mp3")
            try:
                asyncio.run(synthesize_speech(
                    ssml_content=st.session_state.ssml_text,
                    output_path=temp_audio_file,
                    voice_name=voice_name
                ))
                st.session_state.recorded_audio_path = temp_audio_file
                st.success("Thu âm giọng BTV thành công!")
            except Exception as e:
                st.error(f"Lỗi khi thu âm: {str(e)}")

    if st.session_state.recorded_audio_path and os.path.exists(st.session_state.recorded_audio_path):
        st.audio(st.session_state.recorded_audio_path, format="audio/mp3")
        with open(st.session_state.recorded_audio_path, "rb") as af:
            audio_bytes = af.read()
            st.download_button(
                label="📻 Tải file âm thanh phát thanh viên (.mp3)",
                data=audio_bytes,
                file_name=f"ban_tin_phat_thanh_{co_quan_input.replace(' ', '_')}.mp3",
                mime="audio/mp3",
                key="btn_download_audio"
            )

    st.markdown("---")

    # BƯỚC 4: RENDER VIDEO PHÓNG SỰ
    st.markdown("##### 🎥 Bước 4: Xuất bản Video Phóng sự Hoàn Chỉnh")
    st.caption("✨ Tự động tích hợp: Video/Slideshow ảnh + Giọng đọc BTV + Nhạc nền Audio Ducking (15%) + Lower-Third thông tin đơn vị + Logo truyền hình.")
    
    render_btn = st.button("🚀 Render Video Phóng sự", key="btn_render", type="primary")

    if render_btn:
        # Nếu chưa có giọng đọc BTV, tự động thu âm trước
        if not st.session_state.recorded_audio_path or not os.path.exists(st.session_state.recorded_audio_path):
            with st.spinner("Đang tự động thu âm giọng đọc BTV trước khi render..."):
                temp_audio_file = os.path.join(tempfile.gettempdir(), "btv_voice_auto.mp3")
                asyncio.run(synthesize_speech(
                    ssml_content=st.session_state.ssml_text,
                    output_path=temp_audio_file,
                    voice_name=voice_name
                ))
                st.session_state.recorded_audio_path = temp_audio_file

        render_progress = st.progress(0)
        render_status = st.empty()
        
        output_video_file = os.path.join(tempfile.gettempdir(), "final_phong_su_dia_phuong.mp4")
        
        try:
            render_full_report_video(
                source_type=selected_source_type,
                source_files=selected_files,
                voice_path=st.session_state.recorded_audio_path,
                bgm_path=DEFAULT_BGM_PATH,
                logo_path=active_logo_path,
                logo_position=logo_pos_val,
                title=title_input,
                co_quan=co_quan_input,
                the_loai=the_loai_input,
                output_video_path=output_video_file,
                progress_bar=render_progress,
                status_text=render_status
            )
            st.session_state.rendered_video_path = output_video_file
        except Exception as e:
            st.error(f"Lỗi khi render video: {str(e)}")

    # Hiển thị kết quả video và nút tải về
    if st.session_state.rendered_video_path and os.path.exists(st.session_state.rendered_video_path):
        st.markdown("#### 📺 Video Phóng sự Hoàn Chỉnh:")
        st.video(st.session_state.rendered_video_path)
        
        with open(st.session_state.rendered_video_path, "rb") as vf:
            video_bytes = vf.read()
            st.download_button(
                label="📥 Tải video phóng sự hoàn chỉnh (.mp4)",
                data=video_bytes,
                file_name=f"phong_su_{co_quan_input.replace(' ', '_')}.mp4",
                mime="video/mp4",
                key="btn_download_video"
            )

# --- Footer Thông tin ---
st.markdown("""
<div style="text-align: center; color: #8898aa; font-size: 13px; margin-top: 40px; padding-top: 20px; border-top: 1px solid #e2e8f0;">
    Hệ thống Biên tập Video Phóng sự Địa phương (Local AI Reporter) • Phát triển trên Google Antigravity • Công nghệ Edge-TTS & FFmpeg Đa lớp
</div>
""", unsafe_allow_html=True)
