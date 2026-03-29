import asyncio
import json
import os
import subprocess
import sys
from playwright.async_api import async_playwright

async def render():
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    ASSETS_DIR = os.path.join(BASE_DIR, "assets")
    OUTPUT_DIR = os.path.join(BASE_DIR, "output")
    # فولدر مؤقت لتسجيل الفيديو
    VIDEO_TEMP_DIR = os.path.join(BASE_DIR, "temp_video")
    
    for d in [OUTPUT_DIR, VIDEO_TEMP_DIR]:
        if not os.path.exists(d): os.makedirs(d)

    json_path = os.path.join(ASSETS_DIR, "data.json")
    audio_path = os.path.join(ASSETS_DIR, "voice.mp3")
    engine_path = os.path.join(BASE_DIR, "engine.html")
    output_name = os.path.join(OUTPUT_DIR, "final_video.mp4")

    print(f"🚀 Starting Render Process...")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        # 🌟 تفعيل تسجيل الفيديو هنا بشكل صريح
        context = await browser.new_context(
            viewport={'width': 400, 'height': 711},
            device_scale_factor=2,
            record_video_dir=VIDEO_TEMP_DIR,
            record_video_size={'width': 800, 'height': 1422} # جودة مضاعفة
        )
        page = await context.new_page()

        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        await page.goto(f"file://{engine_path}")
        await page.evaluate(f"window.REEL_DATA = {json.dumps(data)};")
        await page.evaluate("startReel();")

        print("⏳ Waiting for Animation...")
        try:
            # الانتظار حتى ظهور علامة التمام
            await page.wait_for_function("document.getElementById('progress-bar').getAttribute('data-done') === 'true'", timeout=120000)
            await asyncio.sleep(2) # أمان إضافي
        except Exception as e:
            print(f"❌ Timeout: {e}")
            sys.exit(1)

        # 🌟 أهم خطوة: قفل الـ Context عشان الفيديو يتسيف
        await context.close()
        
        # الحصول على مسار الفيديو اللي اتسجل
        raw_video_path = await page.video.path()
        await browser.close()

        if raw_video_path and os.path.exists(raw_video_path):
            print(f"🎬 Raw video recorded: {raw_video_path}")
            
            # دمج الصوت (FFmpeg)
            if os.path.exists(audio_path):
                print("🔊 Mixing with Audio...")
                subprocess.run([
                    'ffmpeg', '-y', '-i', raw_video_path, '-i', audio_path,
                    '-c:v', 'libx264', '-crf', '18', '-pix_fmt', 'yuv420p',
                    '-shortest', output_name
                ])
            else:
                print("⚠️ No audio found, moving raw video to output.")
                import shutil
                shutil.move(raw_video_path, output_name)
            
            print(f"✅ SUCCESS: {output_name}")
        else:
            print("❌ ERROR: Video file was not created!")
            sys.exit(1)

if __name__ == "__main__":
    asyncio.run(render())
        
