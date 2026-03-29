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
    output_name = os.path.join(OUTPUT_DIR, "final_video.mp4")

    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        # رفع الـ scale لـ 3 عشان الجودة 1080p حقيقية
        context = await browser.new_context(viewport={'width': 400, 'height': 711}, device_scale_factor=3)
        page = await context.new_page()

        await page.goto(f"file://{os.getcwd()}/engine.html")
        # حقن الداتا وتشغيل المحرك
        await page.evaluate(f"window.REEL_DATA = {json.dumps(data)};")
        await page.evaluate("startReel();")

        print("📸 Capturing Frames...")
        frame = 0
        while True:
            await page.screenshot(path=f"{FRAMES_DIR}/f_{frame:05d}.png")
            frame += 1
            # تشيك لو خلص
            done = await page.evaluate("document.getElementById('progress-bar').getAttribute('data-done') === 'true'")
            if done: break
            await asyncio.sleep(0.01)

        await browser.close()

        # تجميع الفيديو بـ FFmpeg
        cmd = [
            'ffmpeg', '-y', '-framerate', '30', '-i', f'{FRAMES_DIR}/f_%05d.png',
            '-i', audio_path if os.path.exists(audio_path) else '',
            '-c:v', 'libx264', '-crf', '18', '-pix_fmt', 'yuv420p', '-shortest', output_name
        ]
        if not os.path.exists(audio_path): 
            cmd.pop(4); cmd.pop(4)
        
        subprocess.run(cmd)
        print("✅ Done!")

if __name__ == "__main__":
    asyncio.run(render())
        
