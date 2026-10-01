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
APP_MOBILE_LOGO_PATH = os.path.join(ASSETS_DIR, "app_mobile_logo.png")
BGM_CHINH_LUAN_PATH = os.path.join(ASSETS_DIR, "bgm_chinh_luan.mp3")
BGM_NONG_THON_PATH = os.path.join(ASSETS_DIR, "bgm_nong_thon_moi.mp3")
BGM_TRUYEN_CAM_PATH = os.path.join(ASSETS_DIR, "bgm_truyen_cam.mp3")

VOICES_DIR = os.path.join(ASSETS_DIR, "voices")
VOICE_PREVIEWS = {
    "vi-VN-NamMinhNeural": os.path.join(VOICES_DIR, "vi_nam.mp3"),
    "vi-VN-HoaiMyNeural": os.path.join(VOICES_DIR, "vi_nu.mp3"),
    "km-KH-PisethNeural": os.path.join(VOICES_DIR, "km_nam.mp3"),
    "km-KH-SreymomNeural": os.path.join(VOICES_DIR, "km_nu.mp3")
}

# Encode App Mobile Logo sang base64 để hiển thị trực tiếp và làm PWA Icon
APP_LOGO_B64 = ""
if os.path.exists(APP_MOBILE_LOGO_PATH):
    try:
        with open(APP_MOBILE_LOGO_PATH, "rb") as lf:
            APP_LOGO_B64 = base64.b64encode(lf.read()).decode("utf-8")
    except Exception:
        pass

# Fallback nếu thiếu file BGM
if not os.path.exists(BGM_CHINH_LUAN_PATH):
    BGM_CHINH_LUAN_PATH = os.path.join(ASSETS_DIR, "bgm_news.mp3")
if not os.path.exists(BGM_NONG_THON_PATH):
    BGM_NONG_THON_PATH = BGM_CHINH_LUAN_PATH
if not os.path.exists(BGM_TRUYEN_CAM_PATH):
    BGM_TRUYEN_CAM_PATH = BGM_CHINH_LUAN_PATH

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
    page_icon=APP_MOBILE_LOGO_PATH if os.path.exists(APP_MOBILE_LOGO_PATH) else "🎥",
    layout="wide",
    initial_sidebar_state="collapsed",
    menu_items={
        "About": "### Hệ thống Biên tập Video Phóng sự Địa phương\n\nChủ quyền ứng dụng thuộc về: **CÔNG TY TNHH MTV GIẢI PHÁP THANH TOÁN TRỰC TUYẾN SÓC TRĂNG**"
    }
)

# Custom Styling - Professional Broadcast Theme (#003366) + Mobile-First Responsive
st.markdown("""
<style>
    /* Main Background & Fonts */
    .main {
        background-color: #f4f7fa;
    }
    
    /* Optimize Streamlit container for Mobile & Desktop */
    .block-container {
        padding-top: 1.5rem !important;
        padding-bottom: 3.5rem !important;
        max-width: 1200px !important;
    }
    @media (max-width: 768px) {
        .block-container {
            padding-top: 0.8rem !important;
            padding-bottom: 2.5rem !important;
            padding-left: 0.6rem !important;
            padding-right: 0.6rem !important;
        }
    }
    
    /* Header Container */
    .tv-header-container {
        background: linear-gradient(135deg, #001f3f 0%, #003366 50%, #004080 100%);
        border-bottom: 4px solid #FFB800;
        padding: 20px 24px;
        border-radius: 12px;
        color: #ffffff;
        box-shadow: 0 8px 24px rgba(0, 51, 102, 0.25);
        margin-bottom: 16px;
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 16px;
        flex-wrap: wrap;
    }
    .tv-header-brand {
        flex: 1 1 300px;
    }
    .tv-live-badge {
        background: #D90429;
        color: #ffffff;
        padding: 4px 14px;
        border-radius: 20px;
        font-weight: 800;
        font-size: 12.5px;
        letter-spacing: 1.2px;
        display: inline-block;
        animation: pulse 1.8s infinite;
        margin-bottom: 8px;
    }
    @keyframes pulse {
        0% { opacity: 1; transform: scale(1); }
        50% { opacity: 0.75; transform: scale(1.03); }
        100% { opacity: 1; transform: scale(1); }
    }
    .tv-header-title {
        font-size: 24px;
        font-weight: 800;
        color: #ffffff;
        margin: 0;
        letter-spacing: 0.5px;
        text-shadow: 0 2px 4px rgba(0,0,0,0.4);
        line-height: 1.25;
    }
    .tv-header-subtitle {
        font-size: 14px;
        color: #FFD166;
        font-weight: 600;
        margin-top: 4px;
        line-height: 1.35;
    }
    .tv-header-owner-box {
        text-align: right;
        background: rgba(255,255,255,0.08);
        padding: 10px 18px;
        border-radius: 10px;
        border: 1px solid rgba(255,209,102,0.45);
        box-shadow: 0 4px 14px rgba(0,0,0,0.15);
        max-width: 480px;
    }
    .tv-owner-tag {
        font-size: 11px;
        color: #d0e1fd;
        text-transform: uppercase;
        letter-spacing: 1.2px;
        font-weight: 700;
        display: flex;
        align-items: center;
        justify-content: flex-end;
        gap: 6px;
    }
    .tv-owner-company {
        font-size: 13.5px;
        font-weight: 800;
        color: #FFD166;
        margin-top: 3px;
        line-height: 1.35;
        letter-spacing: 0.3px;
    }
    @media (max-width: 768px) {
        .tv-header-container {
            padding: 14px 16px !important;
            margin-bottom: 12px !important;
            gap: 10px !important;
        }
        .tv-header-title {
            font-size: 18.5px !important;
        }
        .tv-header-subtitle {
            font-size: 12.5px !important;
        }
        .tv-header-owner-box {
            text-align: left !important;
            width: 100% !important;
            padding: 8px 12px !important;
        }
        .tv-owner-tag {
            justify-content: flex-start !important;
        }
        .tv-owner-company {
            font-size: 12.5px !important;
        }
    }

    /* Status Bar */
    .tv-status-bar {
        background-color: #00254d;
        color: #ffffff;
        padding: 10px 16px;
        border-radius: 8px;
        margin-bottom: 16px;
        font-size: 14px;
        border-left: 5px solid #FFB800;
        display: flex;
        justify-content: space-between;
        align-items: center;
        flex-wrap: wrap;
        gap: 8px;
    }
    .tv-status-tags {
        display: flex;
        gap: 6px;
        flex-wrap: wrap;
        align-items: center;
    }
    .tv-chip {
        background: rgba(255, 255, 255, 0.12);
        padding: 4px 10px;
        border-radius: 12px;
        font-size: 12px;
        color: #e2e8f0;
        border: 1px solid rgba(255, 255, 255, 0.15);
        font-weight: 600;
    }
    .tv-chip-done {
        background: #059669 !important;
        color: #ffffff !important;
    }
    @media (max-width: 768px) {
        .tv-status-bar {
            padding: 8px 12px !important;
            font-size: 13px !important;
        }
    }

    /* Modern Tabs - Touch-Friendly Pill Navigation */
    .stTabs [data-baseweb="tab-list"] {
        gap: 6px;
        background: #e2e8f0;
        padding: 6px;
        border-radius: 12px;
        border: 1px solid #cbd5e1;
        display: flex;
        width: 100%;
        margin-bottom: 18px;
        box-sizing: border-box;
    }
    .stTabs [data-baseweb="tab"] {
        flex: 1 1 0;
        text-align: center;
        border-radius: 8px;
        padding: 12px 10px;
        font-weight: 700;
        font-size: 15px;
        color: #334155;
        background: transparent;
        transition: all 0.2s ease;
        border: none !important;
        justify-content: center;
        cursor: pointer;
    }
    .stTabs [aria-selected="true"] {
        background: #003366 !important;
        color: #ffffff !important;
        box-shadow: 0 4px 12px rgba(0, 51, 102, 0.3) !important;
    }
    @media (max-width: 768px) {
        .stTabs [data-baseweb="tab-list"] {
            padding: 4px;
            gap: 4px;
        }
        .stTabs [data-baseweb="tab"] {
            padding: 10px 4px !important;
            font-size: 12.5px !important;
            line-height: 1.25 !important;
        }
    }

    /* Card Panels */
    .broadcast-card-header {
        font-size: 16.5px;
        font-weight: 700;
        color: #003366;
        margin-bottom: 14px;
        display: flex;
        align-items: center;
        gap: 8px;
        border-bottom: 2px solid #eef2f6;
        padding-bottom: 8px;
    }

    /* Touch-Friendly Buttons */
    .stButton>button {
        background: linear-gradient(135deg, #003366 0%, #004c99 100%);
        color: #ffffff;
        font-weight: 700;
        border: 1px solid #002244;
        border-radius: 10px;
        padding: 11px 20px;
        font-size: 15px;
        transition: all 0.2s ease;
        box-shadow: 0 4px 8px rgba(0, 51, 102, 0.2);
        width: 100%;
        min-height: 48px;
        touch-action: manipulation;
    }
    .stButton>button:hover {
        background: linear-gradient(135deg, #002244 0%, #003366 100%);
        border-color: #FFB800;
        color: #FFD166;
        box-shadow: 0 6px 14px rgba(0, 51, 102, 0.35);
        transform: translateY(-1px);
    }
    .stButton>button:active {
        transform: scale(0.98);
    }

    /* Download Buttons */
    .stDownloadButton>button {
        min-height: 48px;
        font-size: 15px;
        font-weight: 700;
        border-radius: 10px;
        width: 100%;
        touch-action: manipulation;
    }
    
    /* Social Buttons & Responsive Grid */
    .social-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
        gap: 12px;
        margin-top: 14px;
        margin-bottom: 14px;
    }
    .social-btn {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        gap: 8px;
        padding: 13px 18px;
        border-radius: 10px;
        font-weight: 700;
        font-size: 14.5px;
        text-decoration: none !important;
        color: #ffffff !important;
        text-align: center;
        width: 100%;
        box-sizing: border-box;
        transition: all 0.2s ease;
        box-shadow: 0 4px 10px rgba(0,0,0,0.15);
        min-height: 48px;
        touch-action: manipulation;
    }
    .social-btn:hover {
        opacity: 0.92;
        transform: translateY(-2px);
        box-shadow: 0 6px 14px rgba(0,0,0,0.25);
    }
    .social-btn:active {
        transform: scale(0.98);
    }
    .btn-zalo {
        background: linear-gradient(135deg, #0068FF 0%, #0052cc 100%);
        border: 1px solid #004ecc;
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

    /* Step Navigation Hint Box */
    .mobile-step-hint {
        background: #f0f7ff;
        border-left: 4px solid #004c99;
        border-radius: 8px;
        padding: 12px 16px;
        color: #002244;
        font-size: 14px;
        margin-top: 20px;
        margin-bottom: 10px;
        box-shadow: 0 2px 6px rgba(0,0,0,0.05);
    }

    /* Mobile iOS Auto-Zoom Prevention & Touch Targets */
    @media (max-width: 768px) {
        input[type="text"], input[type="number"], textarea, select {
            font-size: 16px !important;
        }
        .social-grid {
            grid-template-columns: 1fr;
            gap: 10px;
        }
        .mobile-step-hint {
            font-size: 13px;
            padding: 10px 12px;
        }
    }
</style>
""", unsafe_allow_html=True)


