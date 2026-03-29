import asyncio
import json
import os
import subprocess
import sys
from playwright.async_api import async_playwright

async def render():
    ASSETS_DIR = "assets"
    OUTPUT_DIR = "output"
    FRAMES_DIR = "temp_frames"
    
    for d in [OUTPUT_DIR, FRAMES_DIR]:
        if not os.path.exists(d): os.makedirs(d)

    json_path = os.path.join(ASSETS_DIR, "data.json")
    audio_path = os.path.join(ASSETS_DIR, "voice.mp3")
    output_name = os.path.join(OUTPUT_DIR, "final_reel.mp4")

    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    async with async_playwright() as p:
        # تشغيل المتصفح بأعلى إعدادات جرافيكس ممكنة في السحاب
        browser = await p.chromium.launch(headless=True, args=[
            '--disable-gpu', '--force-device-scale-factor=3', 
            '--hide-scrollbars', '--mute-audio'
        ])
        
        # viewport كبير عشان التفاصيل تبان
        context = await browser.new_context(viewport={'width': 1080, 'height': 1920})
        page = await context.new_page()

        await page.goto(f"file://{os.getcwd()}/engine.html")
        await page.evaluate(f"window.REEL_DATA = {json.dumps(data)};")
        await page.evaluate("startReel();")

        print("📸 Capturing High-Res Frames (Please wait)...")
        frame_count = 0
        
        # حلقة التقاط الصور فريم بـ فريم لضمان 0% بكسلة
        while True:
            # لقطة شاشة لكل لحظة أنيميشن بجودة PNG أصلية
            await page.screenshot(path=f"{FRAMES_DIR}/frame_{frame_count:05d}.png", type='png')
            frame_count += 1
            
            # التأكد لو خلصنا
            is_done = await page.evaluate("document.getElementById('progress-bar').getAttribute('data-status') === 'finished'")
            if is_done: break
            # موازنة سرعة الأنيميشن مع الالتقاط (مهم جداً للنعومة)
            await asyncio.sleep(0.016) # لمحاكاة 60fps

        await browser.close()

        print(f"🎬 Compiling {frame_count} frames into Ultra-HD Video...")
        
        # FFmpeg بياخد الصور الـ PNG ويحولها لفيديو عالي الجودة جداً
        ffmpeg_cmd = [
            'ffmpeg', '-y', '-framerate', '60', 
            '-i', f'{FRAMES_DIR}/frame_%05d.png',
            '-i', audio_path if os.path.exists(audio_path) else '', # صوت لو موجود
            '-c:v', 'libx264', '-preset', 'veryslow', '-crf', '12', # CRF 12 يعني جودة خرافية
            '-pix_fmt', 'yuv420p', '-shortest', output_name
        ]
        # لو مفيش صوت هنشيل الـ input التاني
        if not os.path.exists(audio_path): ffmpeg_cmd.pop(4); ffmpeg_cmd.pop(4)

        subprocess.run(ffmpeg_cmd)
        print(f"✅ DONE! Video saved as {output_name}")

if __name__ == "__main__":
    asyncio.run(render())
        context = await browser.new_context(
            viewport={'width': 400, 'height': 711},
            device_scale_factor=3, 
            record_video_dir="temp_raw/" 
        )
        page = await context.new_page()

        print("🌐 Loading Engine...")
        await page.goto(f"file://{os.getcwd()}/engine.html")

        print("💉 Injecting Data...")
        await page.evaluate(f"window.REEL_DATA = {json.dumps(data)};")
        await page.evaluate("startReel();")

        print("⏳ High-Quality Rendering in progress...")
        try:
            await page.wait_for_function(
                "document.getElementById('progress-bar').getAttribute('data-status') === 'finished'",
                timeout=240000 
            )
        except Exception as e:
            print(f"⚠️ Render Error: {e}")
            sys.exit(1)
        
        await context.close()
        
        raw_video_file = os.path.join("temp_raw", os.listdir("temp_raw")[0])
        
        print("🎬 Final Mastering with FFmpeg (Ultra Quality)...")
        
        # 🛠️ السر هنا: preset slow و crf 17 بيضمنوا إن مفيش بكسلة
        ffmpeg_base_args = [
            'ffmpeg', '-y', '-i', raw_video_file,
            '-c:v', 'libx264', 
            '-preset', 'veryslow', # أبطأ بس جودة خرافية
            '-crf', '17',          # جودة احترافية (visually lossless)
            '-pix_fmt', 'yuv420p'
        ]

        if os.path.exists(audio_path):
            inputs = ['-i', audio_path]
            if os.path.exists(sfx_path):
                inputs += ['-stream_loop', '-1', '-i', sfx_path]
                filter_complex = "[2:a]volume=0.15[sfx]; [1:a][sfx]amix=inputs=2:duration=first[a]"
            else:
                filter_complex = "[1:a]volume=1.0[a]"
            
            cmd = [ffmpeg_base_args[0], '-y', '-i', raw_video_file] + inputs + \
                  ['-filter_complex', filter_complex, '-map', '0:v', '-map', '[a]'] + \
                  ffmpeg_base_args[4:] + [output_name]
        else:
            cmd = ffmpeg_base_args + [output_name]

        subprocess.run(cmd)
        await browser.close()
        print(f"🎊 4K-Style Video Ready: {output_name}")

if __name__ == "__main__":
    asyncio.run(render())
        
