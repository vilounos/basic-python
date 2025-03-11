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

def main():
    parser = argparse.ArgumentParser(
        description="Create video with subtitles"
    )
    parser.add_argument("--audio", required=True, help="Audio file")
    parser.add_argument("--background", required=True, help="Video file")
    parser.add_argument("--output", default="output.mp4", help="Output file")
    parser.add_argument("--font", default="/mainfont.ttf", help="Font")
    parser.add_argument("--font_size", default=40, type=int, help="Font size")
    parser.add_argument("--opacity", default=0.3, type=float, help="Background opacity")
    parser.add_argument("--min_duration", default=0.8, type=float, 
                      help="Minimum subtitle duration in seconds")
    parser.add_argument("--merge_threshold", default=0, type=float,
                      help="Merge segments closer than this threshold")
    parser.add_argument("--speech_threshold", default=0.1, type=float,
                      help="Minimum speech probability to keep segment")
    args = parser.parse_args()

    # Load and process audio/video
    background = VideoFileClip(args.background)
    audio_clip = AudioFileClip(args.audio)
    video_duration = min(background.duration, audio_clip.duration)
    background = background.subclipped(0, video_duration)
    audio_clip = audio_clip.subclipped(0, video_duration)

    # Transcribe with Whisper
    with tempfile.NamedTemporaryFile(suffix=".wav") as tmp_audio:
        audio_clip.write_audiofile(tmp_audio.name, codec='pcm_s16le')
        model = whisper.load_model("large-v3")   # base (less than 300 MB) / medium (around 1.5 GBs) / large-v3 (More than 2.8 GBs) DEFAULT PARAMETERS WORK THE BEST WITH large-v3
        result = model.transcribe(tmp_audio.name, word_timestamps=False)

    # Process segments
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

    # Create subtitle clips
    subtitle_clips = []
    for seg in merged_segments:
        start = max(0, seg["start"])
        end = min(seg["end"], video_duration)
        
        # Skip if duration is too short after trimming
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
    overlay = ColorClip(
        background.size, 
        color=(0,0,0), 
        duration=video_duration
    ).with_opacity(args.opacity)

    final = CompositeVideoClip([background, overlay] + subtitle_clips)
    final = final.with_audio(audio_clip)
    
    print("Exporting...")
    final.write_videofile(args.output, fps=24, codec="libx264", audio_codec="aac")

if __name__ == "__main__":
    main()
