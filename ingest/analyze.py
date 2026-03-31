#!/usr/bin/env python3
"""
Analyze music tracks using essentia for BPM, key, energy, danceability,
loudness, and spectral features. Outputs a catalog JSON with per-track
metadata and auto-assigned station/dimension.

Usage:
    python3 analyze.py --music-dir ../music/ --output ../library/catalog.json
    python3 analyze.py --music-dir ../music/ --output ../library/catalog.json --limit 10
"""

import argparse
import json
import os
import sys
from pathlib import Path

import essentia
import essentia.standard as es


# Station definitions — tracks get assigned based on feature matching
STATIONS = [
    {
        "id": "neon-drift-fm",
        "name": "Neon Drift FM",
        "dimension": "K-22β",
        "description": "Synthwave, retro electronic, high energy",
        "rules": {
            "bpm_range": (100, 160),
            "energy_min": 0.5,
            "preferred_sources": ["synthwave"],
            "tags": ["electronic", "synth", "retro", "wave", "80s", "neon"],
        }
    },
    {
        "id": "void-lounge",
        "name": "The Void Lounge",
        "dimension": "C-137",
        "description": "Lo-fi, chill, ambient, downtempo",
        "rules": {
            "bpm_range": (50, 100),
            "energy_max": 0.5,
            "preferred_sources": ["lofi-jazz", "lofi-hiphop"],
            "tags": ["lofi", "lo-fi", "chill", "jazz", "hop", "relax", "ambient", "cafe"],
        }
    },
    {
        "id": "blips-and-hits",
        "name": "Blips & Hits",
        "dimension": "J-19ζ7",
        "description": "Pop, upbeat, danceable, EDM",
        "rules": {
            "bpm_range": (110, 180),
            "energy_min": 0.6,
            "danceability_min": 0.6,
            "preferred_sources": ["ncs"],
            "tags": ["edm", "dance", "pop", "bass", "drop", "electro", "house", "dubstep"],
        }
    },
    {
        "id": "council-elevator",
        "name": "Council Elevator Music",
        "dimension": "Σ-12",
        "description": "Jazz, smooth, mid-tempo, easy listening",
        "rules": {
            "bpm_range": (70, 130),
            "energy_max": 0.6,
            "preferred_sources": ["lofi-jazz"],
            "tags": ["jazz", "smooth", "piano", "saxophone", "swing", "bossa"],
        }
    },
    {
        "id": "portal-static",
        "name": "Portal Static",
        "dimension": "NULL",
        "description": "Glitch, experimental, lo-fi beats",
        "rules": {
            "bpm_range": (60, 110),
            "energy_max": 0.4,
            "preferred_sources": ["lofi-hiphop"],
            "tags": ["beat", "lofi", "hip", "tape", "vinyl", "sample"],
        }
    },
    {
        "id": "cronenberg-classic",
        "name": "Cronenberg Classic",
        "dimension": "R-2ω",
        "description": "Rock, aggressive, high energy",
        "rules": {
            "bpm_range": (120, 200),
            "energy_min": 0.7,
            "tags": ["rock", "metal", "guitar", "heavy", "punk", "hard"],
        }
    },
]


def analyze_track(filepath: str) -> dict | None:
    """Analyze a single audio file with essentia."""
    try:
        # Load audio (mono, 44100 Hz)
        loader = es.MonoLoader(filename=filepath, sampleRate=44100)
        audio = loader()

        if len(audio) < 44100:  # Skip files shorter than 1 second
            return None

        # BPM / Rhythm
        rhythm_extractor = es.RhythmExtractor2013(method="multifeature")
        bpm, beats, beats_confidence, _, beats_intervals = rhythm_extractor(audio)

        # Key detection
        key_extractor = es.KeyExtractor()
        key, scale, key_strength = key_extractor(audio)

        # Energy (RMS)
        energy = es.Energy()(audio)
        rms = es.RMS()(audio)

        # Loudness
        loudness = es.Loudness()(audio)

        # Dynamic complexity
        dynamic_complexity, dynamic_loudness = es.DynamicComplexity()(audio)

        # Danceability
        danceability, danceability_dfa = es.Danceability()(audio)

        # Spectral features (for timbre/genre hints)
        # Ensure even-length audio for FFT
        if len(audio) % 2 != 0:
            audio = audio[:-1]
        frame_size = min(2048, len(audio))
        if frame_size % 2 != 0:
            frame_size -= 1
        spectrum = es.Spectrum(size=frame_size)(audio[:frame_size])
        spectral_centroid = es.Centroid(range=22050)(spectrum)
        spectral_rolloff = es.RollOff()(spectrum)

        # Zero crossing rate (noisiness indicator)
        zcr = es.ZeroCrossingRate()(audio)

        # Duration
        duration = len(audio) / 44100.0

        return {
            "bpm": round(float(bpm), 1),
            "beats_confidence": round(float(beats_confidence), 3),
            "key": key,
            "scale": scale,
            "key_strength": round(float(key_strength), 3),
            "energy": round(float(energy), 6),
            "rms": round(float(rms), 6),
            "loudness": round(float(loudness), 4),
            "dynamic_complexity": round(float(dynamic_complexity), 3),
            "danceability": round(float(danceability), 4),
            "spectral_centroid": round(float(spectral_centroid), 2),
            "spectral_rolloff": round(float(spectral_rolloff), 2),
            "zcr": round(float(zcr), 6),
            "duration": round(duration, 2),
        }
    except Exception as e:
        print(f"  ⚠ Analysis error: {e}", file=sys.stderr)
        return None


