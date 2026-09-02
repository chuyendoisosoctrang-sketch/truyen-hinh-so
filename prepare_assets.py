import os
import math
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import wave
import subprocess
import imageio_ffmpeg

os.makedirs("assets", exist_ok=True)
ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()

print("Generating default logo: assets/default_logo.png...")
# Generate a professional TV emblem logo (300x120 RGBA)
w, h = 320, 100
logo_img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
draw = ImageDraw.Draw(logo_img)

# Background rounded box with glassmorphism / gradient look
# Border and base box
box_coords = [4, 8, w - 6, h - 10]
# Draw subtle drop shadow
draw.rounded_rectangle([box_coords[0]+2, box_coords[1]+2, box_coords[2]+2, box_coords[3]+2], radius=14, fill=(0, 0, 0, 140))
# Draw primary gradient container (#002244 to #003366)
draw.rounded_rectangle(box_coords, radius=14, fill=(0, 36, 75, 235), outline=(255, 193, 7, 240), width=3)

# Left emblem badge: Red badge with "THCS"
badge_rect = [12, 16, 85, h - 18]
draw.rounded_rectangle(badge_rect, radius=8, fill=(185, 28, 28, 255), outline=(255, 215, 0, 255), width=2)
# Draw broadcast wave / antenna icon
center_x = (badge_rect[0] + badge_rect[2]) // 2
draw.arc([center_x - 18, 22, center_x + 18, 58], 200, 340, fill=(255, 255, 255, 240), width=2)
draw.arc([center_x - 12, 28, center_x + 12, 52], 200, 340, fill=(255, 255, 255, 240), width=2)
draw.ellipse([center_x - 4, 38, center_x + 4, 46], fill=(255, 215, 0, 255))
# Text in badge
draw.text((center_x, 62), "THCS", fill=(255, 255, 255), anchor="mm")

# Main Text: TRUYỀN HÌNH ĐỊA PHƯƠNG - PHÓNG SỰ CƠ SỞ
draw.text((98, 32), "TRUYỀN HÌNH ĐỊA PHƯƠNG", fill=(255, 225, 100), anchor="lm")
draw.text((98, 54), "PHÁT THANH - TRUYỀN HÌNH CƠ SỞ", fill=(220, 235, 255), anchor="lm")
draw.text((98, 72), "TIN CẬY - KỊP THỜI - ĐỔI MỚI", fill=(160, 190, 230), anchor="lm")

logo_img.save("assets/default_logo.png", "PNG")
print("Logo saved.")

print("Generating sample photo: assets/sample_photo_1.jpg & sample_photo_2.jpg...")
# Photo 1: Con đường nông thôn mới & công trình đại đoàn kết
p1 = Image.new("RGB", (1280, 720), (35, 120, 75))
draw1 = ImageDraw.Draw(p1)
# Sky gradient
for y in range(400):
    r = int(100 + (190 - 100) * (y / 400))
    g = int(180 + (220 - 180) * (y / 400))
    b = int(240 + (255 - 240) * (y / 400))
    draw1.line([(0, y), (1280, y)], fill=(r, g, b))
# Sun
draw1.ellipse([1000, 80, 1120, 200], fill=(255, 245, 180))
# Hills & trees
draw1.polygon([(0, 420), (300, 320), (700, 400), (1280, 310), (1280, 720), (0, 720)], fill=(34, 110, 52))
draw1.polygon([(0, 450), (450, 380), (950, 440), (1280, 390), (1280, 720), (0, 720)], fill=(46, 139, 87))
# Concrete road
draw1.polygon([(480, 720), (600, 460), (680, 460), (800, 720)], fill=(200, 205, 210))
draw1.line([(640, 720), (640, 460)], fill=(255, 255, 255), width=4)
# House & flags
draw1.rectangle([200, 380, 380, 520], fill=(230, 220, 190), outline=(120, 60, 30), width=3)
draw1.polygon([(180, 380), (290, 300), (400, 380)], fill=(180, 50, 40))
# Banner text
draw1.rectangle([100, 60, 750, 130], fill=(0, 40, 85))
draw1.rectangle([100, 60, 750, 130], outline=(255, 215, 0), width=3)
draw1.text((425, 95), "CÔNG TRÌNH ĐẠI ĐOÀN KẾT - NÔNG THÔN MỚI", fill=(255, 255, 255), anchor="mm")
p1.save("assets/sample_photo_1.jpg", "JPEG", quality=92)

# Photo 2: Hội nghị & Trao quà an sinh xã hội
p2 = Image.new("RGB", (1280, 720), (25, 35, 60))
draw2 = ImageDraw.Draw(p2)
for y in range(720):
    r = int(20 + 20 * (y / 720))
    g = int(35 + 30 * (y / 720))
    b = int(70 + 40 * (y / 720))
    draw2.line([(0, y), (1280, y)], fill=(r, g, b))
draw2.rectangle([80, 70, 1200, 200], fill=(160, 20, 20), outline=(255, 215, 0), width=4)
draw2.text((640, 110), "ỦY BAN MẶT TRẬN TỔ QUỐC VIỆT NAM XÃ LAI HÒA", fill=(255, 255, 255), anchor="mm")
draw2.text((640, 155), "LỄ BÀN GIAO NHÀ ĐẠI ĐOÀN KẾT & TRAO QUÀ AN SINH XÃ HỘI", fill=(255, 230, 80), anchor="mm")
# Podium & flags
draw2.rectangle([450, 350, 830, 680], fill=(139, 69, 19), outline=(100, 40, 10), width=3)
draw2.rectangle([180, 420, 380, 650], fill=(200, 180, 150))
draw2.rectangle([900, 420, 1100, 650], fill=(200, 180, 150))
p2.save("assets/sample_photo_2.jpg", "JPEG", quality=92)
print("Sample photos saved.")

