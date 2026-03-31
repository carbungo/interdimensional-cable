#!/usr/bin/env python3
"""
Download and split timestamped YouTube compilation videos into individual tracks.

Parses timestamps from video description, downloads full audio, splits with ffmpeg.

Usage:
    python3 split.py --url "https://youtu.be/VIDEO_ID" --output ../music/custom-folder/
    python3 split.py --url "https://youtu.be/VIDEO_ID" --output ../music/custom-folder/ --dry-run
"""

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path


def parse_timestamp(ts: str) -> int:
    """Convert timestamp string to seconds. Handles H:MM:SS, MM:SS, M:SS."""
    parts = ts.strip().split(':')
    parts = [int(p) for p in parts]
    if len(parts) == 3:
        return parts[0] * 3600 + parts[1] * 60 + parts[2]
    elif len(parts) == 2:
        return parts[0] * 60 + parts[1]
    return parts[0]


def extract_tracks_from_description(description: str) -> list[dict]:
    """
    Parse timestamped track list from YouTube description.
    Matches patterns like:
        0:00 Track Name
        01:23 Track Name
        1:23:45 Track Name
        0:00 - Track Name
        [0:00] Track Name
    """
    tracks = []

    # Match timestamp at start of line followed by track name
    pattern = r'^\[?(\d{1,2}:\d{2}(?::\d{2})?)\]?\s*[-–—]?\s*(.+?)$'

    for line in description.split('\n'):
        line = line.strip()
        if not line:
            continue

        match = re.match(pattern, line)
        if match:
            ts_str = match.group(1)
            title = match.group(2).strip()

            # Skip lines that are clearly not track names
            if len(title) < 1 or title.startswith('#') or title.startswith('http'):
                continue

            tracks.append({
                "timestamp": ts_str,
                "start_seconds": parse_timestamp(ts_str),
                "title": title,
            })

    # Sort by start time
    tracks.sort(key=lambda t: t["start_seconds"])

    # Calculate end times (next track's start, or None for last)
    for i in range(len(tracks)):
        if i + 1 < len(tracks):
            tracks[i]["end_seconds"] = tracks[i + 1]["start_seconds"]
        else:
            tracks[i]["end_seconds"] = None  # ffmpeg will go to end

    return tracks


def download_full_audio(url: str, output_dir: str) -> tuple[str, dict]:
    """Download full audio and return (filepath, metadata)."""
    os.makedirs(output_dir, exist_ok=True)
    temp_path = os.path.join(output_dir, "_full_compilation")

    # Get metadata first
    result = subprocess.run(
        ["yt-dlp", "--print", "%(title)s", "--print", "%(id)s",
         "--print", "%(description)s", "--skip-download", url],
        capture_output=True, text=True, timeout=30
    )
    lines = result.stdout.strip().split('\n')
    title = lines[0] if lines else "Unknown"
    video_id = lines[1] if len(lines) > 1 else "unknown"
    description = '\n'.join(lines[2:]) if len(lines) > 2 else ""

    # Download audio
    print(f"📥 Downloading: {title}...")
    subprocess.run(
        ["yt-dlp", "-x", "--audio-format", "mp3", "--audio-quality", "0",
         "-o", f"{temp_path}.%(ext)s", url],
        check=True, timeout=600
    )

    mp3_path = f"{temp_path}.mp3"
    if not os.path.exists(mp3_path):
        raise FileNotFoundError(f"Download failed — {mp3_path} not found")

    return mp3_path, {
        "title": title,
        "id": video_id,
        "description": description,
    }


def split_track(full_audio: str, track: dict, index: int, total: int,
                output_dir: str, album_title: str) -> str:
    """Split a single track from the full audio using ffmpeg."""
    # Clean filename — preserve most chars, just strip filesystem-unsafe ones
    safe_title = re.sub(r'[<>:"/\\|?*]', '', track["title"]).strip()
    safe_title = re.sub(r'\s+', ' ', safe_title)
    filename = f"{index:03d} - {safe_title}.mp3"
    output_path = os.path.join(output_dir, filename)

    cmd = ["ffmpeg", "-y", "-i", full_audio,
           "-ss", str(track["start_seconds"]),
           "-metadata", f"title={track['title']}",
           "-metadata", f"album={album_title}",
           "-metadata", f"track={index}/{total}",
           "-c:a", "libmp3lame", "-q:a", "0"]

    if track["end_seconds"] is not None:
        duration = track["end_seconds"] - track["start_seconds"]
        cmd.extend(["-t", str(duration)])

    cmd.append(output_path)

    subprocess.run(cmd, capture_output=True, check=True, timeout=120)
    return output_path


def main():
    parser = argparse.ArgumentParser(description="Split timestamped YouTube compilations")
    parser.add_argument("--url", required=True, help="YouTube video URL")
    parser.add_argument("--output", required=True, help="Output directory for split tracks")
    parser.add_argument("--dry-run", action="store_true", help="Show parsed tracks without downloading")
    args = parser.parse_args()

    # Get description for parsing
    print("🔍 Fetching video info...")
    result = subprocess.run(
        ["yt-dlp", "--print", "%(title)s\n%(description)s", "--skip-download", args.url],
        capture_output=True, text=True, timeout=30
    )
    output = result.stdout.strip()
    title = output.split('\n')[0]
    description = '\n'.join(output.split('\n')[1:])

    tracks = extract_tracks_from_description(description)

    if not tracks:
        print("❌ No timestamped tracks found in description!")
        print("Description preview:")
        print(description[:500])
        sys.exit(1)

    print(f"\n🎵 Found {len(tracks)} tracks in \"{title}\":\n")
    for i, t in enumerate(tracks, 1):
        duration = ""
        if t["end_seconds"]:
            dur = t["end_seconds"] - t["start_seconds"]
            duration = f" ({dur // 60}:{dur % 60:02d})"
        print(f"  {i:2d}. [{t['timestamp']}] {t['title']}{duration}")

    if args.dry_run:
        print("\n(dry run — no download)")
        return

    # Download full audio
    print()
    full_path, meta = download_full_audio(args.url, args.output)

    # Split into individual tracks
    print(f"\n✂️  Splitting {len(tracks)} tracks...")
    for i, track in enumerate(tracks, 1):
        print(f"  [{i}/{len(tracks)}] {track['title']}...")
        split_track(full_path, track, i, len(tracks), args.output, title)

    # Clean up full audio
    os.remove(full_path)
    print(f"\n✅ Done! {len(tracks)} tracks saved to {args.output}")

    # Write metadata sidecar
    meta_path = os.path.join(args.output, "_compilation_info.json")
    with open(meta_path, 'w') as f:
        json.dump({"source": args.url, "album": title, "tracks": tracks, **meta}, f, indent=2)


if __name__ == "__main__":
    main()
