"""
AutoSecOps GreenSentinel - Demo Video Synthesis Pipeline
Synthesizes Christopher Neural voiceover via edge-tts and stitches screenshots into an MP4 demo video.
"""

import asyncio
import os
import subprocess
import sys
from pathlib import Path
import edge_tts

REPO_ROOT = Path(__file__).resolve().parent.parent
ASSETS_DIR = REPO_ROOT / "assets"
SCREENSHOT_DIR = ASSETS_DIR / "screenshots"
AUDIO_DIR = ASSETS_DIR / "audio"
AUDIO_DIR.mkdir(parents=True, exist_ok=True)

OUTPUT_VIDEO = ASSETS_DIR / "greensentinel_demo.mp4"

CHAPTERS = [
    {
        "id": "01",
        "image": SCREENSHOT_DIR / "01_hero_dashboard.png",
        "audio": AUDIO_DIR / "01_hero.mp3",
        "text": (
            "Welcome to AutoSecOps GreenSentinel, our submission for the GitLab Transcend Hackathon. "
            "Built upon Grandma Theory, our executive interface presents zero cognitive load. "
            "Behind this crystal clear summary lies a fully autonomous DevSecOps orchestrator, "
            "protected by strict enterprise guardrails where blind commits are forbidden and all patches require policy-gated Merge Requests."
        )
    },
    {
        "id": "02",
        "image": SCREENSHOT_DIR / "02_auto_healed_diff.png",
        "audio": AUDIO_DIR / "02_diff.mp3",
        "text": (
            "When pipeline anomalies or carbon budget breaches occur in the verify stage, "
            "our GitLab Duo Agent Platform integration immediately kicks in via FastMCP. "
            "The agent autonomously diagnoses the runner trace, validates our security gate, "
            "and generates a surgical unified git diff to rebalance the carbon footprint in under one point five seconds."
        )
    },
    {
        "id": "03",
        "image": SCREENSHOT_DIR / "03_carbon_router.png",
        "audio": AUDIO_DIR / "03_router.mp3",
        "text": (
            "Environmentally, GreenSentinel implements a smart low-carbon grid router. "
            "It queries real-time regional carbon intensity, dynamically steering Google Cloud Run container deployments "
            "away from high-emission grids to Europe West Nine in Paris, achieving up to ninety-six percent clean energy and ninety-one percent carbon reduction."
        )
    },
    {
        "id": "04",
        "image": SCREENSHOT_DIR / "04_devsecops_stages.png",
        "audio": AUDIO_DIR / "04_stages.mp3",
        "text": (
            "Targeting the Most Stages Covered prize, GreenSentinel actively governs all nine phases of the DevSecOps lifecycle: "
            "Plan, Create, Verify, Package, Secure, Release, Configure, Monitor, and Govern. "
            "Each stage produces verifiable artifacts, including CycloneDX SBOMs and Google Cloud Run deployment receipts."
        )
    },
    {
        "id": "05",
        "image": SCREENSHOT_DIR / "05_sci_telemetry.png",
        "audio": AUDIO_DIR / "05_telemetry.mp3",
        "text": (
            "For mathematical credibility, our carbon calculations strictly adhere to the Green Software Foundation's Software Carbon Intensity standard. "
            "We integrate live hardware telemetry using psutil, sampling actual CPU load, memory utilization, and hardware embodied carbon to produce an undeniable carbon score."
        )
    },
    {
        "id": "06",
        "image": SCREENSHOT_DIR / "06_circuit_breaker.png",
        "audio": AUDIO_DIR / "06_breaker.mp3",
        "text": (
            "Finally, to guarantee enterprise safety and prevent infinite remediation loops, "
            "we engineered a hard circuit breaker. If two consecutive autonomous fixes fail, "
            "the system instantly halts, rolls back the repository, and raises a critical priority-one incident issue. "
            "AutoSecOps GreenSentinel: safe, sustainable, and truly hands-off."
        )
    }
]


async def generate_speech():
    print("[*] Generating neural voiceover via edge-tts (en-US-ChristopherNeural)...")
    for ch in CHAPTERS:
        if not ch["audio"].exists():
            print(f"    -> Generating audio for Chapter {ch['id']}...")
            communicate = edge_tts.Communicate(ch["text"], voice="en-US-ChristopherNeural")
            await communicate.save(str(ch["audio"]))
    print("[OK] All voiceover chapters synthesized.")


def get_audio_duration(audio_path: Path) -> float:
    cmd = ["ffmpeg", "-i", str(audio_path), "-f", "null", "-"]
    res = subprocess.run(cmd, capture_output=True, text=True)
    for line in res.stderr.splitlines():
        if "Duration:" in line:
            parts = line.split("Duration:")[1].split(",")[0].strip()
            h, m, s = parts.split(":")
            return float(h) * 3600 + float(m) * 60 + float(s)
    return 20.0


def render_chapter_clips():
    print("[*] Rendering synchronized 1080p clips for each chapter...")
    clip_files = []
    
    for ch in CHAPTERS:
        clip_path = ASSETS_DIR / f"clip_{ch['id']}.mp4"
        duration = get_audio_duration(ch["audio"]) + 0.5  # pad 0.5s for seamless transition
        print(f"    -> Rendering {clip_path.name} (Duration: {duration:.2f}s)...")
        
        # Exact length 30fps clip with x264 ultrafast
        ffmpeg_cmd = [
            "ffmpeg", "-y",
            "-loop", "1",
            "-i", str(ch["image"]),
            "-i", str(ch["audio"]),
            "-c:v", "libx264", "-preset", "ultrafast",
            "-vf", "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2:color=0x020617",
            "-c:a", "aac", "-b:a", "192k",
            "-pix_fmt", "yuv420p",
            "-t", str(duration),
            "-r", "30",
            str(clip_path)
        ]
        subprocess.run(ffmpeg_cmd, capture_output=True, check=True)
        clip_files.append(clip_path)
        
    return clip_files


def stitch_final_video(clip_files):
    print("[*] Stitching chapters into final MP4 demo video...")
    concat_list_file = ASSETS_DIR / "concat_list.txt"
    with open(concat_list_file, "w", encoding="utf-8") as f:
        for clip in clip_files:
            f.write(f"file '{clip.resolve().as_posix()}'\n")

    ffmpeg_concat_cmd = [
        "ffmpeg", "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", str(concat_list_file),
        "-c", "copy",
        str(OUTPUT_VIDEO)
    ]
    subprocess.run(ffmpeg_concat_cmd, capture_output=True, check=True)
    print(f"[OK] Master demo video generated successfully at: {OUTPUT_VIDEO}")
    
    # Cleanup temporary clips
    for clip in clip_files:
        if clip.exists():
            clip.unlink()
    if concat_list_file.exists():
        concat_list_file.unlink()
    test_file = ASSETS_DIR / "test.mp4"
    if test_file.exists():
        test_file.unlink()
    clip_fast = ASSETS_DIR / "clip_fast_01.mp4"
    if clip_fast.exists():
        clip_fast.unlink()


def main():
    asyncio.run(generate_speech())
    clip_files = render_chapter_clips()
    stitch_final_video(clip_files)


if __name__ == "__main__":
    main()
