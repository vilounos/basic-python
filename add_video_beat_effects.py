import argparse
import random
import numpy as np
import librosa
import cv2
import os
from moviepy import *

# --- EFFECTS ---
def effect_swing(frame, t, intensity=10, freq=2):
    """Swing: Horizontal swings"""
    shift = int(intensity * np.sin(freq * t * 2 * np.pi))
    M = np.float32([[1, 0, shift], [0, 1, 0]])
    return cv2.warpAffine(frame, M, (frame.shape[1], frame.shape[0]))

def effect_wave(frame, t, intensity=5, freq=10):
    """Wave Distortion: Video waving"""
    rows, cols, _ = frame.shape
    map_y, map_x = np.indices((rows, cols), dtype=np.float32)
    map_y += intensity * np.sin(2 * np.pi * map_x / freq + t)
    return cv2.remap(frame, map_x, map_y, interpolation=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)

def effect_shake(frame, t, max_shift=5):
    """Shake: Random shakes"""
    shift_x = np.random.randint(-max_shift, max_shift)
    shift_y = np.random.randint(-max_shift, max_shift)
    M = np.float32([[1, 0, shift_x], [0, 1, shift_y]])
    return cv2.warpAffine(frame, M, (frame.shape[1], frame.shape[0]))

def effect_invert(frame, t):
    """Invert Colors: Does what it says"""
    return cv2.bitwise_not(frame)

def effect_pixelate(frame, t, pixel_size=10):
    """Pixelate: The video is blury and pixelate"""
    height, width = frame.shape[:2]
    temp = cv2.resize(frame, (max(1, width // pixel_size), max(1, height // pixel_size)), interpolation=cv2.INTER_LINEAR)
    return cv2.resize(temp, (width, height), interpolation=cv2.INTER_NEAREST)

def effect_timewarp(frame, t, factor=0.5):
    """Time Warp: Does what it says"""
    shifted = np.roll(frame, int(5 * np.sin(t * 10)), axis=0)
    return cv2.addWeighted(frame, factor, shifted, 1 - factor, 0)

def effect_glitch(frame, t, intensity=20, segments=10):
    """Glitch: It glitches"""
    h, w, _ = frame.shape
    output = frame.copy()
    for _ in range(segments):
        start_row = np.random.randint(0, h)
        seg_height = np.random.randint(5, max(5, h // segments))
        shift = np.random.randint(-intensity, intensity)
        output[start_row:start_row+seg_height] = np.roll(output[start_row:start_row+seg_height], shift, axis=1)
    return output

def effect_zoom(frame, t, intensity=0.2, freq=1):
    """Zoom In/Out: fast frame zoom"""
    zoom_factor = 1 + intensity * np.sin(2 * np.pi * freq * t)
    h, w = frame.shape[:2]
    resized = cv2.resize(frame, None, fx=zoom_factor, fy=zoom_factor, interpolation=cv2.INTER_LINEAR)
    new_h, new_w = resized.shape[:2]
    if zoom_factor >= 1:
        start_y = (new_h - h) // 2
        start_x = (new_w - w) // 2
        cropped = resized[start_y:start_y+h, start_x:start_x+w]
    else:
        pad_y = (h - new_h) // 2
        pad_x = (w - new_w) // 2
        cropped = cv2.copyMakeBorder(resized, pad_y, h - new_h - pad_y, pad_x, w - new_w - pad_x, cv2.BORDER_REFLECT)
    return cropped

def effect_flash(frame, t, alpha=0.7):
    """Flash: White flash"""
    white = np.full(frame.shape, 255, dtype=np.uint8)
    return cv2.addWeighted(frame, 1 - alpha, white, alpha, 0)

def effect_rgb_shift(frame, t, shift=5):
    """RGB Shift: Changes RGB values"""
    B, G, R = cv2.split(frame)
    B = np.roll(B, shift, axis=0)
    G = np.roll(G, -shift, axis=1)
    R = np.roll(R, shift // 2, axis=0)
    return cv2.merge((B, G, R))

# Effects dictionary
EFFECTS = {
    "swing": effect_swing,
    "wave": effect_wave,
    "shake": effect_shake,
    "invert": effect_invert,
    "pixelate": effect_pixelate,
    "timewarp": effect_timewarp,
    "glitch": effect_glitch,
    "zoom": effect_zoom,
    "flash": effect_flash,
    "rgbshift": effect_rgb_shift
}

# --- Beat Detection ---
def get_beat_times(audio_file):
    """Loads audio and returns times of beat."""
    y, sr = librosa.load(audio_file)
    tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr)
    beat_times = librosa.frames_to_time(beat_frames, sr=sr)
    return beat_times

# --- MAIN ---
def main():
    parser = argparse.ArgumentParser(description="Audio Video generator / Enhancer")
    parser.add_argument("--input", type=str, default="input.mp4", help="Video input")
    parser.add_argument("--output", type=str, default="output.mp4", help="Video output")
    parser.add_argument("--start", type=float, default=0.0, help="Start of the video (seconds)")
    parser.add_argument("--end", type=float, default=None, help="End of the video (seconds)")
    parser.add_argument("--mode", type=str, choices=["random", "specific"], default="random", help="Mode: 'random' or 'specific'")
    parser.add_argument("--effect", type=str, choices=list(EFFECTS.keys()), default="swing", help="Selected effect when mode is 'specific'")
    args = parser.parse_args()
    
    print(f"[INFO] Loading video: {args.input}")
    clip = VideoFileClip(args.input)
    if args.end is not None:
        clip = clip[args.start:args.end]
    else:
        clip = clip[args.start:]
    
    print(f"[INFO] Video loaded. Length: {clip.duration:.2f} s, FPS: {clip.fps}")
    
    # Save TEMP audio
    temp_audio = "temp_audio.wav"
    print("[INFO] Extracting audio for beat detection...")
    clip.audio.write_audiofile(temp_audio, logger=None)
    beat_times = get_beat_times(temp_audio)
    print(f"[INFO] Detected {len(beat_times)} beats.")
    
    beat_threshold = 0.1
    # Logging stuff
    last_logged = [-beat_threshold]
    
    def make_frame(t):
        frame = clip.get_frame(t)
        if np.any(np.abs(beat_times - t) < beat_threshold):
            if args.mode == "random":
                effect_name = random.choice(list(EFFECTS.keys()))
            else:
                effect_name = args.effect
            if t - last_logged[0] >= beat_threshold:
                print(f"[INFO] {t:.2f}s: Applying effect '{effect_name}'")
                last_logged[0] = t
            return EFFECTS[effect_name](frame, t)
        else:
            return frame

    print("[INFO] Processing video with effects...")
    processed_clip = VideoClip(make_frame, duration=clip.duration)
    processed_clip.fps = clip.fps
    processed_clip = processed_clip.with_audio(clip.audio)
    
    print(f"[INFO] Saving video: {args.output}")
    processed_clip.write_videofile(args.output, audio_codec="aac")
    
    print("[INFO] Deleting temporary audio file...")
    os.remove(temp_audio)
    print("[INFO] Temporary audio file deleted.")

if __name__ == "__main__":
    main()

