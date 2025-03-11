#
# I AM NOT RESPONDING TO ANYONE WHO WANTS TO USE THIS SCRIPT AND CAN'T USE IT!! I ONLY ANSWER IF YOU HAVE A SERIOUS PROBLEM WITH USING IT!!
#
# If the subtitles are not matching the sung text, it is not my fault, but STT models fault!
#
# This script makes subtitles using audio/video only.
#
# You can change the whisper model to something else or if you want, you can make or use your own STT model.
#
# You can edit this code because the subtitles are pretty basic.
#
# Requirements: pip install moviepy openai-whisper
# Requirements if problems with whisper (helped for me): pip install --upgrade openai-whisper
#
# You need to have the font you want to use
#

import argparse
import os
import textwrap
import whisper
from moviepy import *
import tempfile

def write_srt(segments, filename="text.txt"):
    """Write segments to SRT file."""
    with open(filename, "w", encoding="utf-8") as f:
        for i, seg in enumerate(segments, start=1):
            # Format start time
            start = seg["start"]
            hours = int(start // 3600)
            minutes = int((start % 3600) // 60)
            seconds = start % 60
            start_str = f"{hours:02d}:{minutes:02d}:{seconds:06.3f}".replace(".", ",")
            # Format end time
            end = seg["end"]
            hours = int(end // 3600)
            minutes = int((end % 3600) // 60)
            seconds = end % 60
            end_str = f"{hours:02d}:{minutes:02d}:{seconds:06.3f}".replace(".", ",")
            # Wrap text for readability
            wrapped_text = "\n".join(textwrap.wrap(seg["text"].strip(), width=40))
            f.write(f"{i}\n")
            f.write(f"{start_str} --> {end_str}\n")
            f.write(f"{wrapped_text}\n\n")

def read_srt(filename="text.txt"):
    """Read SRT file and return list of segments."""
    segments = []
    with open(filename, "r", encoding="utf-8") as f:
        content = f.read().strip()
    if not content:
        return segments
    blocks = content.split("\n\n")
    for block in blocks:
        lines = block.splitlines()
        if len(lines) >= 3:
            # First line is index (ignore)
            time_line = lines[1]
            try:
                start_str, arrow, end_str = time_line.split()
            except Exception:
                continue
            def parse_time(t):
                h, m, s_ms = t.split(":")
                s, ms = s_ms.split(",")
                return int(h)*3600 + int(m)*60 + float(s) + float(ms)/1000
            start = parse_time(start_str.strip())
            end = parse_time(end_str.strip())
            text = "\n".join(lines[2:]).strip()
            segments.append({"start": start, "end": end, "text": text})
    return segments

def main():
    parser = argparse.ArgumentParser(
        description="Create video with subtitles"
    )
    parser.add_argument("--audio", required=True, help="Audio file")
    parser.add_argument("--background", required=True, help="Video file")
    parser.add_argument("--output", default="output.mp4", help="Output file")
    parser.add_argument("--font", default="mainfont.ttf", help="Font")
    parser.add_argument("--font_size", default=40, type=int, help="Font size")
    parser.add_argument("--opacity", default=0.3, type=float, help="Background opacity")
    parser.add_argument("--min_duration", default=0.8, type=float, 
                      help="Minimum subtitle duration in seconds")
    parser.add_argument("--merge_threshold", default=0, type=float,
                      help="Merge segments closer than this threshold")
    parser.add_argument("--speech_threshold", default=0.1, type=float,
                      help="Minimum speech probability to keep segment")
    parser.add_argument("--fps", default=24, type=int, help="Set video framerate")
    parser.add_argument("--usetext", action="store_true", help="Skips AI STT and makes video using text.txt data")
    args = parser.parse_args()

    # Load and process audio/video
    print("INFO: Loading background and audio...")
    background = VideoFileClip(args.background)
    audio_clip = AudioFileClip(args.audio)
    video_duration = min(background.duration, audio_clip.duration)
    background = background.subclipped(0, video_duration)
    audio_clip = audio_clip.subclipped(0, video_duration)

    if not args.usetextx        :
        # Transcribe with Whisper
        print("INFO: Transcribing audio with Whisper...")
        with tempfile.NamedTemporaryFile(suffix=".wav") as tmp_audio:
            audio_clip.write_audiofile(tmp_audio.name, codec='pcm_s16le', logger=None)
            model = whisper.load_model("large-v3")   # base (less than 300 MBs) / medium (more than 1.5 GBs) / large-v3 (more than 2.8 GBs)
            result = model.transcribe(tmp_audio.name, word_timestamps=False)

        # Process segments
        print("INFO: Processing segments...")
        filtered_segments = []
        for seg in result["segments"]:
            # Filter out non-speech segments
            if seg.get('no_speech_prob', 1) > (1 - args.speech_threshold):
                continue
                
            # Apply minimum duration
            if seg['end'] - seg['start'] < args.min_duration:
                continue
                
            filtered_segments.append(seg)

        # Merge adjacent segments
        merged_segments = []
        for seg in filtered_segments:
            if not merged_segments:
                merged_segments.append(seg)
            else:
                last = merged_segments[-1]
                if seg['start'] - last['end'] < args.merge_threshold:
                    # Merge segments
                    last['end'] = seg['end']
                    last['text'] += " " + seg['text'].strip()
                else:
                    merged_segments.append(seg)

        # Create text.txt
        print("INFO: Writing subtitles to text.txt for editing...")
        write_srt(merged_segments, filename="text.txt")
        print("INFO: Please edit text.txt as needed! Press ENTER to continue.")
        input()
    else:
        print("INFO: Skipping transcription phase. Using subtitles from text.txt.")

    # Read text.txt
    print("INFO: Reading edited subtitles from text.txt...")
    edited_segments = read_srt(filename="text.txt")
    if not edited_segments:
        print("ERROR: No subtitles found in text.txt, aborting.")
        return

    # Create subtitle clips
    print("INFO: Creating subtitle clips...")
    subtitle_clips = []
    for seg in edited_segments:
        start = max(0, seg["start"])
        end = min(seg["end"], video_duration)
        
        if end - start < 0.1:
            continue
            
        text = seg["text"].strip()
        wrapped_text = "\n".join(textwrap.wrap(text, width=40))
        
        txt_clip = (TextClip(text=wrapped_text, font=args.font, font_size=args.font_size,
                           color='white', method='label', size=background.size)
                   .with_position('center')
                   .with_start(start)
                   .with_duration(end - start))
        subtitle_clips.append(txt_clip)

    # Create final video
    print("INFO: Creating final video...")
    overlay = ColorClip(
        background.size, 
        color=(0,0,0), 
        duration=video_duration
    ).with_opacity(args.opacity)

    final = CompositeVideoClip([background, overlay] + subtitle_clips)
    final = final.with_audio(audio_clip)
    
    print("INFO: Exporting video...")
    final.write_videofile(args.output, fps=args.fps, codec="libx264", audio_codec="aac")
    print("INFO: Video exported successfully.")

if __name__ == "__main__":
    main()