print("Generating TV News BGM: assets/bgm_news.mp3...")
# Synthesize a broadcast news background track (warm, rhythmic, inspiring tempo)
sample_rate = 44100
duration_sec = 45 # 45s loopable
total_samples = int(sample_rate * duration_sec)
t = np.linspace(0, duration_sec, total_samples, endpoint=False)

# Tempo: 110 BPM -> beat length = 60 / 110 = 0.545 sec
beat_len = 60.0 / 110.0

# Base chord progression: D minor (D - F - A), Bb major, C major, F major
# Frequencies: D3=146.83, F3=174.61, A3=220, Bb2=116.54, C3=130.81
audio = np.zeros(total_samples)

# 1. Warm String Pad
chords = [
    (146.83, 174.61, 220.0), # Dm
    (116.54, 146.83, 174.61), # Bb
    (130.81, 164.81, 196.0), # C
    (174.61, 220.0, 261.63), # F
]
chord_dur = beat_len * 8 # 8 beats per chord

for i, (f1, f2, f3) in enumerate(chords * (int(duration_sec / (chord_dur * 4)) + 1)):
    start_t = i * chord_dur
    end_t = (i + 1) * chord_dur
    mask = (t >= start_t) & (t < end_t)
    if not np.any(mask):
        break
    tm = t[mask] - start_t
    # envelope
    env = np.sin(np.pi * (tm / chord_dur)) ** 0.5
    wave_chord = (
        0.5 * np.sin(2 * np.pi * f1 * tm) +
        0.3 * np.sin(2 * np.pi * f1 * 2 * tm) +
        0.4 * np.sin(2 * np.pi * f2 * tm) +
        0.4 * np.sin(2 * np.pi * f3 * tm) +
        0.2 * np.sin(2 * np.pi * (f3 * 2) * tm)
    )
    audio[mask] += wave_chord * env * 0.25

# 2. Rhythmic News Pulse (Pulse bass & electronic tick)
for b in range(int(duration_sec / beat_len)):
    start_b = b * beat_len
    mask_b = (t >= start_b) & (t < start_b + beat_len)
    if not np.any(mask_b):
        break
    tb = t[mask_b] - start_b
    # Kick/thud on beats
    decay = np.exp(-tb * 12)
    thud = np.sin(2 * np.pi * (80 - 40 * (tb / beat_len)) * tb) * decay * 0.3
    # Hi-hat tick
    noise_tick = np.random.normal(0, 0.05, len(tb)) * np.exp(-tb * 35)
    audio[mask_b] += thud + noise_tick

# 3. Melodic Broadcast Chimes / Marimba
melody_notes = [440, 523.25, 587.33, 659.25, 587.33, 523.25]
for m_idx in range(int(duration_sec / (beat_len * 2))):
    note_f = melody_notes[m_idx % len(melody_notes)]
    start_m = m_idx * beat_len * 2
    mask_m = (t >= start_m) & (t < start_m + beat_len * 1.5)
    if np.any(mask_m):
        tm = t[mask_m] - start_m
        env = np.exp(-tm * 4)
        audio[mask_m] += (np.sin(2 * np.pi * note_f * tm) + 0.5 * np.sin(2 * np.pi * note_f * 2 * tm)) * env * 0.12

# Master fade in and fade out
fade_in_samples = int(sample_rate * 1.5)
audio[:fade_in_samples] *= np.linspace(0, 1, fade_in_samples)
fade_out_samples = int(sample_rate * 2.0)
audio[-fade_out_samples:] *= np.linspace(1, 0, fade_out_samples)

# Normalize to -3dB
max_val = np.max(np.abs(audio))
if max_val > 0:
    audio = audio / max_val * 0.75

audio_int16 = (audio * 32767).astype(np.int16)

# Write temp wav
temp_wav = "assets/temp_bgm.wav"
with wave.open(temp_wav, "wb") as wf:
    wf.setnchannels(1)
    wf.setsampwidth(2)
    wf.setframerate(sample_rate)
    wf.writeframes(audio_int16.tobytes())

# Convert to mp3 using ffmpeg
bgm_mp3 = "assets/bgm_news.mp3"
subprocess.run([
    ffmpeg_exe, "-y", "-i", temp_wav,
    "-codec:a", "libmp3lame", "-qscale:a", "2",
    bgm_mp3
], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
if os.path.exists(temp_wav):
    os.remove(temp_wav)

print("BGM News MP3 created at assets/bgm_news.mp3.")

print("Generating sample 10s video from sample photo: assets/sample_video.mp4...")
# Create a 10-second MP4 test video from sample photo
subprocess.run([
    ffmpeg_exe, "-y", "-loop", "1", "-i", "assets/sample_photo_1.jpg",
    "-c:v", "libx264", "-t", "10", "-pix_fmt", "yuv420p", "-vf", "scale=1280:720",
    "assets/sample_video.mp4"
], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
print("Assets preparation complete!")
