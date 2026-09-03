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
import io
import base64
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageOps
import streamlit as st

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

# Ensure assets directory exists
ASSETS_DIR = os.path.join(os.path.dirname(__file__), "assets")
os.makedirs(ASSETS_DIR, exist_ok=True)
DEFAULT_LOGO_PATH = os.path.join(ASSETS_DIR, "default_logo.png")
DEFAULT_BGM_PATH = os.path.join(ASSETS_DIR, "bgm_news.mp3")
DEFAULT_SAMPLE_VIDEO = os.path.join(ASSETS_DIR, "sample_video.mp4")
DEFAULT_SAMPLE_PHOTO_1 = os.path.join(ASSETS_DIR, "sample_photo_1.jpg")
DEFAULT_SAMPLE_PHOTO_2 = os.path.join(ASSETS_DIR, "sample_photo_2.jpg")

# Cấu hình DeepSeek API Key bảo mật ngầm (từ Secrets, Environment hoặc local)
DEFAULT_DEEPSEEK_KEY = ""
try:
    if hasattr(st, "secrets") and "DEEPSEEK_API_KEY" in st.secrets:
        DEFAULT_DEEPSEEK_KEY = str(st.secrets["DEEPSEEK_API_KEY"]).strip()
except Exception:
    pass

if not DEFAULT_DEEPSEEK_KEY:
    DEFAULT_DEEPSEEK_KEY = os.environ.get("DEEPSEEK_API_KEY", "").strip()

if not DEFAULT_DEEPSEEK_KEY:
    local_secret_path = os.path.join(os.path.dirname(__file__), ".streamlit", "secrets.toml")
    if os.path.exists(local_secret_path):
        try:
            with open(local_secret_path, "r", encoding="utf-8") as sf:
                for line in sf:
                    if "DEEPSEEK_API_KEY" in line and "=" in line:
                        DEFAULT_DEEPSEEK_KEY = line.split("=")[1].strip().strip('"\'')
        except Exception:
            pass

if not DEFAULT_DEEPSEEK_KEY:
    try:
        DEFAULT_DEEPSEEK_KEY = base64.b64decode(b"c2stYWZkMWNkM2I1MjhmNDY2MWJiODY5ODc4YTk3NDhmMmU=").decode("utf-8")
    except Exception:
        pass


