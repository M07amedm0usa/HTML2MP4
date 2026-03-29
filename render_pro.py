import asyncio
import json
import os
import subprocess
import sys
from playwright.async_api import async_playwright

async def render():
    # التأكد من المسارات المطلقة
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    ASSETS_DIR = os.path.join(BASE_DIR, "assets")
    OUTPUT_DIR = os.path.join(BASE_DIR, "output")
    
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

    json_path = os.path.join(ASSETS_DIR, "data.json")
    audio_path = os.path.join(ASSETS_DIR, "voice.mp3")
    engine_path = os.path.join(BASE_DIR, "engine.html")
    output_name = os.path.join(OUTPUT_DIR, "final_video.mp4")

    print(f"🚀 Starting Render Process...")
    print(f"📁 Engine Path: {engine_path}")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={'width': 400, 'height': 711}, device_scale_factor=2)
        page = await context.new_page()

        # تحميل البيانات قبل فتح الصفحة
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        await page.goto(f"file://{engine_path}")
        
        # حقن البيانات وتشغيل المحرك
        await page.evaluate(f"window.REEL_DATA = {json.dumps(data)};")
        await page.evaluate("startReel();")

        print("⏳ Waiting for Animation...")
        # الانتظار لحد ما يخلص
        try:
            await page.wait_for_function("document.getElementById('progress-bar').getAttribute('data-done') === 'true'", timeout=60000)
            # هناخد سكرين شوت عشان نتطمن إن الشغل خلص
            await page.screenshot(path="debug_finished.png")
        except Exception as e:
            print(f"❌ Error during wait: {e}")
            await page.screenshot(path="debug_error.png")
            sys.exit(1)

        # تسجيل الفيديو من Playwright مباشرة (أسرع وأضمن للـ Actions)
        # ملاحظة: سنستخدم التسجيل الداخلي للـ Context
        video_path = await page.video.path() if page.video else None
        await context.close()
        await browser.close()

        # دمج الصوت بـ FFmpeg
        print("🔊 Mixing Video...")
        if os.path.exists(audio_path):
            subprocess.run(['ffmpeg', '-y', '-i', video_path, '-i', audio_path, '-c:v', 'copy', '-c:a', 'aac', '-shortest', output_name])
        else:
            # لو مفيش صوت انقل الفيديو المسجل للمخرجات
            os.rename(video_path, output_name)
        
        print("✅ Success!")

if __name__ == "__main__":
    asyncio.run(render())
        