# --- Helper Functions ---

def wrap_subtitle_text(text: str, max_chars: int = 42) -> str:
    """Ngắt dòng phụ đề chuẩn truyền hình (tối đa 2 dòng để giữ bố cục thẩm mỹ)."""
    words = text.split()
    if len(text) <= max_chars or len(words) <= 3:
        return text
    lines = []
    current_line = []
    current_len = 0
    for w in words:
        if current_len + len(w) + (1 if current_line else 0) > max_chars and current_line:
            lines.append(" ".join(current_line))
            current_line = [w]
            current_len = len(w)
        else:
            current_line.append(w)
            current_len += len(w) + (1 if len(current_line) > 1 else 0)
    if current_line:
        lines.append(" ".join(current_line))
    return r"\N".join(lines[:2])


def format_ass_time(ms: float) -> str:
    """Định dạng thời gian theo chuẩn ASS: H:MM:SS.cc"""
    total_sec = max(0.0, ms / 1000.0)
    h = int(total_sec // 3600)
    m = int((total_sec % 3600) // 60)
    s = int(total_sec % 60)
    cs = int(round((total_sec - int(total_sec)) * 100))
    if cs >= 100:
        cs = 99
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def format_srt_time(ms: float) -> str:
    """Định dạng thời gian theo chuẩn SRT: HH:MM:SS,mmm"""
    total_sec = max(0, int(ms // 1000))
    millis = max(0, int(ms % 1000))
    h = total_sec // 3600
    m = (total_sec % 3600) // 60
    s = total_sec % 60
    return f"{h:02d}:{m:02d}:{s:02d},{millis:03d}"


def generate_default_script(the_loai: str, co_quan: str, tieu_de: str, y_tuong: str, is_khmer: bool = False) -> tuple[str, str]:
    """Sinh kịch bản phóng sự và phụ đề tiếng Việt chuẩn văn phong thời sự địa phương."""
    co_quan_clean = co_quan.strip() if co_quan else "Đơn vị thực hiện"
    the_loai_clean = the_loai.strip() if the_loai else "Chương trình thời sự"
    tieu_de_clean = tieu_de.strip() if tieu_de else "nhiệm vụ trọng tâm và phong trào thi đua tại cơ sở"
    y_tuong_clean = y_tuong.strip() if y_tuong else "Các chỉ tiêu, nhiệm vụ được triển khai đồng bộ, hiệu quả, tạo chuyển biến tích cực trên mọi lĩnh vực đời sống nhân dân."

    vi_script = f"""Kính chào quý vị và các đồng bào! Trong không khí thi đua sôi nổi của toàn Đảng bộ, chính quyền và nhân dân địa phương, {the_loai_clean} hôm nay trân trọng phản ánh những kết quả nổi bật và tinh thần trách nhiệm của cán bộ, nhân dân trong công tác xây dựng quê hương.
Thời gian qua, dưới sự lãnh đạo sâu sát và chủ động của {co_quan_clean}, công tác phối hợp thực hiện {tieu_de_clean.lower()} đã gặt hái được những kết quả rất đỗi tự hào. {y_tuong_clean}
Bà con nhân dân tại cơ sở đều bày tỏ sự phấn khởi, đồng thuận cao trước những đổi thay từng ngày của quê hương. Sự đoàn kết gắn bó keo sơn giữa chính quyền, mặt trận và nhân dân chính là cội nguồn sức mạnh để vượt qua mọi khó khăn.
Phát huy những kết quả đã đạt được, {co_quan_clean} sẽ tiếp tục đồng hành cùng bà con, nhân rộng các mô hình hiệu quả, chung sức đồng lòng xây dựng quê hương ngày càng giàu đẹp, văn minh và ấm no hạnh phúc."""

    if is_khmer:
        km_script = f"""សូមគោរពជម្រាបសួរលោកអ្នកនាង និងបងប្អូនជនរួមជាតិជាទីមេត្រី! នៅក្នុងបរិយាកាស thi đua ដ៏ផុលផុស កម្មវិធីព័ត៌មានថ្ងៃនេះសូមឆ្លុះបញ្ចាំងពីលទ្ធផលលេចធ្លោនៅមូលដ្ឋាន។
ក្រោមការដឹកនាំយ៉ាងយកចិត្តទុកដាក់ និងម្ចាស់ការរបស់ {co_quan_clean} ការអនុវត្តភារកិច្ចទទួលបានសមិទ្ធផលគួរជាទីមោទនៈ។ {y_tuong_clean}
បងប្អូនប្រជាពលរដ្ឋនៅមូលដ្ឋានមានសេចក្តីសប្បាយរីករាយ និងឯកភាពខ្ពស់ចំពោះការផ្លាស់ប្តូររីកចម្រើនជាវិជ្ជមាននៃស្រុកកំណើត។
លើកកម្ពស់លទ្ធផលដែលសម្រេចបាន យើងទាំងអស់គ្នានឹងរួមសាមគ្គីកសាងស្រុកកំណើតឱ្យកាន់តែសម្បូរសប្បាយ និងស៊ីវិល័យ។"""
        return km_script.strip(), vi_script.strip()
    
    return vi_script.strip(), vi_script.strip()


def generate_broadcast_script(the_loai: str, co_quan: str, tieu_de: str, y_tuong: str, is_khmer: bool = False) -> tuple[str, str]:
    """Sinh kịch bản phát thanh & phụ đề tiếng Việt tự động bằng mô hình DeepSeek ngầm."""
    key = (DEFAULT_DEEPSEEK_KEY or "").strip()
    if not key:
        return generate_default_script(the_loai, co_quan, tieu_de, y_tuong, is_khmer=is_khmer)
    
    url = "https://api.deepseek.com/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {key}",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    }
    
    if is_khmer:
        system_prompt = (
            "Bạn là Biên tập viên kỳ cựu của Đài Phát thanh và Truyền hình Sóc Trăng, chuyên trách các chương trình "
            "thời sự tiếng Khmer. Bạn thành thạo cả tiếng Khmer chuẩn mực và tiếng Việt chuẩn phát thanh."
        )
        user_prompt = f"""Hãy viết kịch bản phát thanh truyền hình bằng TIẾNG KHMER để phát thanh viên đọc, kèm theo PHỤ ĐỀ TIẾNG VIỆT tương ứng từng dòng theo thông tin sau:
- Thể loại: {the_loai}
- Cơ quan / Đơn vị thực hiện: {co_quan}
- Tiêu đề: {tieu_de}
- Ý tưởng / Số liệu thực tế: {y_tuong}

Yêu cầu:
1. Kịch bản gồm 4-5 câu ngắn gọn, truyền cảm, nhịp điệu phát thanh viên chuẩn mực.
2. Xuất ra định dạng JSON thuần với đúng 2 trường:
   - "khmer": văn bản tiếng Khmer, các câu ngăn cách nhau bằng ký tự xuống dòng \\n.
   - "vietnamese": văn bản phụ đề tiếng Việt tương ứng chính xác với từng dòng tiếng Khmer, ngăn cách nhau bằng ký tự xuống dòng \\n.
3. Tuyệt đối chỉ trả lời bằng JSON thuần túy, không chèn markdown hay giải thích ngoài JSON."""
    else:
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
        "temperature": 0.5 if is_khmer else 0.7,
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
            
            if is_khmer:
                try:
                    parsed = json.loads(content)
                    km_out = parsed.get("khmer", "")
                    vi_out = parsed.get("vietnamese", "")
                    if isinstance(km_out, list):
                        km_out = "\n".join(km_out)
                    if isinstance(vi_out, list):
                        vi_out = "\n".join(vi_out)
                    if km_out and vi_out:
                        return km_out.strip(), vi_out.strip()
                except Exception:
                    pass
                return content, generate_default_script(the_loai, co_quan, tieu_de, y_tuong, is_khmer=False)[1]
            else:
                return content, content
    except Exception:
        return generate_default_script(the_loai, co_quan, tieu_de, y_tuong, is_khmer=is_khmer)


def translate_script_with_ai(text: str, to_khmer: bool = True) -> str:
    """Dịch kịch bản giữa tiếng Việt và tiếng Khmer giữ nguyên cấu trúc dòng."""
    key = (DEFAULT_DEEPSEEK_KEY or "").strip()
    if not key or not text.strip():
        return text
    
    url = "https://api.deepseek.com/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {key}",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    }
    
    target_lang = "tiếng Khmer chuẩn phát thanh" if to_khmer else "tiếng Việt chuẩn thời sự"
    system_prompt = "Bạn là biên dịch viên thời sự song ngữ tiếng Khmer - tiếng Việt của Đài Phát thanh và Truyền hình Sóc Trăng."
    user_prompt = f"Hãy dịch văn bản sau sang {target_lang}. Giữ nguyên cấu trúc dòng, mỗi dòng gốc tương ứng một dòng dịch, không thêm bất kỳ lời giải thích nào:\n{text}"
    
    payload = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": 0.2,
        "max_tokens": 1600
    }
    try:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers=headers, method="POST")
        ssl_ctx = ssl._create_unverified_context()
        with urllib.request.urlopen(req, timeout=35, context=ssl_ctx) as resp:
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
        return text


def translate_inputs_to_khmer(title_vi: str, notes_vi: str) -> tuple[str, str]:
    """Tự động dịch Tiêu đề và Nội dung/Số liệu từ tiếng Việt sang tiếng Khmer chuẩn thời sự."""
    title_clean = title_vi.strip()
    notes_clean = notes_vi.strip()
    if not title_clean and not notes_clean:
        return "", ""
    
    key = (DEFAULT_DEEPSEEK_KEY or "").strip()
    if not key:
        return title_clean, notes_clean

    prompt = f"""Hãy dịch tiêu đề và nội dung/số liệu sự kiện sau từ tiếng Việt sang TIẾNG KHMER chuẩn phát thanh thời sự Sóc Trăng:
Tiêu đề tiếng Việt: {title_clean}
Nội dung/Số liệu tiếng Việt: {notes_clean}

Yêu cầu xuất ra định dạng JSON thuần túy gồm 2 trường:
- "title_khmer": tiêu đề tiếng Khmer ngắn gọn, trang trọng chuẩn truyền hình.
- "notes_khmer": nội dung sự kiện / số liệu dịch sang tiếng Khmer chính xác.
Tuyệt đối chỉ trả lời JSON thuần túy, không chèn markdown hay giải thích ngoài JSON."""

    url = "https://api.deepseek.com/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {key}",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    }
    payload = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": "Bạn là biên dịch viên thời sự tiếng Khmer của Đài Phát thanh và Truyền hình Sóc Trăng."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.2,
        "max_tokens": 1200
    }
    try:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers=headers, method="POST")
        ssl_ctx = ssl._create_unverified_context()
        with urllib.request.urlopen(req, timeout=30, context=ssl_ctx) as resp:
            resp_data = json.loads(resp.read().decode("utf-8"))
            content = resp_data["choices"][0]["message"]["content"].strip()
            if content.startswith("```"):
                lines = content.splitlines()
                if lines[0].startswith("```"):
                    lines = lines[1:]
                if lines and lines[-1].startswith("```"):
                    lines = lines[:-1]
                content = "\n".join(lines).strip()
            parsed = json.loads(content)
            return parsed.get("title_khmer", title_clean), parsed.get("notes_khmer", notes_clean)
    except Exception:
        t_km = translate_script_with_ai(title_clean, to_khmer=True) if title_clean else ""
        n_km = translate_script_with_ai(notes_clean, to_khmer=True) if notes_clean else ""
        return t_km, n_km



