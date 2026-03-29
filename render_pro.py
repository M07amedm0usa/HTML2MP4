import asyncio
import json
import os
import subprocess
import sys
from playwright.async_api import async_playwright

async def render():
    ASSETS_DIR = "assets"
    OUTPUT_DIR = "output"
    
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

    # المسارات (تأكد أن n8n يرفع الملفات بنفس الأسماء)
    json_path = os.path.join(ASSETS_DIR, "data.json")
    audio_path = os.path.join(ASSETS_DIR, "voice.mp3")
    sfx_path = os.path.join(ASSETS_DIR, "marker_sfx.mp3")
    output_name = os.path.join(OUTPUT_DIR, "final_reel.mp4")

    if not os.path.exists(json_path):
        print(f"❌ Error: {json_path} not found!")
        return

    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        # إعدادات الـ 1080p (540x960 * 2)
        context = await browser.new_context(
            viewport={'width': 400, 'height': 711}, # مقاس الحاوية
            device_scale_factor=2.5, # لزيادة حدة الفيديو
            record_video_dir="temp_raw/" 
        )
        page = await context.new_page()

        # فتح المحرك
        await page.goto(f"file://{os.getcwd()}/engine.html")

        # حقن الداتا وتشغيل المحرك
        await page.evaluate(f"window.REEL_DATA = {json.dumps(data)};")
        await page.evaluate("startReel();")

        # انتظار علامة النهاية من الـ JS
        await page.wait_for_selector("[data-status='finished']", timeout=120000)
        
        await context.close()
        raw_video_file = os.path.join("temp_raw", os.listdir("temp_raw")[0])
        
        # دمج الصوت (FFmpeg)
        inputs = ['-i', raw_video_file, '-i', audio_path]
        filter_complex = "[1:a]volume=1.0[a]" # Default لو مفيش SFX
        
        if os.path.exists(sfx_path):
            inputs += ['-stream_loop', '-1', '-i', sfx_path]
            filter_complex = "[2:a]volume=0.15[sfx]; [1:a][sfx]amix=inputs=2:duration=first[a]"

        cmd = ['ffmpeg', '-y'] + inputs + [
            '-filter_complex', filter_complex,
            '-map', '0:v', '-map', '[a]',
            '-c:v', libx264, '-crf', '18', '-pix_fmt', 'yuv420p', 
            output_name
        ]
        
        subprocess.run(cmd)
        await browser.close()
        print(f"🚀 Done! Video saved in {output_name}")

if __name__ == "__main__":
    asyncio.run(render())