def load_yt_metadata(mp3_path: str) -> dict:
    """Load YouTube metadata from sidecar .info.json file."""
    # Try matching info.json path
    base = mp3_path.rsplit('.mp3', 1)[0]
    info_path = base + '.info.json'

    if not os.path.exists(info_path):
        return {}

    try:
        with open(info_path, 'r') as f:
            data = json.load(f)
        return {
            "yt_title": data.get("title", ""),
            "yt_uploader": data.get("uploader", ""),
            "yt_tags": data.get("tags", []),
            "yt_description": (data.get("description", "") or "")[:500],
            "yt_id": data.get("id", ""),
            "yt_view_count": data.get("view_count", 0),
            "yt_like_count": data.get("like_count", 0),
            "yt_categories": data.get("categories", []),
        }
    except (json.JSONDecodeError, KeyError):
        return {}


def score_station(track: dict, station: dict) -> float:
    """Score how well a track matches a station (0.0–1.0+)."""
    rules = station["rules"]
    score = 0.0
    audio = track["audio"]
    meta = track.get("youtube", {})

    # BPM range match
    bpm_lo, bpm_hi = rules.get("bpm_range", (0, 300))
    if bpm_lo <= audio["bpm"] <= bpm_hi:
        score += 1.0
    elif abs(audio["bpm"] - bpm_lo) < 15 or abs(audio["bpm"] - bpm_hi) < 15:
        score += 0.3  # close enough

    # Energy thresholds
    if "energy_min" in rules:
        norm_energy = min(audio["rms"] / 0.15, 1.0)  # normalize RMS
        if norm_energy >= rules["energy_min"]:
            score += 1.0
        else:
            score += norm_energy / rules["energy_min"] * 0.5

    if "energy_max" in rules:
        norm_energy = min(audio["rms"] / 0.15, 1.0)
        if norm_energy <= rules["energy_max"]:
            score += 1.0
        else:
            score += (1 - (norm_energy - rules["energy_max"])) * 0.5

    # Danceability
    if "danceability_min" in rules:
        if audio["danceability"] >= rules["danceability_min"]:
            score += 1.0
        else:
            score += audio["danceability"] / rules["danceability_min"] * 0.5

    # Source directory match (strong signal)
    source = track.get("source_dir", "")
    if source in rules.get("preferred_sources", []):
        score += 2.0

    # Tag matching (title + yt tags + description)
    searchable = " ".join([
        track.get("filename", ""),
        meta.get("yt_title", ""),
        " ".join(meta.get("yt_tags", [])),
        meta.get("yt_description", ""),
    ]).lower()

    tag_matches = sum(1 for tag in rules.get("tags", []) if tag in searchable)
    score += min(tag_matches * 0.5, 2.0)  # cap tag bonus

    return score


def assign_station(track: dict) -> tuple[str, float]:
    """Assign a track to the best-matching station."""
    best_station = None
    best_score = -1

    for station in STATIONS:
        s = score_station(track, station)
        if s > best_score:
            best_score = s
            best_station = station

    return best_station, best_score


def find_mp3s(music_dir: str) -> list[tuple[str, Path]]:
    """Find all MP3s with their source directory name."""
    results = []
    music_path = Path(music_dir)
    for mp3 in sorted(music_path.rglob("*.mp3")):
        # Source dir is the immediate parent relative to music_dir
        rel = mp3.relative_to(music_path)
        source = rel.parts[0] if len(rel.parts) > 1 else "unknown"
        results.append((source, mp3))
    return results


def main():
    parser = argparse.ArgumentParser(description="Analyze and categorize music library")
    parser.add_argument("--music-dir", required=True, help="Root music directory")
    parser.add_argument("--output", required=True, help="Output catalog JSON path")
    parser.add_argument("--limit", type=int, default=0, help="Limit number of tracks to analyze (0=all)")
    args = parser.parse_args()

    # Suppress essentia info messages
    essentia.log.infoActive = False
    essentia.log.warningActive = False

    files = find_mp3s(args.music_dir)
    if args.limit > 0:
        files = files[:args.limit]

    print(f"🎵 Analyzing {len(files)} tracks...")

    catalog = []
    station_counts = {}
    errors = 0

    for i, (source, filepath) in enumerate(files):
        if (i + 1) % 25 == 0 or i == 0:
            print(f"  [{i+1}/{len(files)}] {filepath.name[:60]}...")

        # Audio analysis
        audio_features = analyze_track(str(filepath))
        if not audio_features:
            errors += 1
            continue

        # YouTube metadata
        yt_meta = load_yt_metadata(str(filepath))

        track = {
            "file": str(filepath),
            "filename": filepath.name,
            "source_dir": source,
            "audio": audio_features,
            "youtube": yt_meta,
        }

        # Assign station
        station, score = assign_station(track)
        track["station"] = {
            "id": station["id"],
            "name": station["name"],
            "dimension": station["dimension"],
            "score": round(score, 2),
        }

        catalog.append(track)
        station_counts[station["name"]] = station_counts.get(station["name"], 0) + 1

    # Write output
    os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
    with open(args.output, 'w') as f:
        json.dump({
            "total_tracks": len(catalog),
            "stations": {s["name"]: {"id": s["id"], "dimension": s["dimension"], "track_count": station_counts.get(s["name"], 0)} for s in STATIONS},
            "tracks": catalog,
        }, f, indent=2)

    print(f"\n{'='*60}")
    print(f"✅ Analyzed {len(catalog)} tracks ({errors} errors)")
    print(f"\n📻 Station distribution:")
    for station in STATIONS:
        count = station_counts.get(station["name"], 0)
        bar = "█" * min(count, 50)
        print(f"  {station['dimension']:>8} {station['name']:<25} {count:>4} {bar}")

    print(f"\n📄 Catalog saved to {args.output}")


if __name__ == "__main__":
    main()
