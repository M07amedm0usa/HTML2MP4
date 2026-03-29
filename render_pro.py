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

    json_path = os.path.join(ASSETS_DIR, "data.json")
    audio_path = os.path.join(ASSETS_DIR, "voice.mp3")
    sfx_path = os.path.join(ASSETS_DIR, "marker_sfx.mp3")
    output_name = os.path.join(OUTPUT_DIR, "final_reel.mp4")

    if not os.path.exists(json_path):
        print(f"❌ Error: {json_path} not found!")
        sys.exit(1)

    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    async with async_playwright() as p:
        print("🚀 Launching High-Res Browser...")
        # إضافة args لضمان أفضل ريندر للجرافيكس
        browser = await p.chromium.launch(headless=True, args=[
            '--font-render-hinting=none',
            '--disable-skia-runtime-opts',
            '--disable-font-subpixel-positioning'
        ])
        
        # 🌟 رفع الجودة لـ 3x (هتطلع فيديو أبعاده 1200x2133 تقريباً)
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
        