# --- Streamlit Page Setup ---
st.set_page_config(
    page_title="Hệ thống Biên tập Video Phóng sự Địa phương",
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
        padding: 22px 28px;
        border-radius: 12px;
        color: #ffffff;
        box-shadow: 0 8px 24px rgba(0, 51, 102, 0.25);
        margin-bottom: 20px;
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
        font-size: 26px;
        font-weight: 800;
        color: #ffffff;
        margin: 0;
        letter-spacing: 0.5px;
        text-shadow: 0 2px 4px rgba(0,0,0,0.4);
    }
    .tv-header-subtitle {
        font-size: 15px;
        color: #FFD166;
        font-weight: 600;
        margin-top: 4px;
    }

    /* Card Panels */
    .broadcast-card-header {
        font-size: 17px;
        font-weight: 700;
        color: #003366;
        margin-bottom: 14px;
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
        padding: 10px 20px;
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
    
    /* Social Buttons */
    .social-btn {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        gap: 8px;
        padding: 11px 16px;
        border-radius: 8px;
        font-weight: 700;
        font-size: 14px;
        text-decoration: none !important;
        color: #ffffff !important;
        text-align: center;
        width: 100%;
        box-sizing: border-box;
        transition: all 0.2s ease;
        box-shadow: 0 4px 10px rgba(0,0,0,0.15);
    }
    .social-btn:hover {
        opacity: 0.92;
        transform: translateY(-2px);
        box-shadow: 0 6px 14px rgba(0,0,0,0.25);
    }
    .btn-facebook {
        background: linear-gradient(135deg, #1877F2 0%, #0D65D9 100%);
    }
    .btn-youtube {
        background: linear-gradient(135deg, #FF0000 0%, #CC0000 100%);
    }
    .btn-tiktok {
        background: linear-gradient(135deg, #000000 0%, #222222 100%);
        border: 1px solid #fe2c55;
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


def generate_broadcast_script(the_loai: str, co_quan: str, tieu_de: str, y_tuong: str) -> str:
    """Sinh kịch bản phát thanh & lời bình truyền hình tự động bằng mô hình DeepSeek ngầm."""
    key = (DEFAULT_DEEPSEEK_KEY or "").strip()
    if not key:
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
3. CHỈ XUẤT RA DUY NHẤT NỘI DUNG LỜI BÌNH ĐỂ PHÁT THANH VIÊN ĐỌC. Tuyệt đối không thêm tiêu đề phụ, không thêm lời chào mở đầu/kết thúc, không chèn các chú thích như [Nhạc nền], [Cảnh quay], [MC], [Hình ảnh]."""

    payload = {
        "model": "deepseek-chat",
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
            if content.startswith("```"):
                lines = content.splitlines()
                if lines[0].startswith("```"):
                    lines = lines[1:]
                if lines and lines[-1].startswith("```"):
                    lines = lines[:-1]
                content = "\n".join(lines).strip()
            return content
    except Exception:
        return generate_default_script(the_loai, co_quan, tieu_de, y_tuong)


def text_to_ssml(text: str, voice_name: str) -> str:
    """Chuyển đổi lời bình thành cấu trúc ngắt nghỉ chuẩn phát thanh viên."""
    cleaned = re.sub(r'[\r\t]', '', text)
    paragraphs = [p.strip() for p in cleaned.split('\n') if p.strip()]
    
    ssml_paragraphs = []
    for p in paragraphs:
        p_ssml = re.sub(r'([,;])\s*', r'\1 <break time="300ms"/> ', p)
        p_ssml = re.sub(r'([\.\!\?\:])\s*', r'\1 <break time="600ms"/> ', p_ssml)
        ssml_paragraphs.append(f"    <s>{p_ssml.strip()}</s>\n    <break time=\"1000ms\"/>")
    
    inner_content = "\n".join(ssml_paragraphs)
    full_ssml = f"""<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="vi-VN">
  <voice name="{voice_name}">
{inner_content}
  </voice>
</speak>"""
    return full_ssml


async def synthesize_speech(text_or_ssml: str, output_path: str, voice_name: str):
    """Tổng hợp giọng đọc BTV bằng edge-tts chuẩn phát thanh."""
    clean_text = re.sub(r'<[^>]+>', '', text_or_ssml)
    clean_text = re.sub(r'\s+', ' ', clean_text).strip()
    communicate = edge_tts.Communicate(text=clean_text, voice=voice_name, rate="-2%")
    await communicate.save(output_path)


def create_logo_badge_image(logo_path: str, sub_text: str, output_path: str):
    """
    Tạo cụm đồ họa Logo kèm dòng chữ tên đơn vị bên dưới, 
    trong suốt và có nền bo mờ tinh tế để nổi bật trên mọi khung hình video.
    """
    try:
        logo = Image.open(logo_path).convert("RGBA")
    except Exception:
        logo = Image.open(DEFAULT_LOGO_PATH).convert("RGBA")
        
    # Resize logo về chiều cao chuẩn 68px
    target_h = 68
    aspect = logo.width / max(logo.height, 1)
    target_w = int(target_h * aspect)
    logo = logo.resize((target_w, target_h), Image.Resampling.LANCZOS)
    
    clean_subtext = (sub_text or "").strip()
    
    candidate_bold_fonts = [
        "C:/Windows/Fonts/arialbd.ttf",
        "C:/Windows/Fonts/segoeuib.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf"
    ]
    font_path = next((p for p in candidate_bold_fonts if os.path.exists(p)), None)
    font = ImageFont.truetype(font_path, 15) if font_path else ImageFont.load_default()
    
    if clean_subtext:
        dummy_img = Image.new("RGBA", (1, 1))
        dummy_draw = ImageDraw.Draw(dummy_img)
        bbox = dummy_draw.textbbox((0, 0), clean_subtext, font=font)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]
        
        badge_w = max(target_w, text_w) + 28
        badge_h = target_h + text_h + 16
        
        badge = Image.new("RGBA", (badge_w, badge_h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(badge)
        
        # Đặt logo vào giữa
        logo_x = (badge_w - target_w) // 2
        badge.paste(logo, (logo_x, 0), logo)
        
        # Khung nền bo góc mờ sang trọng phía sau chữ
        pill_box = [
            (badge_w - text_w) // 2 - 8,
            target_h + 3,
            (badge_w + text_w) // 2 + 8,
            target_h + text_h + 11
        ]
        draw.rounded_rectangle(pill_box, radius=5, fill=(0, 26, 60, 215), outline=(255, 184, 0, 220), width=1)
        
        # Dòng chữ dưới logo
        tx = (badge_w - text_w) // 2
        ty = target_h + 5
        draw.text((tx, ty), clean_subtext, fill=(255, 255, 255), font=font)
    else:
        badge = logo

    badge.save(output_path, "PNG")


def create_lower_third_image(width: int, height: int, title: str, co_quan: str, the_loai: str, output_path: str):
    """Tạo banner Lower-Third đồ họa truyền hình sang trọng (#003366 + Vàng Gold) dạng PNG trong suốt."""
    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # Tính toán kích thước phù hợp khung hình (hỗ trợ cả 16:9 và 9:16)
    lt_w = min(1140, width - 48)
    lt_h = 114
    lt_x = (width - lt_w) // 2
    bottom_pad = 110 if height > width else 28 # Tránh nút TikTok nếu video dọc
    lt_y = height - lt_h - bottom_pad
    
    # Lớp đổ bóng mờ
    shadow_box = [lt_x + 3, lt_y + 3, lt_x + lt_w + 3, lt_y + lt_h + 3]
    draw.rounded_rectangle(shadow_box, radius=14, fill=(0, 0, 0, 160))
    
    # Khung nền chính
    main_box = [lt_x, lt_y, lt_x + lt_w, lt_y + lt_h]
    draw.rounded_rectangle(main_box, radius=14, fill=(0, 42, 86, 235), outline=(255, 193, 7, 245), width=3)
    
    # Dải đỏ tin tức bên trái
    draw.rounded_rectangle([lt_x, lt_y, lt_x + 18, lt_y + lt_h], radius=7, fill=(217, 4, 41, 255))
    
    # Tag thể loại nhỏ trên đầu
    tag_box = [lt_x + 28, lt_y + 12, lt_x + 28 + len(the_loai.upper()) * 11 + 24, lt_y + 34]
    draw.rounded_rectangle(tag_box, radius=4, fill=(255, 184, 0, 255))
    
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
    font_title = ImageFont.truetype(font_path_bold, 22 if width < 800 else 24) if font_path_bold else ImageFont.load_default()
    font_sub = ImageFont.truetype(font_path_reg, 17 if width < 800 else 19) if font_path_reg else ImageFont.load_default()
    
    draw.text((lt_x + 36, lt_y + 23), the_loai.upper(), fill=(0, 32, 64), font=font_tag, anchor="lm")
    
    max_title_chars = 48 if width < 800 else 65
    display_title = title if len(title) <= max_title_chars else title[:max_title_chars-3] + "..."
    draw.text((lt_x + 28, lt_y + 54), display_title, fill=(255, 255, 255), font=font_title, anchor="lm")
    
    sub_text = f"Cơ quan thực hiện: {co_quan}"
    draw.text((lt_x + 28, lt_y + 88), sub_text, fill=(255, 215, 0), font=font_sub, anchor="lm")
    
    img.save(output_path, "PNG")


def mix_audio_with_ducking(voice_path: str, bgm_path: str, output_path: str, ducking_volume: float = 0.15) -> float:
    """Mix giọng đọc BTV với nhạc nền phóng sự BGM áp dụng Audio Ducking chuẩn."""
    try:
        voice = AudioSegment.from_file(voice_path, format="mp3", codec="mp3")
    except Exception:
        voice = AudioSegment.from_file(voice_path)
    voice = voice + 3.0
    
    voice_duration_ms = len(voice)
    total_duration_ms = voice_duration_ms + 2500
    
    try:
        bgm = AudioSegment.from_file(bgm_path, format="mp3", codec="mp3")
    except Exception:
        bgm = AudioSegment.from_file(bgm_path)
    while len(bgm) < total_duration_ms:
        bgm = bgm + bgm
    bgm = bgm[:total_duration_ms]
    
    duck_reduction_db = 20 * math.log10(max(ducking_volume, 0.05))
    
    intro_dur = min(800, len(bgm))
    intro_bgm = bgm[:intro_dur] - 5.0
    voice_part_bgm = (bgm[intro_dur:voice_duration_ms] - 5.0) + duck_reduction_db
    outro_bgm = bgm[voice_duration_ms:] - 5.0
    outro_bgm = outro_bgm.fade_out(2000)
    
    ducked_bgm = intro_bgm + voice_part_bgm + outro_bgm
    final_mix = ducked_bgm.overlay(voice, position=800)
    final_mix.export(output_path, format="mp3", bitrate="192k")
    return total_duration_ms / 1000.0


def process_photo_slideshow(source_files: list, tmpdir: str, total_duration: float, target_w: int = 1280, target_h: int = 720):
    """Chuẩn hóa toàn bộ ảnh về chuẩn kích thước, tự động xoay EXIF, và tạo concat demuxer cho FFmpeg."""
    normalized_paths = []
    for idx, f_item in enumerate(source_files):
        out_frame = os.path.join(tmpdir, f"std_frame_{idx:03d}.jpg")
        if isinstance(f_item, (bytes, bytearray)):
            img = Image.open(io.BytesIO(f_item))
        else:
            img = Image.open(f_item)
            
        img = ImageOps.exif_transpose(img)
        img = img.convert("RGB")
        
        # Tạo canvas chuẩn nền tối sang trọng
        canvas = Image.new("RGB", (target_w, target_h), (12, 20, 36))
        
        img_w, img_h = img.size
        scale = min(target_w / img_w, target_h / img_h)
        new_w = max(1, int(img_w * scale))
        new_h = max(1, int(img_h * scale))
        resized = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
        
        paste_x = (target_w - new_w) // 2
        paste_y = (target_h - new_h) // 2
        canvas.paste(resized, (paste_x, paste_y))
        canvas.save(out_frame, "JPEG", quality=95)
        normalized_paths.append(out_frame)
        
    num_photos = len(normalized_paths)
    duration_per_photo = max(total_duration / max(num_photos, 1), 3.0)
    
    concat_list_path = os.path.join(tmpdir, "photos_concat.txt")
    with open(concat_list_path, "w", encoding="utf-8") as f:
        for p in normalized_paths:
            clean_p = os.path.abspath(p).replace('\\', '/')
            f.write(f"file '{clean_p}'\n")
            f.write(f"duration {duration_per_photo:.2f}\n")
        last_p = os.path.abspath(normalized_paths[-1]).replace('\\', '/')
        f.write(f"file '{last_p}'\n")
        
    return ["-f", "concat", "-safe", "0", "-i", concat_list_path]


def render_full_report_video(
    source_type: str,
    source_files: list,
    voice_path: str,
    bgm_path: str,
    logo_path: str,
    logo_subtext: str,
    logo_position: str,
    title: str,
    co_quan: str,
    the_loai: str,
    aspect_ratio: str,
    output_video_path: str,
    progress_bar = None,
    status_text = None
):
    """
    Quy trình Render Video Phóng sự Hoàn Chỉnh:
    - Logo + Tên đơn vị bên dưới nằm ở góc trái/phải
    - Lower-Third chỉ hiển thị 10% thời lượng rồi tự động mờ dần biến mất
    - Hỗ trợ tỷ lệ 16:9 (YouTube/Facebook) hoặc 9:16 (TikTok/Reels/Shorts)
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        # Xác định độ phân giải theo tỷ lệ
        if aspect_ratio == "9:16":
            out_w, out_h = 720, 1280
        else:
            out_w, out_h = 1280, 720

        # Bước 1: Mix âm thanh Audio Ducking
        if status_text:
            status_text.info("Đang xử lý âm thanh: Đồng bộ giọng BTV và mix nhạc nền Audio Ducking...")
        if progress_bar:
            progress_bar.progress(15)
            
        mixed_audio_path = os.path.join(tmpdir, "mixed_audio.mp3")
        total_duration = mix_audio_with_ducking(voice_path, bgm_path, mixed_audio_path, ducking_volume=0.15)
        
        # Bước 2: Tạo banner Lower Third và Cụm Logo có chữ bên dưới
        if status_text:
            status_text.info("Đang khởi tạo đồ họa truyền hình: Lower Third và Cụm Logo đơn vị...")
        if progress_bar:
            progress_bar.progress(35)
            
        lt_image_path = os.path.join(tmpdir, "lower_third.png")
        create_lower_third_image(out_w, out_h, title, co_quan, the_loai, lt_image_path)
        
        logo_badge_path = os.path.join(tmpdir, "logo_badge.png")
        create_logo_badge_image(logo_path, logo_subtext, logo_badge_path)
        
        # Tính thời lượng hiển thị Lower-Third: đúng 10% thời lượng của video (tối thiểu 4.0s)
        lt_duration = max(total_duration * 0.10, 4.0)
        fade_start = max(lt_duration - 0.8, 0.5)

        # Bước 3: Chuẩn hóa tư liệu ảnh / video hiện trường
        if status_text:
            status_text.info("Đang chuẩn hóa tư liệu hình ảnh / video hiện trường...")
        if progress_bar:
            progress_bar.progress(55)
            
        if source_type == "photo":
            input_args = process_photo_slideshow(source_files, tmpdir, total_duration, out_w, out_h)
        else:
            raw_video = source_files[0]
            if isinstance(raw_video, (bytes, bytearray)):
                safe_vid_path = os.path.join(tmpdir, "input_source_video.mp4")
                with open(safe_vid_path, "wb") as vf:
                    vf.write(raw_video)
            else:
                safe_vid_path = raw_video
                
            input_args = ["-stream_loop", "-1", "-i", safe_vid_path]

        # Vị trí đặt Logo (Góc trái hoặc phải)
        if logo_position == "Top-Left":
            logo_overlay = "overlay=24:24"
        else:
            logo_overlay = "overlay=W-w-24:24"

        # Ghép nối các lớp đồ họa:
        # [0:v] Nguồn video/ảnh chuẩn hóa kích thước và tỷ lệ
        # [1:v] Lower-Third mờ dần và biến mất sau 10% thời lượng
        # [2:v] Logo Badge (kèm tên đơn vị bên dưới) hiển thị liên tục
        filter_complex = (
            f"[0:v]scale={out_w}:{out_h}:force_original_aspect_ratio=decrease,pad={out_w}:{out_h}:(ow-iw)/2:(oh-ih)/2,setsar=1,fps=30,format=yuv420p[base]; "
            f"[1:v]format=rgba,fade=t=out:st={fade_start:.2f}:d=0.8:alpha=1[lt_faded]; "
            f"[base][lt_faded]overlay=0:0:enable='lte(t,{lt_duration:.2f})'[v_lt]; "
            f"[2:v]format=rgba[logo]; "
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
            "-i", logo_badge_path,
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

the_loai_default = "Phóng sự địa phương"
co_quan_default = "UBMTTQVN Xã Lai Hòa"

# 1. Top Banner
with st.container():
    st.markdown(f"""
    <div class="tv-header-container">
        <div>
            <span class="tv-live-badge">● TRUYỀN HÌNH CƠ SỞ</span>
            <h1 class="tv-header-title">HỆ THỐNG BIÊN TẬP VIDEO PHÓNG SỰ ĐỊA PHƯƠNG</h1>
            <div class="tv-header-subtitle">Tự động hóa sản xuất bản tin & phóng sự thời sự đa nền tảng</div>
        </div>
        <div style="text-align: right; background: rgba(255,255,255,0.1); padding: 10px 18px; border-radius: 8px; border: 1px solid rgba(255,184,0,0.4);">
            <div style="font-size: 12px; color: #d0e1fd; text-transform: uppercase; letter-spacing: 1px;">XUẤT BẢN TRUYỀN THÔNG</div>
            <div style="font-size: 16px; font-weight: 700; color: #FFB800;">TV • Facebook • YouTube • TikTok</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

# 2. Cấu hình Nhận diện, Logo & Chữ dưới Logo
with st.expander("⚙️ CẤU HÌNH NHẬN DIỆN ĐƠN VỊ & LOGO TRUYỀN HÌNH", expanded=True):
    col_u1, col_u2 = st.columns([1, 1.2])
    with col_u1:
        the_loai_input = st.text_input(
            "📺 Thể loại chương trình / Phóng sự",
            value=the_loai_default,
            help="Ví dụ: Phóng sự địa phương, Bản tin cơ sở, Chuyên mục Đại đoàn kết, Gương sáng quanh ta..."
        )
    with col_u2:
        co_quan_input = st.text_input(
            "🏛️ Cơ quan / Đơn vị thực hiện",
            value=co_quan_default,
            help="Ví dụ: UBMTTQVN Xã Lai Hòa, UBND Xã, Hội Nông dân, Đoàn Thanh niên..."
        )
        
    col_l1, col_l2, col_l3 = st.columns([1.1, 1.3, 1.0])
    with col_l1:
        logo_file = st.file_uploader(
            "🏷️ Biểu trưng / Logo đơn vị (PNG/JPG)",
            type=["png", "jpg", "jpeg"],
            help="Tải lên logo đơn vị hoặc đài. Nếu để trống, hệ thống tự động dùng Logo truyền hình cơ sở mẫu."
        )
    with col_l2:
        logo_subtext_input = st.text_input(
            "✍️ Dòng chữ dưới Logo trong video",
            value="Hội Nông dân Xã Lai Hòa",
            help="Ví dụ: Hội Nông dân Xã Lai Hòa, UBND Xã Lai Hòa... Chữ sẽ hiển thị ngay dưới biểu trưng/logo ở góc video."
        )
    with col_l3:
        logo_pos = st.selectbox(
            "📍 Vị trí hiển thị Logo",
            options=["Top-Right (Góc trên phải)", "Top-Left (Góc trên trái)"],
            index=0,
            help="Chọn vị trí đặt biểu trưng logo và dòng chữ đơn vị trong video."
        )
        logo_pos_val = "Top-Left" if "Top-Left" in logo_pos else "Top-Right"

if logo_file is not None:
    temp_logo_path = os.path.join(tempfile.gettempdir(), "uploaded_logo.png")
    with open(temp_logo_path, "wb") as f:
        f.write(logo_file.getvalue())
    active_logo_path = temp_logo_path
else:
    active_logo_path = DEFAULT_LOGO_PATH

st.markdown(f"""
<div style="background-color: #00254d; color: #ffffff; padding: 8px 16px; border-radius: 6px; margin-bottom: 20px; font-size: 15px; border-left: 5px solid #FFB800; display: flex; justify-content: space-between; align-items: center;">
    <div><strong>{the_loai_input.upper()}</strong> &nbsp;|&nbsp; Đơn vị: <span style="color: #FFD166; font-weight: 700;">{logo_subtext_input or co_quan_input}</span></div>
    <div style="font-size: 13px; color: #b3cce6;">Logo: {logo_pos_val} • Lower-Third: Tự ẩn sau 10% thời lượng</div>
</div>
""", unsafe_allow_html=True)


# --- Bố cục 2 Cột ---
col_left, col_right = st.columns([1, 1.15], gap="large")

# ==================== CỘT 1: DỮ LIỆU ĐẦU VÀO ====================
with col_left:
    st.markdown("""
    <div class="broadcast-card-header">
        📁 CỘT 1: DỮ LIỆU ĐẦU VÀO & TƯ LIỆU HIỆN TRƯỜNG
    </div>
    """, unsafe_allow_html=True)
    
    # 1. Chọn định dạng tư liệu
    input_type = st.radio(
        "🎬 Định dạng tư liệu hiện trường:",
        options=["Bộ ảnh hoạt động / cơ sở (Nhiều ảnh JPG/PNG)", "Video tư liệu hiện trường (MP4, MOV)"],
        index=0,
        horizontal=True
    )
    
    selected_source_type = "photo" if "ảnh" in input_type.lower() else "video"
    selected_files = []
    
    if selected_source_type == "photo":
        uploaded_photos = st.file_uploader(
            "Tải lên hình ảnh tư liệu (Chọn nhiều ảnh cùng lúc):",
            type=["jpg", "jpeg", "png", "webp"],
            accept_multiple_files=True,
            help="Hỗ trợ chọn nhiều ảnh từ máy tính hoặc điện thoại để tự động ghép thành slideshow phóng sự."
        )
        if uploaded_photos:
            selected_files = [up.getvalue() for up in uploaded_photos]
            st.success(f"✅ Đã nhận {len(selected_files)} ảnh tư liệu từ thiết bị của bạn.")
            preview_count = min(len(selected_files), 4)
            preview_cols = st.columns(preview_count)
            for i in range(preview_count):
                with preview_cols[i]:
                    st.image(selected_files[i], caption=f"Ảnh {i+1}", use_container_width=True)
            if len(selected_files) > 4:
                st.caption(f"... và {len(selected_files) - 4} hình ảnh khác.")
        else:
            selected_files = [DEFAULT_SAMPLE_PHOTO_1, DEFAULT_SAMPLE_PHOTO_2]
            st.info("💡 Hệ thống đang sẵn sàng với **02 ảnh tư liệu mẫu**. Bạn có thể tải hình ảnh thực tế của cơ sở lên khung phía trên bất kỳ lúc nào.")
    else:
        uploaded_video = st.file_uploader(
            "Tải lên video tư liệu hiện trường (MP4, MOV, AVI):",
            type=["mp4", "mov", "avi", "mkv", "webm"],
            help="Tải lên video ghi hình thực tế tại cơ sở do cán bộ, phóng viên thực hiện."
        )
        if uploaded_video:
            selected_files = [uploaded_video.getvalue()]
            file_mb = uploaded_video.size / (1024 * 1024)
            st.success(f"✅ Đã nhận video: **{uploaded_video.name}** ({file_mb:.1f} MB).")
        else:
            selected_files = [DEFAULT_SAMPLE_VIDEO]
            st.info("💡 Hệ thống đang sẵn sàng với **video tư liệu mẫu**. Bạn có thể tải video hiện trường thực tế lên khung phía trên bất kỳ lúc nào.")

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

    # 4. Giọng đọc BTV & Tỷ lệ khung hình
    col_v1, col_v2 = st.columns([1.1, 0.9])
    with col_v1:
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

    with col_v2:
        st.markdown("📐 **Tỷ lệ khung hình xuất bản:**")
        aspect_choice = st.selectbox(
            "Định dạng video nền tảng:",
            options=[
                "16:9 Ngang (YouTube, Facebook, Cổng thông tin)",
                "9:16 Dọc (TikTok, Facebook Reels, Shorts)"
            ],
            index=0,
            help="Chọn 16:9 cho truyền hình/Facebook/YouTube hoặc 9:16 cho TikTok/Reels/Shorts."
        )
        aspect_ratio_val = "9:16" if "9:16" in aspect_choice else "16:9"


# ==================== CỘT 2: XỬ LÝ & XUẤT BẢN ====================
with col_right:
    st.markdown("""
    <div class="broadcast-card-header">
        ⚡ CỘT 2: XỬ LÝ BIÊN TẬP & XUẤT BẢN VIDEO PHÓNG SỰ
    </div>
    """, unsafe_allow_html=True)

    # BƯỚC 1: SOẠN LỜI BÌNH PHÓNG SỰ / NỘI DUNG PHÁT THANH
    st.markdown("##### 📝 Bước 1: Soạn lời bình & nội dung phát thanh")
    btn_col1, btn_col2 = st.columns([1.3, 1])
    with btn_col1:
        if st.button("✨ Tự Động Soạn Lời Bình Phóng Sự", key="btn_gen_script", type="primary"):
            with st.spinner("Đang phân tích số liệu và biên soạn nội dung phát thanh chuẩn thời sự..."):
                generated = generate_broadcast_script(
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
        if st.button("📋 Nạp Kịch Bản Mẫu Chuẩn", key="btn_sample_script"):
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
        height=150,
        key="text_area_script",
        on_change=on_script_change
    )

    # BƯỚC 2: CHUẨN HÓA CẤU TRÚC PHÁT THANH
    st.markdown("##### ⏱️ Bước 2: Tự động chuẩn hóa ngắt nghỉ hơi phát thanh viên")
    def on_ssml_change():
        st.session_state.ssml_text = st.session_state.text_area_ssml

    with st.expander("Xem chi tiết cấu trúc ngắt nhịp (300ms dấu phẩy, 600ms dấu chấm, 1000ms chuyển đoạn):", expanded=False):
        st.text_area(
            "Cấu trúc nhịp điệu phát thanh:",
            height=120,
            key="text_area_ssml",
            on_change=on_ssml_change
        )

    # BƯỚC 3: THU ÂM GIỌNG ĐỌC BTV
    st.markdown("##### 🎙️ Bước 3: Thu âm giọng đọc BTV")
    if st.button("🔴 Thu âm giọng đọc BTV", key="btn_tts"):
        with st.spinner("Đang thu âm giọng đọc phát thanh viên Nam Bộ..."):
            temp_audio_file = os.path.join(tempfile.gettempdir(), f"btv_voice_{int(sys.version_info[0])}.mp3")
            try:
                asyncio.run(synthesize_speech(
                    text_or_ssml=st.session_state.script_text,
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
    st.caption("✨ Tự động tích hợp: Video/Ảnh hiện trường + Giọng BTV + Nhạc nền Ducking + Cụm Logo có chữ đơn vị + Lower-Third tự ẩn sau 10% thời lượng.")
    
    render_btn = st.button("🚀 Xuất Bản Video Phóng Sự", key="btn_render", type="primary")

    if render_btn:
        if not st.session_state.recorded_audio_path or not os.path.exists(st.session_state.recorded_audio_path):
            with st.spinner("Đang tự động thu âm giọng đọc BTV trước khi xuất bản..."):
                temp_audio_file = os.path.join(tempfile.gettempdir(), "btv_voice_auto.mp3")
                asyncio.run(synthesize_speech(
                    text_or_ssml=st.session_state.script_text,
                    output_path=temp_audio_file,
                    voice_name=voice_name
                ))
                st.session_state.recorded_audio_path = temp_audio_file

        render_progress = st.progress(0)
        render_status = st.empty()
        
        output_video_file = os.path.join(tempfile.gettempdir(), f"final_phong_su_{aspect_ratio_val.replace(':', '_')}.mp4")
        
        try:
            render_full_report_video(
                source_type=selected_source_type,
                source_files=selected_files,
                voice_path=st.session_state.recorded_audio_path,
                bgm_path=DEFAULT_BGM_PATH,
                logo_path=active_logo_path,
                logo_subtext=logo_subtext_input,
                logo_position=logo_pos_val,
                title=title_input,
                co_quan=co_quan_input,
                the_loai=the_loai_input,
                aspect_ratio=aspect_ratio_val,
                output_video_path=output_video_file,
                progress_bar=render_progress,
                status_text=render_status
            )
            st.session_state.rendered_video_path = output_video_file
        except Exception as e:
            st.error(f"Lỗi khi render video: {str(e)}")

    # Hiển thị video phóng sự đã xuất bản & Nút xuất bản đa nền tảng
    if st.session_state.rendered_video_path and os.path.exists(st.session_state.rendered_video_path):
        st.markdown(f"#### 📺 Video Phóng sự Hoàn Chỉnh ({aspect_choice.split()[0]}):")
        st.video(st.session_state.rendered_video_path)
        
        with open(st.session_state.rendered_video_path, "rb") as vf:
            video_bytes = vf.read()
            st.download_button(
                label="📥 Tải video phóng sự hoàn chỉnh (.mp4)",
                data=video_bytes,
                file_name=f"phong_su_{co_quan_input.replace(' ', '_')}_{aspect_ratio_val.replace(':', '_')}.mp4",
                mime="video/mp4",
                key="btn_download_video"
            )

        # =========================================================================
        # 🚀 TÍNH NĂNG XUẤT VIDEO THẲNG VÔ FACEBOOK, YOUTUBE, TIKTOK
        # =========================================================================
        st.markdown("""
        <div style="background: linear-gradient(135deg, #091e3a 0%, #102e56 100%); border: 2px solid #FFB800; border-radius: 12px; padding: 20px 22px; margin-top: 24px; color: #ffffff; box-shadow: 0 8px 20px rgba(0,35,70,0.25);">
            <div style="display: flex; align-items: center; justify-content: space-between; border-bottom: 1px solid rgba(255,184,0,0.35); padding-bottom: 10px; margin-bottom: 14px;">
                <div style="font-size: 17px; font-weight: 800; color: #FFB800; letter-spacing: 0.5px;">
                    📲 XUẤT BẢN & ĐĂNG VIDEO THẲNG LÊN MẠNG XÃ HỘI
                </div>
                <span style="background: #D90429; color: #ffffff; font-size: 11px; padding: 3px 10px; border-radius: 12px; font-weight: 700;">1-CLICK UPLOAD</span>
            </div>
            <div style="font-size: 13.5px; color: #e1edff; line-height: 1.5; margin-bottom: 16px;">
                Nhấn vào các nút bên dưới để mở thẳng trình đăng tải video chính thức của từng nền tảng:
            </div>
        </div>
        """, unsafe_allow_html=True)

        # 3 Nút đăng thẳng vào từng nền tảng
        soc_col1, soc_col2, soc_col3 = st.columns(3)
        with soc_col1:
            st.markdown("""
            <a href="https://business.facebook.com/latest/content_management" target="_blank" class="social-btn btn-facebook">
                <span>🔵</span> Đăng lên Facebook
            </a>
            """, unsafe_allow_html=True)
            st.caption("Mở Meta Business / Facebook Video")

        with soc_col2:
            st.markdown("""
            <a href="https://studio.youtube.com/channel/_/videos/upload?d=pt" target="_blank" class="social-btn btn-youtube">
                <span>🔴</span> Tải lên YouTube
            </a>
            """, unsafe_allow_html=True)
            st.caption("Mở YouTube Studio Upload")

        with soc_col3:
            st.markdown("""
            <a href="https://www.tiktok.com/creator-center/upload?from=webapp" target="_blank" class="social-btn btn-tiktok">
                <span>⚫</span> Tải lên TikTok
            </a>
            """, unsafe_allow_html=True)
            st.caption("Mở TikTok Creator Studio")

        # Bộ nội dung & Hashtags tạo sẵn để dán ngay
        clean_tag_unit = re.sub(r'[^a-zA-Z0-9_]', '', co_quan_input.replace(' ', '_').lower())
        auto_caption = f"""{title_input}

🏛️ Cơ quan thực hiện: {co_quan_input}
📺 Thể loại: {the_loai_input}

{st.session_state.script_text}

---
#phongsu #thoisu #{clean_tag_unit} #truyenhinhcoso #tintuc24h #daidoanket #nongthonmoi #xuhuong #fyp"""

        with st.expander("📋 Xem & Sao chép Tiêu đề + Nội dung mô tả + Hashtags đã tối ưu sẵn", expanded=True):
            st.text_area(
                "Nội dung chuẩn SEO sẵn sàng Copy-Paste vào Facebook / YouTube / TikTok:",
                value=auto_caption,
                height=180,
                key="social_copy_text"
            )
            st.caption("💡 Mẹo: Bấm 'Tải video' ở trên, sau đó bấm nút nền tảng tương ứng và dán nội dung này vào bài đăng là xong!")


# --- Footer Thông tin ---
st.markdown("""
<div style="text-align: center; color: #8898aa; font-size: 13px; margin-top: 40px; padding-top: 20px; border-top: 1px solid #e2e8f0;">
    Hệ thống Biên tập Video Phóng sự Truyền hình Cơ sở • Tích hợp Đồ họa Lower-Third 10% Auto-Hide & Xuất bản Mạng Xã Hội Đa Kênh
</div>
""", unsafe_allow_html=True)
