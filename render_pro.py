import asyncio
import json
import os
import subprocess
import sys
from playwright.async_api import async_playwright

async def render():
    ASSETS_DIR = "assets"
    OUTPUT_DIR = "output"
    
    # التأكد من وجود المجلدات المطلوبة
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

    # مسارات الملفات
    json_path = os.path.join(ASSETS_DIR, "data.json")
    audio_path = os.path.join(ASSETS_DIR, "voice.mp3")
    sfx_path = os.path.join(ASSETS_DIR, "marker_sfx.mp3")
    output_name = os.path.join(OUTPUT_DIR, "final_reel.mp4")

    # التحقق من وجود ملف البيانات (أساسي للريندر)
    if not os.path.exists(json_path):
        print(f"❌ Error: {json_path} not found! Check your assets folder.")
        sys.exit(1)

    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    async with async_playwright() as p:
        print("🌐 Starting Browser...")
        browser = await p.chromium.launch(headless=True)
        # إعدادات الـ Reels (جودة عالية 2.5x Scale)
        context = await browser.new_context(
            viewport={'width': 400, 'height': 711},
            device_scale_factor=2.5,
            record_video_dir="temp_raw/" 
        )
        page = await context.new_page()

        # فتح المحرك
        print("🚀 Loading Engine...")
        await page.goto(f"file://{os.getcwd()}/engine.html")

        # حقن البيانات وتشغيل المحرك
        print("💉 Injecting Data and Starting Animation...")
        await page.evaluate(f"window.REEL_DATA = {json.dumps(data)};")
        await page.evaluate("startReel();")

        # الانتظار الذكي (مراقبة الـ Attribute اللي ضفناه في الـ JS)
        print("⏳ Rendering... Please wait.")
        try:
            await page.wait_for_function(
                "document.getElementById('progress-bar').getAttribute('data-status') === 'finished'",
                timeout=180000 # 3 دقائق
            )
            print("✅ Animation Finished!")
        except Exception as e:
            print(f"⚠️ Timeout or Error: {e}")
            await page.screenshot(path="error_state.png")
            sys.exit(1)
        
        await context.close()
        
        # تحديد ملف الفيديو الخام اللي Playwright سجله
        raw_videos = os.listdir("temp_raw")
        if not raw_videos:
            print("❌ Error: No raw video recorded by Playwright.")
            sys.exit(1)
        
        raw_video_file = os.path.join("temp_raw", raw_videos[0])
        
        # 🎬 معالجة الصوت والدمج النهائي (النسخة المرنة)
        print("🔊 Processing Final Video with FFmpeg...")
        
        if os.path.exists(audio_path):
            print("🎵 Voiceover found, mixing...")
            inputs = ['-i', raw_video_file, '-i', audio_path]
            
            if os.path.exists(sfx_path):
                print("🖋️ Marker SFX found, mixing with voiceover...")
                inputs += ['-stream_loop', '-1', '-i', sfx_path]
                # دمج صوت التعليق مع صوت الماركر (الماركر صوته أهدى 15%)
                filter_complex = "[2:a]volume=0.15[sfx]; [1:a][sfx]amix=inputs=2:duration=first[a]"
            else:
                filter_complex = "[1:a]volume=1.0[a]"

            cmd = ['ffmpeg', '-y'] + inputs + [
                '-filter_complex', filter_complex,
                '-map', '0:v', '-map', '[a]',
                '-c:v', 'libx264', '-crf', '18', '-pix_fmt', 'yuv420p', 
                output_name
            ]
        else:
            print("⚠️ No audio found in assets. Rendering silent video.")
            cmd = [
                'ffmpeg', '-y', '-i', raw_video_file,
                '-c:v', 'libx264', '-crf', '18', '-pix_fmt', 'yuv420p', 
                output_name
            ]

        subprocess.run(cmd)
        await browser.close()
        print(f"🎊 SUCCESS! Video is ready at: {output_name}")

if __name__ == "__main__":
    asyncio.run(render())
        
