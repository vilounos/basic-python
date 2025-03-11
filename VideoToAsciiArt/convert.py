#!/usr/bin/env python3
import argparse
import logging
import os
import subprocess
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from concurrent.futures import ProcessPoolExecutor

# Global settings
OUT_WIDTH, OUT_HEIGHT = 1920, 1080
COLS, ROWS = 512, 288
CELL_WIDTH = OUT_WIDTH // COLS
CELL_HEIGHT = OUT_HEIGHT // ROWS
FONT_PATH = "font.ttf"

def process_frame(frame):
    import cv2
    import numpy as np
    from PIL import Image, ImageDraw, ImageFont

    # Grayscale
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    # Lower res
    small_gray = cv2.resize(gray, (COLS, ROWS), interpolation=cv2.INTER_AREA)
    # Black x White
    _, binary = cv2.threshold(small_gray, 127, 255, cv2.THRESH_BINARY)
    
    # White frame
    ascii_img = Image.new("RGB", (OUT_WIDTH, OUT_HEIGHT), "white")
    draw = ImageDraw.Draw(ascii_img)
    # Load font
    try:
        font = ImageFont.truetype(FONT_PATH, CELL_HEIGHT)
    except IOError:
        font = ImageFont.load_default()
    
    # Create grid
    for r in range(ROWS):
        for c in range(COLS):
            char = "|" if binary[r, c] == 0 else "-"
            x = c * CELL_WIDTH
            y = r * CELL_HEIGHT
            draw.text((x, y), char, font=font, fill="black")
    
    # PIL pic ready
    ascii_frame = np.array(ascii_img)
    ascii_frame = cv2.cvtColor(ascii_frame, cv2.COLOR_RGB2BGR)
    return ascii_frame

def extract_and_merge_audio(input_video, start_time, end_time, video_only, final_output):
    temp_audio = "temp_audio.aac"
    logging.info("Extracting audio from the original file...")
    # Extract audio
    subprocess.run([
        "ffmpeg", "-y",
        "-i", input_video,
        "-ss", str(start_time),
        "-to", str(end_time),
        "-vn",
        "-acodec", "copy",
        temp_audio
    ], check=True)
    
    logging.info("Merging video and audio into final output...")
    # Re-encode video using libx264 for better compression
    subprocess.run([
        "ffmpeg", "-y",
        "-i", video_only,
        "-i", temp_audio,
        "-c:v", "libx264",
        "-preset", "slow",
        "-crf", "23",
        "-c:a", "aac",
        final_output
    ], check=True)
    
    # Delete temp audio file
    os.remove(temp_audio)
    logging.info("Audio + Video merged successfully.")

def main():
    parser = argparse.ArgumentParser(
        description="Video do ASCII art..."
    )
    parser.add_argument("--input", type=str, default="input.mp4", help="Input file")
    parser.add_argument("--output", type=str, default="output.mp4", help="Output file")
    parser.add_argument("--start", type=float, default=0, help="Start time (seconds)")
    parser.add_argument("--end", type=float, default=None, help="End time (seconds)")
    parser.add_argument("--workers", type=int, default=os.cpu_count(), help="Paraller workers")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
    logging.info("Starting...")

    # Verify video
    cap = cv2.VideoCapture(args.input)
    if not cap.isOpened():
        logging.error("Cannot open video file %s", args.input)
        return

    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frame_count = cap.get(cv2.CAP_PROP_FRAME_COUNT)
    video_duration = total_frame_count / fps if fps > 0 else 0
    logging.info("Video: %.2f FPS, Length: %.2f seconds", fps, video_duration)
    
    end_time = args.end if args.end is not None else video_duration
    if args.start < 0 or end_time > video_duration or args.start >= end_time:
        logging.error("Incorrect times: start=%.2f, end=%.2f", args.start, end_time)
        return

    # Set starting time
    cap.set(cv2.CAP_PROP_POS_MSEC, args.start * 1000)
    logging.info("Video starts: %.2f do %.2f seconds...", args.start, end_time)

    frames = []
    frame_indices = []
    while True:
        pos_sec = cap.get(cv2.CAP_PROP_POS_MSEC) / 1000.0
        if pos_sec > end_time:
            break
        ret, frame = cap.read()
        if not ret:
            break
        frames.append(frame)
    cap.release()
    total_frames = len(frames)
    logging.info("Loaded %d frames.", total_frames) 
    
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    temp_video = "temp_video.mp4"
    video_writer = cv2.VideoWriter(temp_video, fourcc, fps, (OUT_WIDTH, OUT_HEIGHT))

    # Paraller calculations
    logging.info("Parraler computation with %d workers...", args.workers)
    processed_count = 0
    with ProcessPoolExecutor(max_workers=args.workers) as executor:
        for processed_frame in executor.map(process_frame, frames):
            processed_count += 1
            if processed_count % 10 == 0 or processed_count == total_frames:
                logging.info(" %d/%d frames ready", processed_count, total_frames)
            video_writer.write(processed_frame)
    video_writer.release()
    logging.info("Video without audio saved as %s", temp_video)

    # Merge video and audio
    final_output = args.output
    try:
        extract_and_merge_audio(args.input, args.start, end_time, temp_video, final_output)
    except subprocess.CalledProcessError as e:
        logging.error("FFMPEG ERROR: %s", e)
        return

    # Delete temp file
    os.remove(temp_video)
    logging.info("DONE! Saved as %s", final_output)

if __name__ == '__main__':
    main()