def text_to_ssml(text: str, voice_name: str) -> str:
    """Chuyển đổi lời bình thành cấu trúc ngắt nghỉ chuẩn phát thanh viên."""
    cleaned = re.sub(r'[\r\t]', '', text)
    paragraphs = [p.strip() for p in cleaned.split('\n') if p.strip()]
    
    ssml_paragraphs = []
    for p in paragraphs:
        p_ssml = re.sub(r'([,;])\s*', r'\1 <break time="300ms"/> ', p)
        p_ssml = re.sub(r'([\.\!\?\:។])\s*', r'\1 <break time="600ms"/> ', p_ssml)
        ssml_paragraphs.append(f"    <s>{p_ssml.strip()}</s>\n    <break time=\"1000ms\"/>")
    
    inner_content = "\n".join(ssml_paragraphs)
    xml_lang = "km-KH" if "km-" in voice_name else "vi-VN"
    full_ssml = f"""<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="{xml_lang}">
  <voice name="{voice_name}">
{inner_content}
  </voice>
</speak>"""
    return full_ssml


async def synthesize_speech(text_or_ssml: str, output_path: str, voice_name: str):
    """Tổng hợp giọng đọc BTV bằng edge-tts chuẩn phát thanh."""
    clean_text = re.sub(r'<[^>]+>', '', text_or_ssml)
    clean_text = re.sub(r'\s+', ' ', clean_text).strip()
    rate = "-2%" if "vi-" in voice_name else "+0%"
    communicate = edge_tts.Communicate(text=clean_text, voice=voice_name, rate=rate)
    await communicate.save(output_path)


