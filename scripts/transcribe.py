"""Produce a local, time-aligned ASR draft. Speaker identities require review."""
import argparse
import json
import subprocess

import numpy as np
from pathlib import Path

from faster_whisper import WhisperModel


def timestamp(seconds):
    millis = round(seconds * 1000)
    hours, rest = divmod(millis, 3600000)
    minutes, rest = divmod(rest, 60000)
    return f"{hours:02}:{minutes:02}:{rest // 1000:02}.{rest % 1000:03}"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("media", type=Path)
    parser.add_argument("--model", default="small", help="Cached model name or path")
    parser.add_argument("--language", help="Source language, e.g. zh. Omit for detection.")
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    model = WhisperModel(args.model, device="cpu", compute_type="int8", local_files_only=True)
    command = ["ffmpeg", "-nostdin", "-v", "error", "-i", str(args.media.resolve()),
               "-map", "0:a:0", "-ac", "1", "-ar", "16000", "-f", "f32le", "pipe:1"]
    pcm = subprocess.run(command, stdout=subprocess.PIPE, check=True).stdout
    if not pcm:
        parser.exit(1, "所选音轨为空。\n")
    waveform = np.frombuffer(pcm, dtype="<f4")
    segments, info = model.transcribe(waveform, language=args.language,
                                      task="transcribe", word_timestamps=True,
                                      vad_filter=False, condition_on_previous_text=False)
    rows = []
    for segment in segments:
        rows.append({"start": timestamp(segment.start), "end": timestamp(segment.end),
                     "speaker": "说话人待确认", "draft": segment.text,
                     "words": [{"start": timestamp(w.start), "end": timestamp(w.end),
                                "text": w.word, "probability": round(w.probability, 3)}
                               for w in segment.words or []]})
    if not rows:
        parser.exit(1, "没有可识别片段，请检查音轨或提供逐字稿。\n")
    with args.output.open("x", encoding="utf-8") as out:
        json.dump({"status": "机器初稿，待逐段核听", "duration": timestamp(info.duration),
                   "language": info.language, "segments": rows}, out, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
