#!/usr/bin/env python3
"""
Deduplicate music library using Chromaprint audio fingerprints.
Compares acoustic fingerprints across all tracks — catches re-uploads,
different encodings, and slight variations.

Usage:
    python3 dedup.py --music-dir ../music/ [--threshold 0.9] [--dry-run]
"""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from collections import defaultdict


def get_fingerprint(filepath: str, duration: int = 120) -> tuple[int, list[int]] | None:
    """Get Chromaprint fingerprint for an audio file."""
    try:
        result = subprocess.run(
            ["fpcalc", "-json", "-length", str(duration), filepath],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode != 0:
            return None
        data = json.loads(result.stdout)
        return data.get("duration", 0), data.get("fingerprint", [])
    except (subprocess.TimeoutExpired, json.JSONDecodeError, KeyError):
        return None


def fingerprint_similarity(fp1: list[int], fp2: list[int]) -> float:
    """
    Compare two Chromaprint fingerprints using bitwise similarity.
    Returns 0.0–1.0 where 1.0 = identical.
    """
    if not fp1 or not fp2:
        return 0.0

    # Compare overlapping portion
    min_len = min(len(fp1), len(fp2))
    if min_len == 0:
        return 0.0

    matching_bits = 0
    total_bits = 0

    for i in range(min_len):
        xor = fp1[i] ^ fp2[i]
        # Count matching bits (32-bit integers)
        matching_bits += 32 - bin(xor & 0xFFFFFFFF).count('1')
        total_bits += 32

    return matching_bits / total_bits if total_bits > 0 else 0.0


def find_mp3s(music_dir: str) -> list[Path]:
    """Recursively find all MP3 files."""
    return sorted(Path(music_dir).rglob("*.mp3"))


def main():
    parser = argparse.ArgumentParser(description="Deduplicate music by audio fingerprint")
    parser.add_argument("--music-dir", required=True, help="Root music directory")
    parser.add_argument("--threshold", type=float, default=0.85,
                        help="Similarity threshold for duplicate detection (0.0–1.0, default 0.85)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show duplicates without deleting")
    parser.add_argument("--output", default=None,
                        help="Write duplicate report to JSON file")
    args = parser.parse_args()

    files = find_mp3s(args.music_dir)
    print(f"Found {len(files)} MP3 files")

    # Phase 1: Fingerprint all tracks
    print("\n📊 Fingerprinting tracks...")
    fingerprints = {}
    errors = 0

    for i, f in enumerate(files):
        if (i + 1) % 50 == 0 or i == 0:
            print(f"  [{i+1}/{len(files)}] {f.name[:60]}...")

        fp = get_fingerprint(str(f))
        if fp:
            fingerprints[str(f)] = fp
        else:
            errors += 1
            print(f"  ⚠ Failed: {f.name[:60]}")

    print(f"\n✅ Fingerprinted {len(fingerprints)} tracks ({errors} errors)")

    # Phase 2: Compare fingerprints
    print(f"\n🔍 Comparing {len(fingerprints)} tracks for duplicates (threshold: {args.threshold})...")
    paths = list(fingerprints.keys())
    duplicates = []  # list of (file1, file2, similarity)
    duplicate_set = set()  # files marked as duplicates (keep first seen)

    for i in range(len(paths)):
        if paths[i] in duplicate_set:
            continue

        dur_i, fp_i = fingerprints[paths[i]]

        for j in range(i + 1, len(paths)):
            if paths[j] in duplicate_set:
                continue

            dur_j, fp_j = fingerprints[paths[j]]

            # Quick filter: if durations differ by >15%, skip
            if dur_i > 0 and dur_j > 0:
                ratio = min(dur_i, dur_j) / max(dur_i, dur_j)
                if ratio < 0.85:
                    continue

            sim = fingerprint_similarity(fp_i, fp_j)
            if sim >= args.threshold:
                duplicates.append({
                    "keep": paths[i],
                    "duplicate": paths[j],
                    "similarity": round(sim, 4),
                    "duration_keep": dur_i,
                    "duration_dup": dur_j
                })
                duplicate_set.add(paths[j])
                print(f"  🔁 {sim:.1%} match:")
                print(f"     KEEP: {Path(paths[i]).name[:60]}")
                print(f"     DUP:  {Path(paths[j]).name[:60]}")

    print(f"\n{'='*60}")
    print(f"📊 Results: {len(duplicates)} duplicates found out of {len(fingerprints)} tracks")

    if duplicates:
        total_size = sum(os.path.getsize(d["duplicate"]) for d in duplicates if os.path.exists(d["duplicate"]))
        print(f"💾 Space recoverable: {total_size / 1024 / 1024:.1f} MB")

    if args.output:
        with open(args.output, 'w') as f:
            json.dump({"threshold": args.threshold, "duplicates": duplicates}, f, indent=2)
        print(f"\n📄 Report saved to {args.output}")

    if not args.dry_run and duplicates:
        print(f"\n🗑️  Removing {len(duplicates)} duplicates...")
        for d in duplicates:
            dup_path = d["duplicate"]
            # Also remove the .info.json sidecar
            info_path = dup_path.rsplit('.mp3', 1)[0] + '.info.json'
            try:
                os.remove(dup_path)
                if os.path.exists(info_path):
                    os.remove(info_path)
                print(f"  ✓ Removed: {Path(dup_path).name[:60]}")
            except OSError as e:
                print(f"  ✗ Error removing {Path(dup_path).name[:60]}: {e}")
        print("✅ Done!")
    elif args.dry_run and duplicates:
        print("\n(dry run — no files removed)")


if __name__ == "__main__":
    main()