async def synthesize_speech_and_subtitles(
    spoken_text: str,
    voice_name: str,
    subtitle_text: str,
    output_audio_path: str,
    output_ass_path: str,
    output_srt_path: str,
    aspect_ratio: str = "16:9",
    lt_duration: float = 4.0
):
    """
    Tổng hợp giọng đọc BTV (Tiếng Khmer hoặc Tiếng Việt) 
    và trích xuất chính xác thời gian hiển thị phụ đề tiếng Việt chuẩn truyền hình.
    """
    clean_spoken = re.sub(r'<[^>]+>', '', spoken_text).strip()
    spoken_lines = [l.strip() for l in clean_spoken.splitlines() if l.strip()]
    if not spoken_lines:
        spoken_lines = [clean_spoken]
    
    clean_subs = re.sub(r'<[^>]+>', '', subtitle_text).strip()
    sub_lines = [l.strip() for l in clean_subs.splitlines() if l.strip()]
    if not sub_lines:
        sub_lines = spoken_lines[:]

    # Nối lại bằng newline để edge-tts nhận diện từng câu theo từng dòng
    text_to_synthesize = "\n".join(spoken_lines)
    rate = "-2%" if "vi-" in voice_name else "+0%"

    timings = []
    # Gọi edge-tts stream với cơ chế thử lại (retry) nếu mạng chập chờn
    last_err = None
    for attempt in range(3):
        try:
            comm = edge_tts.Communicate(text=text_to_synthesize, voice=voice_name, rate=rate)
            timings.clear()
            with open(output_audio_path, "wb") as f_audio:
                async for chunk in comm.stream():
                    if chunk["type"] == "audio":
                        f_audio.write(chunk["data"])
                    elif chunk["type"] == "SentenceBoundary":
                        # Giọng BTV được mix trễ 800ms (lead-in) vào video
                        start_ms = 800.0 + (chunk["offset"] / 10000.0)
                        end_ms = start_ms + (chunk["duration"] / 10000.0)
                        timings.append((start_ms, end_ms))
            if os.path.exists(output_audio_path) and os.path.getsize(output_audio_path) > 100:
                last_err = None
                break
        except Exception as e:
            last_err = e
            await asyncio.sleep(1.0)
            
    if last_err is not None:
        raise RuntimeError(f"Lỗi khi tổng hợp giọng đọc edge-tts: {last_err}")

    # Fallback timing nếu edge-tts không trả về SentenceBoundary
    if not timings and os.path.exists(output_audio_path):
        try:
            audio_seg = AudioSegment.from_file(output_audio_path, format="mp3", codec="mp3")
            total_speech_ms = float(len(audio_seg))
        except Exception:
            total_speech_ms = 30000.0

        n = len(sub_lines)
        seg_dur = total_speech_ms / max(n, 1)
        cur_t = 800.0
        for _ in range(n):
            timings.append((cur_t, cur_t + seg_dur))
            cur_t += seg_dur

    # Cấu hình phong cách hiển thị phụ đề theo tỷ lệ khung hình
    if aspect_ratio == "9:16":
        res_x, res_y = 720, 1280
        font_size = 23
        margin_v_normal = 140   # Tránh nút tương tác TikTok ở đáy màn hình
        margin_v_intro = 265    # Nằm ngay trên Lower Third banner (đã tính chiều cao banner 138px)
        max_chars = 32
    else:
        res_x, res_y = 1280, 720
        font_size = 20
        margin_v_normal = 28    # Vị trí chuẩn chân trang truyền hình
        margin_v_intro = 175    # Nằm ngay trên Lower Third banner (đã tính chiều cao banner 138px)
        max_chars = 48

    ass_header = f"""[Script Info]
Title: Vietnamese Subtitles
ScriptType: v4.00+
WrapStyle: 0
PlayResX: {res_x}
PlayResY: {res_y}
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: SubNormal,Arial,{font_size},&H00FFFFFF,&H000000FF,&H00000000,&HB0000000,-1,0,0,0,100,100,0,0,3,3,0,2,25,25,{margin_v_normal},1
Style: SubIntro,Arial,{font_size},&H00FFFFFF,&H000000FF,&H00000000,&HB0000000,-1,0,0,0,100,100,0,0,3,3,0,2,25,25,{margin_v_intro},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    ass_events = []
    srt_events = []

    for idx, (s_ms, e_ms) in enumerate(timings):
        sub_text_raw = sub_lines[idx] if idx < len(sub_lines) else (spoken_lines[idx] if idx < len(spoken_lines) else "")
        if not sub_text_raw.strip():
            continue
        wrapped_sub = wrap_subtitle_text(sub_text_raw, max_chars=max_chars)
        style_to_use = "SubIntro" if s_ms < (lt_duration * 1000.0) else "SubNormal"

        ass_events.append(
            f"Dialogue: 0,{format_ass_time(s_ms)},{format_ass_time(e_ms)},{style_to_use},,0,0,0,,{wrapped_sub}"
        )
        srt_sub = wrapped_sub.replace(r"\N", "\n")
        srt_events.append(
            f"{len(srt_events) + 1}\n{format_srt_time(s_ms)} --> {format_srt_time(e_ms)}\n{srt_sub}\n"
        )

    # Nếu sub_lines nhiều hơn timings, thêm dòng cuối mượt mà
    if len(sub_lines) > len(timings) and timings:
        last_end = timings[-1][1]
        for extra_idx in range(len(timings), len(sub_lines)):
            txt = sub_lines[extra_idx].strip()
            if not txt:
                continue
            s_extra = last_end + 300.0
            e_extra = s_extra + 3500.0
            last_end = e_extra
            wrapped_sub = wrap_subtitle_text(txt, max_chars=max_chars)
            ass_events.append(
                f"Dialogue: 0,{format_ass_time(s_extra)},{format_ass_time(e_extra)},SubNormal,,0,0,0,,{wrapped_sub}"
            )
            srt_sub = wrapped_sub.replace(r"\N", "\n")
            srt_events.append(
                f"{len(srt_events) + 1}\n{format_srt_time(s_extra)} --> {format_srt_time(e_extra)}\n{srt_sub}\n"
            )

    with open(output_ass_path, "w", encoding="utf-8") as f_ass:
        f_ass.write(ass_header + "\n".join(ass_events) + "\n")

    with open(output_srt_path, "w", encoding="utf-8") as f_srt:
        f_srt.write("\n".join(srt_events) + "\n")



def get_khmer_compatible_fonts():
    """
    Tìm font hỗ trợ đầy đủ cả Tiếng Việt và Tiếng Khmer (Leelawadee UI / KhmerOS / Noto Sans Khmer).
    Đảm bảo 100% không lỗi ô vuông (tofu) trên cả Windows và Linux (Streamlit Cloud).
    """
    base_dir = os.path.dirname(os.path.abspath(__file__))
    bundled_bold = os.path.join(base_dir, "assets", "fonts", "LeelaUIb.ttf")
    bundled_reg = os.path.join(base_dir, "assets", "fonts", "LeelawUI.ttf")
    
    candidate_bold_fonts = [
        bundled_bold,
        "C:/Windows/Fonts/LeelaUIb.ttf",
        "C:/Windows/Fonts/khmeruib.ttf",
        "C:/Windows/Fonts/segoeuib.ttf",
        "C:/Windows/Fonts/arialbd.ttf",
        "/usr/share/fonts/truetype/khmeros/KhmerOSsys.ttf",
        "/usr/share/fonts/truetype/khmeros/KhmerOS_sys.ttf",
        "/usr/share/fonts/truetype/khmeros/KhmerOS.ttf",
        "/usr/share/fonts/opentype/noto/NotoSansKhmer-Bold.ttf",
        "/usr/share/fonts/truetype/noto/NotoSansKhmer-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
    ]
    candidate_reg_fonts = [
        bundled_reg,
        "C:/Windows/Fonts/LeelawUI.ttf",
        "C:/Windows/Fonts/khmerui.ttf",
        "C:/Windows/Fonts/segoeui.ttf",
        "C:/Windows/Fonts/arial.ttf",
        "/usr/share/fonts/truetype/khmeros/KhmerOS.ttf",
        "/usr/share/fonts/truetype/khmeros/KhmerOSsys.ttf",
        "/usr/share/fonts/opentype/noto/NotoSansKhmer-Regular.ttf",
        "/usr/share/fonts/truetype/noto/NotoSansKhmer-Regular.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
    ]
    bold_path = next((p for p in candidate_bold_fonts if os.path.exists(p)), None)
    reg_path = next((p for p in candidate_reg_fonts if os.path.exists(p)), None)
    return bold_path, reg_path


def is_khmer_text(text: str) -> bool:
    """Kiểm tra chuỗi có chứa ký tự tiếng Khmer hay không."""
    return any('\u1780' <= c <= '\u17ff' or '\u19e0' <= c <= '\u19ff' for c in (text or ""))


def fit_title_to_lines(text: str, max_w: int, font_path: str, is_narrow: bool = False):
    """
    Tự động xuống dòng tối đa 2 dòng và thu nhỏ cỡ chữ linh hoạt,
    đảm bảo tiêu đề phóng sự không bao giờ bị tràn hoặc mất chữ (cả tiếng Việt và Khmer).
    """
    dummy_img = Image.new("RGBA", (1, 1))
    draw = ImageDraw.Draw(dummy_img)
    font_sizes = [21, 19, 17, 16, 15, 14, 13] if is_narrow else [24, 22, 20, 18, 16, 15, 14]
    cluster_re = re.compile(r'(?:[\u1780-\u17a2](?:\u17d2[\u1780-\u17a2]|[\u17b4-\u17d3\u17dd])*|[\s\S])')
    
    clean_text = " ".join(text.strip().split())
    if not clean_text:
        font = ImageFont.truetype(font_path, font_sizes[0]) if font_path else ImageFont.load_default()
        return font, [""], font_sizes[0]
        
    for fs in font_sizes:
        font = ImageFont.truetype(font_path, fs) if font_path else ImageFont.load_default()
        bbox = draw.textbbox((0, 0), clean_text, font=font)
        if (bbox[2] - bbox[0]) <= max_w:
            return font, [clean_text], fs
            
        words = clean_text.split(" ") if " " in clean_text else cluster_re.findall(clean_text)
        join_char = " " if " " in clean_text else ""
        lines = []
        cur_line = ""
        
        for w in words:
            test_line = (cur_line + join_char + w) if cur_line else w
            t_bbox = draw.textbbox((0, 0), test_line, font=font)
            if (t_bbox[2] - t_bbox[0]) <= max_w:
                cur_line = test_line
            else:
                if cur_line:
                    lines.append(cur_line)
                    cur_line = w
                else:
                    lines.append(w)
                    cur_line = ""
        if cur_line:
            lines.append(cur_line)
            
        if len(lines) <= 2:
            return font, lines, fs
            
    # Trường hợp tiêu đề quá dài vượt mức tối đa, gói gọn vào 2 dòng an toàn
    final_font = ImageFont.truetype(font_path, font_sizes[-1]) if font_path else ImageFont.load_default()
    line1 = lines[0] if lines else ""
    line2 = (" " if " " in clean_text else "").join(lines[1:]) if len(lines) > 1 else ""
    if (draw.textbbox((0, 0), line2, font=final_font)[2] - draw.textbbox((0, 0), line2, font=final_font)[0]) > max_w:
        clusters = cluster_re.findall(line2)
        trimmed = ""
        for c in clusters:
            if (draw.textbbox((0, 0), trimmed + c + "...", font=final_font)[2] - draw.textbbox((0, 0), trimmed + c + "...", font=final_font)[0]) <= max_w:
                trimmed += c
            else:
                break
        line2 = trimmed + "..."
    return final_font, [line1, line2], font_sizes[-1]


def fit_single_line_text(text: str, max_w: int, font_path: str, start_size: int = 18, min_size: int = 12):
    """Tự động thu nhỏ cỡ chữ để dòng thông tin (cơ quan thực hiện) nằm vừa vặn trên 1 dòng duy nhất."""
    dummy_img = Image.new("RGBA", (1, 1))
    draw = ImageDraw.Draw(dummy_img)
    clean_text = " ".join(text.strip().split())
    cluster_re = re.compile(r'(?:[\u1780-\u17a2](?:\u17d2[\u1780-\u17a2]|[\u17b4-\u17d3\u17dd])*|[\s\S])')
    
    for fs in range(start_size, min_size - 1, -1):
        font = ImageFont.truetype(font_path, fs) if font_path else ImageFont.load_default()
        bbox = draw.textbbox((0, 0), clean_text, font=font)
        if (bbox[2] - bbox[0]) <= max_w:
            return font, clean_text, fs
            
    font = ImageFont.truetype(font_path, min_size) if font_path else ImageFont.load_default()
    clusters = cluster_re.findall(clean_text)
    trimmed = ""
    for c in clusters:
        if (draw.textbbox((0, 0), trimmed + c + "...", font=font)[2] - draw.textbbox((0, 0), trimmed + c + "...", font=font)[0]) <= max_w:
            trimmed += c
        else:
            break
    return font, trimmed + "...", min_size


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
    font_path_bold, _ = get_khmer_compatible_fonts()
    font = ImageFont.truetype(font_path_bold, 15) if font_path_bold else ImageFont.load_default()
    
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


def create_lower_third_image(width: int, height: int, title: str, co_quan: str, the_loai: str, output_path: str, is_khmer: bool = False):
    """
    Tạo banner Lower-Third đồ họa truyền hình sang trọng (#003366 + Vàng Gold) dạng PNG trong suốt.
    Hỗ trợ hiển thị hoàn hảo chữ tiếng Việt và tiếng Khmer không bị lỗi font,
    tự động co giãn cỡ chữ và xuống dòng thông minh để không bao giờ bị mất hoặc tràn chữ.
    """
    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    is_narrow = width < 800
    lt_w = min(1140, width - 48)
    max_text_w = lt_w - 60
    
    font_path_bold, font_path_reg = get_khmer_compatible_fonts()
    
    # Xử lý tự động xuống dòng và co giãn cỡ chữ cho Tiêu đề
    font_title, title_lines, _ = fit_title_to_lines(title, max_text_w, font_path_bold, is_narrow)
    has_2_lines = len(title_lines) >= 2
    
    # Chiều cao banner linh hoạt: 114px nếu 1 dòng, 138px nếu 2 dòng tiêu đề
    lt_h = 138 if has_2_lines else 114
    lt_x = (width - lt_w) // 2
    bottom_pad = 110 if height > width else 28  # Tránh nút TikTok nếu video dọc
    lt_y = height - lt_h - bottom_pad
    
    # Lớp đổ bóng mờ
    shadow_box = [lt_x + 3, lt_y + 3, lt_x + lt_w + 3, lt_y + lt_h + 3]
    draw.rounded_rectangle(shadow_box, radius=14, fill=(0, 0, 0, 160))
    
    # Khung nền chính
    main_box = [lt_x, lt_y, lt_x + lt_w, lt_y + lt_h]
    draw.rounded_rectangle(main_box, radius=14, fill=(0, 42, 86, 235), outline=(255, 193, 7, 245), width=3)
    
    # Dải đỏ tin tức bên trái
    draw.rounded_rectangle([lt_x, lt_y, lt_x + 16, lt_y + lt_h], radius=7, fill=(217, 4, 41, 255))
    
    # Tag thể loại nhỏ trên đầu
    font_tag = ImageFont.truetype(font_path_bold, 13) if font_path_bold else ImageFont.load_default()
    tag_clean = the_loai.upper() if not (is_khmer or is_khmer_text(the_loai)) else the_loai
    t_bbox = draw.textbbox((0, 0), tag_clean, font=font_tag)
    tag_w = (t_bbox[2] - t_bbox[0]) + 18
    tag_box = [lt_x + 28, lt_y + 11, lt_x + 28 + tag_w, lt_y + 31]
    draw.rounded_rectangle(tag_box, radius=4, fill=(255, 184, 0, 255))
    draw.text((lt_x + 37, lt_y + 20), tag_clean, fill=(0, 32, 64), font=font_tag, anchor="lm")
    
    # Xử lý dòng Cơ quan thực hiện (tự động co giãn để không bị tràn màn hình)
    clean_co_quan = (co_quan or "").strip()
    is_km_active = is_khmer or is_khmer_text(clean_co_quan) or is_khmer_text(title)
    if is_km_active:
        prefix = "អង្គភាពអនុវត្ត: "
        if clean_co_quan.startswith("អង្គភាពអនុវត្ត:") or clean_co_quan.startswith("Cơ quan thực hiện:"):
            full_agency = clean_co_quan
        else:
            full_agency = f"{prefix}{clean_co_quan}" if clean_co_quan else prefix.strip()
    else:
        prefix = "Cơ quan thực hiện: "
        if clean_co_quan.startswith("Cơ quan thực hiện:") or clean_co_quan.startswith("អង្គភាពអនុវត្ត:"):
            full_agency = clean_co_quan
        else:
            full_agency = f"{prefix}{clean_co_quan}" if clean_co_quan else prefix.strip()
            
    font_sub, agency_display, _ = fit_single_line_text(
        full_agency, max_text_w, font_path_reg, 18 if not is_narrow else 16, 12
    )
    
    # Vẽ Tiêu đề và Tên Cơ quan
    if has_2_lines:
        draw.text((lt_x + 28, lt_y + 52), title_lines[0], fill=(255, 255, 255), font=font_title, anchor="lm")
        draw.text((lt_x + 28, lt_y + 78), title_lines[1], fill=(255, 255, 255), font=font_title, anchor="lm")
        draw.text((lt_x + 28, lt_y + 110), agency_display, fill=(255, 215, 0), font=font_sub, anchor="lm")
    else:
        draw.text((lt_x + 28, lt_y + 56), title_lines[0], fill=(255, 255, 255), font=font_title, anchor="lm")
        draw.text((lt_x + 28, lt_y + 90), agency_display, fill=(255, 215, 0), font=font_sub, anchor="lm")
        
    img.save(output_path, "PNG")


def mix_audio_with_ducking(voice_path: str, bgm_path: str, output_path: str, ducking_volume: float = 0.15) -> float:
    """Mix giọng đọc BTV với nhạc nền phóng sự BGM áp dụng Audio Ducking chuẩn (hoặc chỉ xuất giọng nếu không dùng BGM)."""
    try:
        voice = AudioSegment.from_file(voice_path, format="mp3", codec="mp3")
    except Exception:
        voice = AudioSegment.from_file(voice_path)
    voice = voice + 3.0
    
    voice_duration_ms = len(voice)
    total_duration_ms = voice_duration_ms + 2500

    # Nếu không dùng nhạc nền (hoặc không tìm thấy file nhạc)
    if not bgm_path or not os.path.exists(bgm_path):
        silence_start = AudioSegment.silent(duration=800)
        silence_end = AudioSegment.silent(duration=1700)
        final_mix = silence_start + voice + silence_end
        final_mix.export(output_path, format="mp3", bitrate="192k")
        return total_duration_ms / 1000.0
    
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


def process_photo_slideshow(
    source_files: list,
    tmpdir: str,
    total_duration: float,
    target_w: int = 1280,
    target_h: int = 720,
    enable_transition: bool = True
):
    """Chuẩn hóa toàn bộ ảnh về chuẩn kích thước, tự động xoay EXIF, và tạo hiệu ứng chuyển cảnh mờ chồng mượt mà."""
    normalized_canvases = []
    for idx, f_item in enumerate(source_files):
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
        normalized_canvases.append(canvas)
        
    num_photos = len(normalized_canvases)
    duration_per_photo = max(total_duration / max(num_photos, 1), 3.0)
    
    concat_list_path = os.path.join(tmpdir, "photos_concat.txt")
    concat_entries = []
    
    trans_dur = 0.5  # Thời gian chuyển cảnh hòa tan 0.5 giây
    num_trans_frames = 10  # 10 khung hình trung gian
    frame_step_dur = trans_dur / num_trans_frames
    
    for i in range(num_photos):
        base_frame_path = os.path.join(tmpdir, f"std_frame_{i:03d}.jpg")
        normalized_canvases[i].save(base_frame_path, "JPEG", quality=95)
        
        # Tạo hiệu ứng chuyển tiếp hòa tan nếu có nhiều hơn 1 ảnh và không phải ảnh cuối
        if enable_transition and num_photos > 1 and i < num_photos - 1 and duration_per_photo > (trans_dur + 0.8):
            hold_dur = duration_per_photo - trans_dur
            concat_entries.append((base_frame_path, hold_dur))
            
            for f in range(num_trans_frames):
                alpha = (f + 1) / (num_trans_frames + 1)
                blended = Image.blend(normalized_canvases[i], normalized_canvases[i+1], alpha)
                trans_path = os.path.join(tmpdir, f"trans_{i:03d}_{f:02d}.jpg")
                blended.save(trans_path, "JPEG", quality=95)
                concat_entries.append((trans_path, frame_step_dur))
        else:
            concat_entries.append((base_frame_path, duration_per_photo))

    with open(concat_list_path, "w", encoding="utf-8") as f:
        for p, dur in concat_entries:
            clean_p = os.path.abspath(p).replace('\\', '/')
            f.write(f"file '{clean_p}'\n")
            f.write(f"duration {dur:.3f}\n")
        last_clean_p = os.path.abspath(concat_entries[-1][0]).replace('\\', '/')
        f.write(f"file '{last_clean_p}'\n")
        
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
    vfx_style: str = "cinematic",
    ducking_volume: float = 0.15,
    ass_subtitle_path: str = "",
    output_video_path: str = "",
    progress_bar = None,
    status_text = None,
    is_khmer: bool = False
):
    """
    Quy trình Render Video Phóng sự Hoàn Chỉnh:
    - Logo + Tên đơn vị bên dưới nằm ở góc trái/phải
    - Lower-Third chỉ hiển thị 10% thời lượng rồi tự động mờ dần biến mất
    - Hiển thị phụ đề tiếng Việt chuẩn đồ họa truyền hình (tránh che Lower-Third)
    - Hỗ trợ tỷ lệ 16:9 (YouTube/Facebook) hoặc 9:16 (TikTok/Reels/Shorts)
    - Tích hợp hiệu ứng hình ảnh (VFX) và tùy chỉnh nhạc nền linh hoạt
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
        total_duration = mix_audio_with_ducking(voice_path, bgm_path, mixed_audio_path, ducking_volume=ducking_volume)
        
        # Bước 2: Tạo banner Lower Third và Cụm Logo có chữ bên dưới
        if status_text:
            status_text.info("Đang khởi tạo đồ họa truyền hình: Lower Third và Cụm Logo đơn vị...")
        if progress_bar:
            progress_bar.progress(35)
            
        lt_image_path = os.path.join(tmpdir, "lower_third.png")
        create_lower_third_image(out_w, out_h, title, co_quan, the_loai, lt_image_path, is_khmer=is_khmer)
        
        logo_badge_path = os.path.join(tmpdir, "logo_badge.png")
        create_logo_badge_image(logo_path, logo_subtext, logo_badge_path)
        
        # Tính thời lượng hiển thị Lower-Third: đúng 10% thời lượng của video (tối thiểu 4.0s)
        lt_duration = max(total_duration * 0.10, 4.0)
        fade_start = max(lt_duration - 0.8, 0.5)

        # Bước 3: Chuẩn hóa tư liệu ảnh / video hiện trường
        if status_text:
            status_text.info("Đang chuẩn hóa tư liệu hình ảnh / video hiện trường và áp dụng hiệu ứng...")
        if progress_bar:
            progress_bar.progress(55)
            
        enable_trans = "mượt" in vfx_style.lower() or "điện ảnh" in vfx_style.lower()
        if source_type == "photo":
            input_args = process_photo_slideshow(source_files, tmpdir, total_duration, out_w, out_h, enable_transition=enable_trans)
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

        # Tùy chỉnh bộ lọc màu sắc hình ảnh theo VFX được chọn
        if "điện ảnh" in vfx_style.lower():
            color_grading = ",eq=contrast=1.06:saturation=1.12:brightness=0.01,unsharp=5:5:0.8:5:5:0.0"
        elif "màu sắc" in vfx_style.lower():
            color_grading = ",eq=contrast=1.05:saturation=1.15:brightness=0.01"
        else:
            color_grading = ""

        # Ghép nối các lớp đồ họa và phụ đề
        if ass_subtitle_path and os.path.exists(ass_subtitle_path):
            clean_ass = ass_subtitle_path.replace('\\', '/').replace(':', '\\:')
            sub_filter = f"[v_logo]ass='{clean_ass}'[vout]"
            logo_out_label = "[v_logo]; "
        else:
            sub_filter = ""
            logo_out_label = "[vout]"

        filter_complex = (
            f"[0:v]scale={out_w}:{out_h}:force_original_aspect_ratio=decrease,pad={out_w}:{out_h}:(ow-iw)/2:(oh-ih)/2,setsar=1,fps=30{color_grading},format=yuv420p[base]; "
            f"[1:v]format=rgba,fade=t=out:st={fade_start:.2f}:d=0.8:alpha=1[lt_faded]; "
            f"[base][lt_faded]overlay=0:0:enable='lte(t,{lt_duration:.2f})'[v_lt]; "
            f"[2:v]format=rgba[logo]; "
            f"[v_lt][logo]{logo_overlay}{logo_out_label}{sub_filter}"
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
if "script_text_vi" not in st.session_state:
    st.session_state.script_text_vi = ""
if "text_area_script_vi" not in st.session_state:
    st.session_state.text_area_script_vi = ""
if "script_text_km" not in st.session_state:
    st.session_state.script_text_km = ""
if "text_area_script_km" not in st.session_state:
    st.session_state.text_area_script_km = ""
if "subtitle_text_km" not in st.session_state:
    st.session_state.subtitle_text_km = ""
if "text_area_sub_km" not in st.session_state:
    st.session_state.text_area_sub_km = ""
if "ssml_text" not in st.session_state:
    st.session_state.ssml_text = ""
if "text_area_ssml" not in st.session_state:
    st.session_state.text_area_ssml = ""
if "recorded_audio_path" not in st.session_state:
    st.session_state.recorded_audio_path = None
if "rendered_video_path" not in st.session_state:
    st.session_state.rendered_video_path = None
if "rendered_ass_path" not in st.session_state:
    st.session_state.rendered_ass_path = None
if "rendered_srt_path" not in st.session_state:
    st.session_state.rendered_srt_path = None
if "has_subtitles" not in st.session_state:
    st.session_state.has_subtitles = False
if "title_km" not in st.session_state:
    st.session_state.title_km = ""
if "notes_km" not in st.session_state:
    st.session_state.notes_km = ""


# --- APP INTERFACE ---

the_loai_default = "Bản tin thời sự cơ sở"
co_quan_default = ""

# 1. Top Banner với Logo Ứng Dụng
logo_html_img = f'<img src="data:image/png;base64,{APP_LOGO_B64}" alt="Logo App" style="width: 64px; height: 64px; border-radius: 14px; box-shadow: 0 4px 14px rgba(0,0,0,0.35); border: 2.5px solid #FFD166; object-fit: cover; flex-shrink: 0;">' if APP_LOGO_B64 else '<span style="font-size: 42px;">🎥</span>'

with st.container():
    st.markdown(f"""
    <div class="tv-header-container">
        <div style="display: flex; align-items: center; gap: 16px; flex: 1 1 320px;">
            {logo_html_img}
            <div class="tv-header-brand">
                <span class="tv-live-badge">● TRUYỀN HÌNH</span>
                <h1 class="tv-header-title">HỆ THỐNG BIÊN TẬP VIDEO PHÓNG SỰ</h1>
                <div class="tv-header-subtitle">Sản xuất video tin tức & phóng sự tự động bằng AI</div>
            </div>
        </div>
        <div class="tv-header-owner-box">
            <div class="tv-owner-tag">🏛️ BẢN QUYỀN</div>
            <div class="tv-owner-company">CÔNG TY TNHH MTV GIẢI PHÁP THANH TOÁN TRỰC TUYẾN SÓC TRĂNG</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

# Khung hướng dẫn cài đặt ứng dụng vào điện thoại
with st.expander("📲 Hướng Dẫn Cài Đặt App Trực Tiếp Vào Màn Hình Điện Thoại (iOS / Android)", expanded=False):
    col_inst_l, col_inst_r = st.columns([1, 2.5])
    with col_inst_l:
        if os.path.exists(APP_MOBILE_LOGO_PATH):
            st.image(APP_MOBILE_LOGO_PATH, caption="Biểu tượng App khi ghim vào điện thoại", use_container_width=True)
    with col_inst_r:
        st.markdown("""
        <div style="background: #f8fafc; border: 1px solid #cbd5e1; border-radius: 10px; padding: 14px; color: #1e293b;">
            <div style="font-weight: 800; font-size: 15px; color: #003366; margin-bottom: 8px;">
                🚀 Ghim ứng dụng ra màn hình chính để mở toàn màn hình (dùng như App tải từ Store, không cần gõ web)
            </div>
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 12px; margin-top: 10px;">
                <div style="background: #ffffff; border-radius: 8px; padding: 10px 12px; border-left: 4px solid #007aff; box-shadow: 0 2px 5px rgba(0,0,0,0.05);">
                    <strong style="color: #007aff;">🍎 Trên iPhone / iPad (Safari):</strong>
                    <ol style="margin: 6px 0 0 16px; padding: 0; font-size: 13px; line-height: 1.55;">
                        <li>Mở trang web bằng trình duyệt <strong>Safari</strong></li>
                        <li>Bấm nút <strong>Chia sẻ</strong> (biểu tượng <span style="font-size: 15px;">📤</span> ở đáy màn hình)</li>
                        <li>Cuộn xuống tìm và chọn <strong>"Thêm vào MH chính"</strong> (Add to Home Screen)</li>
                        <li>Bấm <strong>"Thêm" (Add)</strong> ở góc trên bên phải.</li>
                    </ol>
                </div>
                <div style="background: #ffffff; border-radius: 8px; padding: 10px 12px; border-left: 4px solid #34a853; box-shadow: 0 2px 5px rgba(0,0,0,0.05);">
                    <strong style="color: #1e7e34;">🤖 Trên Android (Chrome / Cốc Cốc):</strong>
                    <ol style="margin: 6px 0 0 16px; padding: 0; font-size: 13px; line-height: 1.55;">
                        <li>Mở trang web bằng <strong>Google Chrome</strong></li>
                        <li>Bấm nút <strong>3 chấm</strong> (<span style="font-size: 15px;">⋮</span>) ở góc trên bên phải</li>
                        <li>Chọn <strong>"Cài đặt ứng dụng"</strong> hoặc <strong>"Thêm vào Màn hình chính"</strong></li>
                        <li>Bấm <strong>"Cài đặt" / "Thêm"</strong> để xác nhận.</li>
                    </ol>
                </div>
            </div>
            <div style="margin-top: 10px; font-size: 12.5px; color: #64748b;">
                💡 <em>Sau khi ghim, Logo biểu tượng <strong>Truyền Hình Số</strong> sẽ xuất hiện trên màn hình điện thoại. Chạm vào biểu tượng sẽ mở ứng dụng tức thì.</em>
            </div>
        </div>
        """, unsafe_allow_html=True)

# 2. Nhập thông tin & Tư liệu
st.markdown("""
<div class="broadcast-card-header">
    🎬 THÔNG TIN & TƯ LIỆU
</div>
""", unsafe_allow_html=True)

# Khung cấu hình Đơn vị & Logo
with st.expander("⚙️ Tên đơn vị & Logo", expanded=False):
    col_u1, col_u2 = st.columns(2)
    with col_u1:
        the_loai_input = st.text_input(
            "Thể loại:",
            value=the_loai_default,
            placeholder="Bản tin, phóng sự..."
        )
    with col_u2:
        co_quan_input = st.text_input(
            "Đơn vị thực hiện:",
            value=co_quan_default,
            placeholder="UBND Xã, Ban ngành..."
        )
        
    col_l1, col_l2 = st.columns(2)
    with col_l1:
        logo_file = st.file_uploader(
            "Logo (PNG/JPG):",
            type=["png", "jpg", "jpeg"]
        )
    with col_l2:
        logo_subtext_input = st.text_input(
            "Chữ dưới logo:",
            value="",
            placeholder="Để trống nếu chỉ hiện logo"
        )
        logo_pos = st.selectbox(
            "Vị trí logo:",
            options=["Góc trên phải", "Góc trên trái"],
            index=0
        )
        logo_pos_val = "Top-Left" if "trái" in logo_pos.lower() else "Top-Right"

if 'the_loai_input' not in locals() or not the_loai_input.strip():
    the_loai_input = "Bản tin thời sự cơ sở"
if 'co_quan_input' not in locals():
    co_quan_input = ""
if 'logo_subtext_input' not in locals():
    logo_subtext_input = ""
if 'logo_pos_val' not in locals():
    logo_pos_val = "Top-Right"

if 'logo_file' in locals() and logo_file is not None:
    temp_logo_path = os.path.join(tempfile.gettempdir(), "uploaded_logo.png")
    with open(temp_logo_path, "wb") as f:
        f.write(logo_file.getvalue())
    active_logo_path = temp_logo_path
else:
    active_logo_path = DEFAULT_LOGO_PATH

# Thanh trạng thái
display_unit = logo_subtext_input.strip() or co_quan_input.strip() or "Đơn vị cơ sở"
current_mode_is_km = "Khmer" in st.session_state.get("selected_video_mode", "Tiếng Kinh")
current_has_sub = st.session_state.get("enable_subtitles_chk", False)

mode_badge = "🇰🇭 BTV Tiếng Khmer" if current_mode_is_km else "🇻🇳 BTV Tiếng Kinh"
sub_badge = "💬 Có phụ đề tiếng Việt" if current_has_sub else "🚫 Không phụ đề"

st.markdown(f"""
<div class="tv-status-bar">
    <div><strong>📺 {the_loai_input.upper()}</strong> &nbsp;|&nbsp; Đơn vị: <span style="color: #FFD166; font-weight: 700;">{display_unit}</span></div>
    <div class="tv-status-tags">
        <span class="tv-chip">🎙️ {mode_badge}</span>
        <span class="tv-chip">{sub_badge}</span>
        <span class="tv-chip">Logo: {logo_pos_val}</span>
        <span class="tv-chip">⚡ Xử lý tự động AI</span>
    </div>
</div>
""", unsafe_allow_html=True)

# 1. Tư liệu hiện trường
st.markdown("##### 🎬 1. Tư liệu hiện trường:")
input_type = st.radio(
    "Định dạng tư liệu hiện trường:",
    options=["Bộ ảnh (JPG/PNG)", "Video (MP4/MOV)"],
    index=0,
    horizontal=True,
    label_visibility="collapsed"
)

selected_source_type = "photo" if "ảnh" in input_type.lower() else "video"
selected_files = []

if selected_source_type == "photo":
    uploaded_photos = st.file_uploader(
        "Chọn ảnh từ thiết bị:",
        type=["jpg", "jpeg", "png", "webp"],
        accept_multiple_files=True
    )
    if uploaded_photos:
        selected_files = [up.getvalue() for up in uploaded_photos]
        st.success(f"✅ Đã nhận {len(selected_files)} ảnh.")
        preview_count = min(len(selected_files), 4)
        p_cols = st.columns(2)
        for i in range(preview_count):
            with p_cols[i % 2]:
                st.image(selected_files[i], caption=f"Ảnh {i+1}", use_container_width=True)
        if len(selected_files) > 4:
            st.caption(f"... và {len(selected_files) - 4} ảnh khác.")
else:
    uploaded_video = st.file_uploader(
        "Chọn video từ thiết bị:",
        type=["mp4", "mov", "avi", "mkv", "webm"]
    )
    if uploaded_video:
        selected_files = [uploaded_video.getvalue()]
        file_mb = uploaded_video.size / (1024 * 1024)
        st.success(f"✅ Đã nhận video: **{uploaded_video.name}** ({file_mb:.1f} MB).")

st.markdown("---")

# 2. Chế độ video & Giọng đọc BTV & Khung hình (Nằm trên Tiêu đề và Nội dung)
st.markdown("##### 🌐 2. Chế độ video phóng sự & Giọng đọc BTV:")

mode_c1, mode_c2 = st.columns([1.6, 1.2])
with mode_c1:
    selected_mode = st.radio(
        "Chọn chế độ ngôn ngữ:",
        options=["🇻🇳 Video Tiếng Việt", "🇰🇭 Video Tiếng Khmer"],
        index=0,
        horizontal=True,
        key="selected_video_mode"
    )
    is_khmer = "Khmer" in selected_mode

with mode_c2:
    aspect_choice = st.selectbox(
        "📐 Tỷ lệ khung hình:",
        options=["16:9 (Ngang - TV/FB/YT)", "9:16 (Dọc - TikTok/Reels)"],
        index=0
    )
    aspect_ratio_val = "9:16" if "9:16" in aspect_choice else "16:9"

col_v1, col_v2 = st.columns([1.4, 1.4])
with col_v1:
    if is_khmer:
        voice_choice = st.selectbox(
            "🎙️ Giọng đọc BTV Tiếng Khmer:",
            options=["Nữ Khmer (Sreymom)", "Nam Khmer (Piseth)"],
            index=0
        )
        voice_name = "km-KH-SreymomNeural" if ("Nữ" in voice_choice or "Sreymom" in voice_choice) else "km-KH-PisethNeural"
    else:
        voice_choice = st.selectbox(
            "🎙️ Giọng đọc BTV Tiếng Việt (Nam Bộ):",
            options=["Nữ Nam Bộ (Hoài My)", "Nam Nam Bộ (Nam Minh)"],
            index=0
        )
        voice_name = "vi-VN-HoaiMyNeural" if ("Nữ" in voice_choice or "Hoài My" in voice_choice) else "vi-VN-NamMinhNeural"

with col_v2:
    preview_audio_file = VOICE_PREVIEWS.get(voice_name)
    if preview_audio_file and os.path.exists(preview_audio_file):
        st.markdown(f"<div style='font-size: 13px; font-weight: 700; color: #003366; margin-bottom: 4px;'>🔊 Nghe thử giọng ({voice_choice.split()[0]}):</div>", unsafe_allow_html=True)
        st.audio(preview_audio_file, format="audio/mp3")

st.markdown("---")

# 3. Tiêu đề
st.markdown("##### 📝 3. Tiêu đề phóng sự:")
title_input = st.text_input(
    "Tiêu đề phóng sự / bản tin (nhập tiếng Việt):",
    value="",
    placeholder="Ví dụ: Đại hội đại biểu Mặt trận Tổ quốc xã An Ninh lần thứ X...",
    key="input_title_vi"
)

# 4. Nội dung sự kiện / Số liệu
st.markdown("##### 📊 4. Nội dung / Số liệu sự kiện:")
notes_input = st.text_area(
    "Nội dung / Số liệu sự kiện (nhập tiếng Việt):",
    value="",
    height=100,
    placeholder="Nhập nội dung sự kiện, số liệu thực tế bằng tiếng Việt để AI xử lý biên soạn...",
    key="input_notes_vi"
)

# Nếu chọn tiếng Khmer: Tự động dịch thuật tiêu đề & nội dung sang tiếng Khmer
if is_khmer:
    col_trans1, col_trans2 = st.columns([1.6, 2.4])
    with col_trans1:
        if st.button("🔄 Dịch tiêu đề & nội dung sang Khmer", key="btn_trans_inputs_km", help="Bấm để dịch ngay tiêu đề và nội dung tiếng Việt sang tiếng Khmer"):
            t_vi = title_input.strip()
            n_vi = notes_input.strip()
            if t_vi or n_vi:
                with st.spinner("Đang dịch thuật tiêu đề và số liệu sang tiếng Khmer..."):
                    km_t, km_n = translate_inputs_to_khmer(t_vi, n_vi)
                    st.session_state.title_km = km_t
                    st.session_state.notes_km = km_n
                    st.rerun()
    with col_trans2:
        st.caption("💡 *Hệ thống tự động dịch thuật tiêu đề & nội dung khi bạn bấm 'AI soạn kịch bản' bên dưới.*")

    with st.expander("🇰🇭 Bản dịch Tiêu đề & Nội dung tiếng Khmer (Tự động cập nhật)", expanded=bool(st.session_state.title_km or st.session_state.notes_km)):
        def on_title_km_change():
            st.session_state.title_km = st.session_state.text_input_title_km

        st.text_input(
            "Tiêu đề tiếng Khmer (hiển thị trên video):",
            value=st.session_state.title_km,
            key="text_input_title_km",
            on_change=on_title_km_change,
            placeholder="Tự động dịch sang tiếng Khmer..."
        )

        def on_notes_km_change():
            st.session_state.notes_km = st.session_state.text_area_notes_km

        st.text_area(
            "Nội dung / Số liệu tiếng Khmer (để AI soạn kịch bản):",
            value=st.session_state.notes_km,
            key="text_area_notes_km",
            height=85,
            on_change=on_notes_km_change,
            placeholder="Tự động dịch sang tiếng Khmer..."
        )

st.markdown("---")

# 5. Kịch bản lời bình BTV
st.markdown("##### 📝 5. Kịch bản lời bình BTV:")
if is_khmer:
    with st.expander("📝 Kịch bản lời bình BTV Tiếng Khmer (Tùy chọn — AI tự viết nếu để trống)", expanded=False):
        btn_col1, btn_col2 = st.columns([1.5, 1.2])
        with btn_col1:
            if st.button("✨ AI soạn kịch bản tiếng Khmer", key="btn_preview_script_km"):
                with st.spinner("Đang tự động dịch thuật và soạn kịch bản tiếng Khmer..."):
                    t_vi = title_input.strip()
                    n_vi = notes_input.strip()
                    if (t_vi or n_vi) and (not st.session_state.title_km or not st.session_state.notes_km):
                        km_t, km_n = translate_inputs_to_khmer(t_vi, n_vi)
                        st.session_state.title_km = km_t
                        st.session_state.notes_km = km_n

                    gen_km, gen_vi = generate_broadcast_script(
                        the_loai=the_loai_input,
                        co_quan=co_quan_input,
                        tieu_de=st.session_state.title_km or t_vi,
                        y_tuong=st.session_state.notes_km or n_vi,
                        is_khmer=True
                    )
                    st.session_state.script_text_km = gen_km
                    st.session_state.text_area_script_km = gen_km
                    st.session_state.subtitle_text_km = gen_vi
                    st.session_state.text_area_sub_km = gen_vi
                    st.session_state.ssml_text = text_to_ssml(gen_km, voice_name)
                    st.session_state.text_area_ssml = st.session_state.ssml_text
                    st.rerun()

        with btn_col2:
            if st.button("📋 Kịch bản mẫu", key="btn_preview_sample_km"):
                t_vi = title_input.strip()
                n_vi = notes_input.strip()
                sample_km, sample_vi = generate_default_script(
                    the_loai=the_loai_input,
                    co_quan=co_quan_input,
                    tieu_de=st.session_state.title_km or t_vi,
                    y_tuong=st.session_state.notes_km or n_vi,
                    is_khmer=True
                )
                st.session_state.script_text_km = sample_km
                st.session_state.text_area_script_km = sample_km
                st.session_state.subtitle_text_km = sample_vi
                st.session_state.text_area_sub_km = sample_vi
                st.session_state.ssml_text = text_to_ssml(sample_km, voice_name)
                st.session_state.text_area_ssml = st.session_state.ssml_text
                st.rerun()

        def on_script_km_change():
            st.session_state.script_text_km = st.session_state.text_area_script_km
            st.session_state.ssml_text = text_to_ssml(st.session_state.text_area_script_km, voice_name)
            st.session_state.text_area_ssml = st.session_state.ssml_text

        st.text_area(
            "Văn bản tiếng Khmer (BTV phát thanh đọc — mỗi dòng là một câu):",
            value=st.session_state.script_text_km,
            height=130,
            key="text_area_script_km",
            on_change=on_script_km_change,
            placeholder="Nhập tiếng Khmer hoặc bấm 'AI soạn kịch bản' để tự động tạo..."
        )

else:
    with st.expander("📝 Kịch bản lời bình BTV Tiếng Việt (Tùy chọn — AI tự viết nếu để trống)", expanded=False):
        btn_col1, btn_col2 = st.columns([1.4, 1])
        with btn_col1:
            if st.button("✨ AI soạn kịch bản tiếng Việt", key="btn_preview_script_vi"):
                with st.spinner("Đang soạn lời bình tiếng Việt..."):
                    gen_vi, _ = generate_broadcast_script(
                        the_loai=the_loai_input,
                        co_quan=co_quan_input,
                        tieu_de=title_input,
                        y_tuong=notes_input,
                        is_khmer=False
                    )
                    st.session_state.script_text_vi = gen_vi
                    st.session_state.text_area_script_vi = gen_vi
                    st.session_state.ssml_text = text_to_ssml(gen_vi, voice_name)
                    st.session_state.text_area_ssml = st.session_state.ssml_text
                    st.rerun()

        with btn_col2:
            if st.button("📋 Kịch bản mẫu", key="btn_preview_sample_vi"):
                sample_vi, _ = generate_default_script(
                    the_loai=the_loai_input,
                    co_quan=co_quan_input,
                    tieu_de=title_input,
                    y_tuong=notes_input,
                    is_khmer=False
                )
                st.session_state.script_text_vi = sample_vi
                st.session_state.text_area_script_vi = sample_vi
                st.session_state.ssml_text = text_to_ssml(sample_vi, voice_name)
                st.session_state.text_area_ssml = st.session_state.ssml_text
                st.rerun()

        def on_script_vi_change():
            st.session_state.script_text_vi = st.session_state.text_area_script_vi
            st.session_state.ssml_text = text_to_ssml(st.session_state.text_area_script_vi, voice_name)
            st.session_state.text_area_ssml = st.session_state.ssml_text

        st.text_area(
            "Nội dung lời bình BTV đọc (tiếng Việt — mỗi dòng là một câu):",
            value=st.session_state.script_text_vi,
            height=130,
            key="text_area_script_vi",
            on_change=on_script_vi_change,
            placeholder="Nhập nội dung lời bình hoặc để trống để AI tự biên soạn..."
        )

def on_ssml_change():
    st.session_state.ssml_text = st.session_state.text_area_ssml

with st.expander("⏱️ Cấu trúc ngắt nhịp (SSML)", expanded=False):
    st.text_area(
        "Nhịp điệu phát thanh:",
        value=st.session_state.ssml_text,
        height=90,
        key="text_area_ssml",
        on_change=on_ssml_change
    )

st.markdown("---")

# 6. Tùy chọn Phụ đề tiếng Việt (SAU ĐÓ MỚI CHỌN TẠO PHỤ ĐỀ)
enable_subtitles = st.checkbox(
    "💬 Tạo phụ đề tiếng Việt trên video",
    value=False,
    key="enable_subtitles_chk",
    help="Mặc định tắt phụ đề để khung hình video thông thoáng, sạch sẽ. Chỉ kích chọn khi bạn muốn hiển thị dòng chữ phụ đề chạy theo lời bình BTV trên video."
)

if enable_subtitles:
    if is_khmer:
        with st.expander("🇻🇳 Xem & Tùy chỉnh Phụ đề tiếng Việt trên video", expanded=True):
            def on_sub_km_change():
                st.session_state.subtitle_text_km = st.session_state.text_area_sub_km

            st.text_area(
                "Nội dung phụ đề tiếng Việt hiển thị trên video (tương ứng từng câu với tiếng Khmer):",
                value=st.session_state.subtitle_text_km,
                height=110,
                key="text_area_sub_km",
                on_change=on_sub_km_change,
                placeholder="Phụ đề tiếng Việt tương ứng từng câu tiếng Khmer..."
            )
            if st.button("🔄 Dịch lời bình Khmer sang Phụ đề Việt", key="btn_trans_km_to_vi_sub"):
                km_txt = st.session_state.script_text_km.strip() or st.session_state.text_area_script_km.strip()
                if km_txt:
                    with st.spinner("Đang dịch sang phụ đề tiếng Việt..."):
                        sub_vi = translate_script_with_ai(km_txt, to_khmer=False)
                        st.session_state.subtitle_text_km = sub_vi
                        st.session_state.text_area_sub_km = sub_vi
                        st.rerun()
    else:
        st.caption("💬 *Phụ đề tiếng Việt trên video sẽ tự động hiển thị đồng bộ chính xác theo từng dòng lời bình BTV ở trên.*")

# 7. Cấu hình mặc định ngầm cho BGM & VFX (MẶC ĐỊNH LÀ TẮT)
active_bgm_path = ""
ducking_vol = 0.15
vfx_choice = "Tiêu chuẩn (Gốc)"
bgm_summary_label = "Tắt nhạc"
vfx_summary_label = "Gốc"

# Tùy chọn nâng cao (Thu gọn mặc định — MẶC ĐỊNH LÀ TẮT)
with st.expander("⚙️ Tùy chọn: Nhạc nền & Hiệu ứng (Mặc định tắt)", expanded=False):
    adv_col1, adv_col2 = st.columns(2)
    with adv_col1:
        use_bgm = st.checkbox("Bật nhạc nền", value=False)
        if use_bgm:
            bgm_genre = st.selectbox(
                "Phong cách nhạc:",
                options=[
                    "Thời sự chính luận",
                    "Nông thôn mới",
                    "Phóng sự truyền cảm",
                    "Tải lên file riêng"
                ],
                index=0
            )
            ducking_choice = st.selectbox(
                "Mức giảm nhạc (Ducking):",
                options=[
                    "15% (Chuẩn)",
                    "10% (Nhẹ)",
                    "20% (Rõ giọng)",
                    "25% (Nhạc nhỏ)"
                ],
                index=0
            )
            ducking_map = {
                "15% (Chuẩn)": 0.15,
                "10% (Nhẹ)": 0.25,
                "20% (Rõ giọng)": 0.10,
                "25% (Nhạc nhỏ)": 0.05
            }
            ducking_vol = ducking_map.get(ducking_choice, 0.15)
            if "Tải lên" in bgm_genre:
                custom_bgm = st.file_uploader(
                    "Tải file nhạc (.mp3, .wav):",
                    type=["mp3", "wav", "m4a", "ogg"]
                )
                if custom_bgm:
                    custom_bgm_path = os.path.join(tempfile.gettempdir(), f"custom_bgm_{custom_bgm.name}")
                    with open(custom_bgm_path, "wb") as cbf:
                        cbf.write(custom_bgm.getvalue())
                    active_bgm_path = custom_bgm_path
            elif "Nông thôn" in bgm_genre:
                active_bgm_path = BGM_NONG_THON_PATH
            elif "Phóng sự" in bgm_genre:
                active_bgm_path = BGM_TRUYEN_CAM_PATH
            else:
                active_bgm_path = BGM_CHINH_LUAN_PATH
            
            bgm_summary_label = f"{bgm_genre} ({ducking_choice.split()[0]})"
        else:
            active_bgm_path = ""
            bgm_summary_label = "Tắt nhạc"

    with adv_col2:
        use_vfx = st.checkbox("Bật hiệu ứng hình ảnh", value=False)
        if use_vfx:
            vfx_choice = st.selectbox(
                "Hiệu ứng:",
                options=[
                    "Điện ảnh (Mượt + Sắc nét)",
                    "Chuyển cảnh mượt",
                    "Màu sắc rực rỡ"
                ],
                index=0
            )
            vfx_summary_label = vfx_choice
        else:
            vfx_choice = "Tiêu chuẩn (Gốc)"
            vfx_summary_label = "Gốc"

# Nút tạo video
st.markdown("<div style='margin-top: 18px; margin-bottom: 18px;'>", unsafe_allow_html=True)
render_btn = st.button(
    "🚀 TẠO VIDEO TỰ ĐỘNG",
    key="btn_auto_render",
    type="primary",
    use_container_width=True
)
st.markdown("</div>", unsafe_allow_html=True)

if render_btn:
    if len(selected_files) == 0:
        st.error("⚠️ Vui lòng tải lên ít nhất một ảnh hoặc video ở mục 1.")
        st.stop()

    # 1. Soạn kịch bản & Phụ đề nếu chưa có
    if is_khmer:
        t_vi = title_input.strip()
        n_vi = notes_input.strip()
        if (t_vi or n_vi) and (not st.session_state.title_km or not st.session_state.notes_km):
            with st.spinner("🤖 [1/3] Đang tự động dịch tiêu đề & nội dung sang tiếng Khmer..."):
                km_t, km_n = translate_inputs_to_khmer(t_vi, n_vi)
                if not st.session_state.title_km:
                    st.session_state.title_km = km_t
                if not st.session_state.notes_km:
                    st.session_state.notes_km = km_n

        script_to_speak = st.session_state.script_text_km.strip()
        subtitles_to_use = st.session_state.subtitle_text_km.strip() if enable_subtitles else ""

        if not script_to_speak:
            with st.spinner("🤖 [1/3] AI đang viết kịch bản phát thanh tiếng Khmer..."):
                gen_km, gen_vi = generate_broadcast_script(
                    the_loai=the_loai_input,
                    co_quan=co_quan_input,
                    tieu_de=st.session_state.title_km or t_vi,
                    y_tuong=st.session_state.notes_km or n_vi,
                    is_khmer=True
                )
                st.session_state.script_text_km = gen_km
                st.session_state.text_area_script_km = gen_km
                st.session_state.subtitle_text_km = gen_vi
                st.session_state.text_area_sub_km = gen_vi
                st.session_state.ssml_text = text_to_ssml(gen_km, voice_name)
                st.session_state.text_area_ssml = st.session_state.ssml_text
                script_to_speak = gen_km
                if enable_subtitles:
                    subtitles_to_use = gen_vi
        elif enable_subtitles and not subtitles_to_use:
            with st.spinner("🤖 [1/3] AI đang tạo phụ đề tiếng Việt tương ứng..."):
                subtitles_to_use = translate_script_with_ai(script_to_speak, to_khmer=False)
                st.session_state.subtitle_text_km = subtitles_to_use
                st.session_state.text_area_sub_km = subtitles_to_use
    else:
        script_to_speak = st.session_state.script_text_vi.strip()
        subtitles_to_use = script_to_speak if enable_subtitles else ""

        if not script_to_speak:
            with st.spinner("🤖 [1/3] AI đang viết kịch bản phát thanh tiếng Việt..."):
                gen_vi, _ = generate_broadcast_script(
                    the_loai=the_loai_input,
                    co_quan=co_quan_input,
                    tieu_de=title_input,
                    y_tuong=notes_input,
                    is_khmer=False
                )
                st.session_state.script_text_vi = gen_vi
                st.session_state.text_area_script_vi = gen_vi
                st.session_state.ssml_text = text_to_ssml(gen_vi, voice_name)
                st.session_state.text_area_ssml = st.session_state.ssml_text
                script_to_speak = gen_vi
                if enable_subtitles:
                    subtitles_to_use = gen_vi

    # 2. Thu âm BTV (và trích xuất phụ đề NẾU người dùng kích chọn)
    temp_audio_file = os.path.join(tempfile.gettempdir(), f"btv_voice_{voice_name.replace('-', '_')}.mp3")
    temp_ass_file = os.path.join(tempfile.gettempdir(), f"subtitles_{aspect_ratio_val.replace(':', '_')}.ass")
    temp_srt_file = os.path.join(tempfile.gettempdir(), f"subtitles_{aspect_ratio_val.replace(':', '_')}.srt")

    lang_tag = "BTV Tiếng Khmer" if is_khmer else "BTV Tiếng Kinh"

    if enable_subtitles:
        with st.spinner(f"🎙️ [2/3] Đang thu âm giọng đọc {lang_tag} & tạo phụ đề tiếng Việt..."):
            try:
                asyncio.run(synthesize_speech_and_subtitles(
                    spoken_text=script_to_speak,
                    voice_name=voice_name,
                    subtitle_text=subtitles_to_use,
                    output_audio_path=temp_audio_file,
                    output_ass_path=temp_ass_file,
                    output_srt_path=temp_srt_file,
                    aspect_ratio=aspect_ratio_val,
                    lt_duration=4.0
                ))
                st.session_state.recorded_audio_path = temp_audio_file
                st.session_state.rendered_ass_path = temp_ass_file
                st.session_state.rendered_srt_path = temp_srt_file
            except Exception as e:
                st.error(f"Lỗi thu âm và tạo phụ đề: {str(e)}")
                st.stop()
    else:
        with st.spinner(f"🎙️ [2/3] Đang thu âm giọng đọc {lang_tag}..."):
            try:
                asyncio.run(synthesize_speech(
                    text_or_ssml=script_to_speak,
                    output_path=temp_audio_file,
                    voice_name=voice_name
                ))
                st.session_state.recorded_audio_path = temp_audio_file
                st.session_state.rendered_ass_path = None
                st.session_state.rendered_srt_path = None
            except Exception as e:
                st.error(f"Lỗi thu âm: {str(e)}")
                st.stop()

    # 3. Render video
    render_progress = st.progress(0)
    render_status = st.empty()
    output_video_file = os.path.join(tempfile.gettempdir(), f"final_phong_su_{aspect_ratio_val.replace(':', '_')}.mp4")

    active_sub_path = temp_ass_file if (enable_subtitles and os.path.exists(temp_ass_file)) else ""
    try:
        render_full_report_video(
            source_type=selected_source_type,
            source_files=selected_files,
            voice_path=st.session_state.recorded_audio_path,
            bgm_path=active_bgm_path,
            logo_path=active_logo_path,
            logo_subtext=logo_subtext_input,
            logo_position=logo_pos_val,
            title=((st.session_state.title_km.strip() if (is_khmer and st.session_state.title_km.strip()) else title_input.strip()) or ("ព័ត៌មានមូលដ្ឋាន" if is_khmer else "BẢN TIN CƠ SỞ")),
            co_quan=co_quan_input.strip() or ("អង្គភាពមូលដ្ឋាន" if is_khmer else "ĐƠN VỊ CƠ SỞ"),
            the_loai=("ព័ត៌មាន" if is_khmer else (the_loai_input.strip() or "THỜI SỰ")),
            aspect_ratio=aspect_ratio_val,
            vfx_style=vfx_choice,
            ducking_volume=ducking_vol,
            ass_subtitle_path=active_sub_path,
            output_video_path=output_video_file,
            progress_bar=render_progress,
            status_text=render_status,
            is_khmer=is_khmer
        )
        st.session_state.rendered_video_path = output_video_file
        st.session_state.has_subtitles = enable_subtitles
        st.success("✅ Xuất video thành công!")
    except Exception as e:
        st.error(f"Lỗi render video: {str(e)}")

# Kết quả
if st.session_state.rendered_video_path and os.path.exists(st.session_state.rendered_video_path):
    st.markdown("---")
    st.markdown(f"#### 📺 Video hoàn chỉnh ({aspect_choice.split()[0]}):")
    st.video(st.session_state.rendered_video_path)
    
    clean_unit_filename = re.sub(r'[^a-zA-Z0-9_]', '', co_quan_input.strip().replace(' ', '_').lower()) or "co_so"
    has_srt = st.session_state.get("has_subtitles", False) and st.session_state.rendered_srt_path and os.path.exists(st.session_state.rendered_srt_path)
    
    if has_srt:
        col_dl1, col_dl2, col_dl3 = st.columns(3)
    else:
        col_dl1, col_dl2 = st.columns(2)
        
    with col_dl1:
        with open(st.session_state.rendered_video_path, "rb") as vf:
            video_bytes = vf.read()
            st.download_button(
                label="📥 Tải Video (.mp4)",
                data=video_bytes,
                file_name=f"phong_su_{clean_unit_filename}_{aspect_ratio_val.replace(':', '_')}.mp4",
                mime="video/mp4",
                key="btn_download_video",
                use_container_width=True
            )
            
    with col_dl2:
        if st.session_state.recorded_audio_path and os.path.exists(st.session_state.recorded_audio_path):
            with open(st.session_state.recorded_audio_path, "rb") as af:
                audio_bytes = af.read()
                st.download_button(
                    label="📻 Tải Âm Thanh (.mp3)",
                    data=audio_bytes,
                    file_name=f"ban_tin_phat_thanh_{clean_unit_filename}.mp3",
                    mime="audio/mp3",
                    key="btn_download_audio",
                    use_container_width=True
                )

    if has_srt:
        with col_dl3:
            with open(st.session_state.rendered_srt_path, "rb") as sf:
                srt_bytes = sf.read()
                st.download_button(
                    label="📝 Tải Phụ Đề (.srt)",
                    data=srt_bytes,
                    file_name=f"phu_de_tieng_viet_{clean_unit_filename}.srt",
                    mime="text/plain",
                    key="btn_download_srt",
                    use_container_width=True
                )

    # Đăng lên mạng xã hội
    st.markdown("""
    <div style="background: linear-gradient(135deg, #091e3a 0%, #102e56 100%); border: 2px solid #FFB800; border-radius: 12px; padding: 16px 18px; margin-top: 18px; color: #ffffff;">
        <div style="display: flex; align-items: center; justify-content: space-between; border-bottom: 1px solid rgba(255,184,0,0.35); padding-bottom: 8px; margin-bottom: 10px;">
            <div style="font-size: 15px; font-weight: 800; color: #FFB800;">
                📲 ĐĂNG LÊN MẠNG XÃ HỘI
            </div>
            <span style="background: #059669; color: #ffffff; font-size: 11px; padding: 2px 8px; border-radius: 10px; font-weight: 700;">TIỆN ÍCH</span>
        </div>
        <div style="font-size: 13px; color: #e1edff; margin-bottom: 12px;">
            Mở nhanh trang đăng video:
        </div>
        <div class="social-grid">
            <a href="https://chat.zalo.me/" target="_blank" class="social-btn btn-zalo">
                <span>💬</span> Zalo
            </a>
            <a href="https://business.facebook.com/latest/content_management" target="_blank" class="social-btn btn-facebook">
                <span>🔵</span> Facebook
            </a>
            <a href="https://studio.youtube.com/channel/_/videos/upload?d=pt" target="_blank" class="social-btn btn-youtube">
                <span>🔴</span> YouTube
            </a>
            <a href="https://www.tiktok.com/creator-center/upload?from=webapp" target="_blank" class="social-btn btn-tiktok">
                <span>⚫</span> TikTok
            </a>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Tiêu đề & Hashtags
    clean_tag_unit = re.sub(r'[^a-zA-Z0-9_]', '', co_quan_input.replace(' ', '_').lower())
    hashtag_unit_str = f"#{clean_tag_unit} " if clean_tag_unit else ""
    khmer_tags = "#khmer #truyenhinhkhmer " if is_khmer else ""
    if is_khmer and enable_subtitles:
        khmer_tags += "#phudetiengviet "

    curr_spoken_script = st.session_state.script_text_km if is_khmer else st.session_state.script_text_vi
    curr_sub_script = st.session_state.subtitle_text_km if is_khmer else curr_spoken_script
    has_active_subs = st.session_state.get("has_subtitles", False)

    sub_section_text = f"\n---\nPhụ đề tiếng Việt:\n{curr_sub_script}\n" if (has_active_subs and curr_sub_script) else ""
    lang_info_str = ("Tiếng Khmer" + (" (có phụ đề tiếng Việt)" if has_active_subs else "")) if is_khmer else ("Tiếng Kinh (Tiếng Việt)" + (" (có phụ đề)" if has_active_subs else ""))

    auto_caption = f"""{title_input.strip() or ('ព័ត៌មានមូលដ្ឋាន' if is_khmer else 'BẢN TIN PHÓNG SỰ')}

🏛️ Cơ quan thực hiện: {co_quan_input.strip() or 'Đơn vị cơ sở'}
📺 Thể loại: {the_loai_input.strip()}
🌐 Ngôn ngữ: {lang_info_str}

{curr_spoken_script}
{sub_section_text}
---
#phongsu #thoisu {hashtag_unit_str}{khmer_tags}#truyenhinhcoso #tintuc24h #soctrang #daidoanket #nongthonmoi #xuhuong #fyp"""

    with st.expander("📋 Tiêu đề & Hashtags đăng bài", expanded=True):
        st.text_area(
            "Nội dung bài đăng:",
            value=auto_caption,
            height=150,
            key="social_copy_text"
        )
        st.caption("💡 Mẹo: Bấm Tải video ở trên, rồi dán nội dung này vào bài đăng.")

    with st.expander("📖 Lời bình đã đọc" + (" & Phụ đề" if has_active_subs else ""), expanded=False):
        if has_active_subs and is_khmer:
            col_view1, col_view2 = st.columns(2)
            with col_view1:
                st.markdown("**Lời bình BTV (Tiếng Khmer):**")
                st.write(curr_spoken_script)
                if st.session_state.recorded_audio_path and os.path.exists(st.session_state.recorded_audio_path):
                    st.audio(st.session_state.recorded_audio_path, format="audio/mp3")
            with col_view2:
                st.markdown("**Phụ đề tiếng Việt hiển thị trên video:**")
                st.write(curr_sub_script)
        else:
            st.markdown(f"**Lời bình BTV ({'Tiếng Khmer' if is_khmer else 'Tiếng Kinh'}):**")
            st.write(curr_spoken_script)
            if st.session_state.recorded_audio_path and os.path.exists(st.session_state.recorded_audio_path):
                st.audio(st.session_state.recorded_audio_path, format="audio/mp3")


# --- Footer ---
st.markdown("""
<div style="text-align: center; color: #64748b; font-size: 13px; margin-top: 28px; padding-top: 14px; border-top: 1px solid #cbd5e1;">
    <strong>Biên tập Video Phóng sự</strong> • Bản quyền: <strong>CÔNG TY TNHH MTV GIẢI PHÁP THANH TOÁN TRỰC TUYẾN SÓC TRĂNG</strong>
</div>
""", unsafe_allow_html=True)
