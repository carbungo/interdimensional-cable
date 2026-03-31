#!/usr/bin/env python3
"""
Generate station ID bumps and DJ chatter for Interdimensional Cable Radio.

Pre-generates station IDs (reusable) and can generate live DJ chatter
for track transitions.

Usage:
    python3 generate-bumps.py --station gormax-fm --type station-id --count 10
    python3 generate-bumps.py --station void-lounge --type dj-chatter --prev "Mercury" --next "Saturn"
    python3 generate-bumps.py --station all --type station-id --count 5
    python3 generate-bumps.py --type emergency --count 5
"""

import argparse
import json
import os
import random
import subprocess
import sys
import tempfile
import time
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.resolve()
PROJECT_DIR = SCRIPT_DIR.parent
BUMPS_DIR = PROJECT_DIR / "stream" / "bumps"
ELEVENLABS_CONFIG = PROJECT_DIR.parent / "interdimensional-cable" / "stream" / "voices.json"

# ElevenLabs API
ELEVENLABS_KEY = "sk_1fb1ed2dec15cc1d8164220e4a3b812468b50b3bd742b2e2"
ELEVENLABS_URL = "https://api.elevenlabs.io/v1/text-to-speech"

# Station definitions
STATIONS = {
    "gormax-fm": {
        "name": "Gormax FM",
        "dimension": "Ω-70s",
        "frequency": "94.7 petahertz",
        "location": "Relay Station 7, Maricu System",
        "vibe": "Space trucker radio. Warm, analog, nostalgic. Plays retro funk and cosmic groove. Broadcasting from near a Dyson swarm. Listeners are haulers, mechanics, drifters between systems.",
        "dj_name": "Big Vorp",
        "voice_id": "pqHfZKP75CvOlQylNhV4",  # Bill - wise narrator
        "voice_name": "Bill",
    },
    "void-lounge": {
        "name": "The Void Lounge",
        "dimension": "C-137",
        "frequency": "33.3 megahertz",
        "location": "Subspace Pocket, between dimensions",
        "vibe": "Late-night chill. Floating in the space between realities. Lofi beats for interdimensional insomnia. The DJ sounds like they haven't slept in 3 cycles but they're at peace with it.",
        "dj_name": "Null",
        "voice_id": "cjVigY5qzO86Huf0OWal",  # Eric - smooth/trustworthy
        "voice_name": "Eric",
    },
    "neon-drift": {
        "name": "Neon Drift FM",
        "dimension": "K-22β",
        "frequency": "88.8 gigahertz",
        "location": "Neo-Citadel Broadcasting Tower",
        "vibe": "High-energy electronic, synthwave, NCS bangers. Neon-lit megacity. Flying cars, chrome everything. The DJ is amped up, talks fast, hypes everything. Think cyberpunk pirate radio.",
        "dj_name": "Chromex",
        "voice_id": "IKne3meq5aSn9XLyUdCD",  # Charlie - energetic Aussie
        "voice_name": "Charlie",
    },
    "portal-static": {
        "name": "Portal Static",
        "dimension": "NULL",
        "frequency": "unknown",
        "location": "Signal origin: unresolved",
        "vibe": "Mysterious. Ambient, glitchy, experimental. This station shouldn't exist. It broadcasts from nowhere. The DJ might not be a person. Transmissions feel found, not produced. Eerie calm.",
        "dj_name": "???",
        "voice_id": "2EiwWnXFnvU5JabPnv8n",  # Callum - husky trickster
        "voice_name": "Callum",
    },
    "blips-and-hits": {
        "name": "Blips & Hits",
        "dimension": "J-19ζ7",
        "frequency": "107.9 terahertz",
        "location": "Blips and Chitz Arcade, Floor 7",
        "vibe": "Fun, upbeat, poppy. Broadcasting from inside an interdimensional arcade. Sound effects, game references, prize announcements between tracks. The DJ is having the time of their life.",
        "dj_name": "Pixel",
        "voice_id": "cgSgspJ2msm6clMCkdEj",  # Jessica - playful/bright
        "voice_name": "Jessica",
    },
    "cronenberg-classic": {
        "name": "Cronenberg Classic",
        "dimension": "R-2ω",
        "frequency": "66.6 kilohertz",
        "location": "The Flesh Tower, Cronenberg Earth",
        "vibe": "Unhinged. Body horror world but they're totally normal about it. Jazz, weird grooves, avant-garde. The DJ casually mentions horrifying biological facts like it's weather. Dark humor.",
        "dj_name": "Dr. Squelch",
        "voice_id": "2EiwWnXFnvU5JabPnv8n",  # Callum
        "voice_name": "Callum",
    },
}

# Prompt templates
STATION_ID_PROMPT = """You are writing a station ID for an interdimensional radio station. 
This is for a Rick and Morty-style universe where alien radio stations broadcast across dimensions.

Station: {name} ({frequency})
Dimension: {dimension}
Broadcasting from: {location}
DJ Name: {dj_name}
Station vibe: {vibe}

Write a SHORT station ID (2-4 sentences, under 60 words). The DJ is speaking directly to listeners.
Include the station name naturally. Reference the dimension, location, or sci-fi details casually — 
like a real radio DJ who lives in this world. Don't explain things, just exist in them.

Variation #{variation} — make each one unique. Some can be funny, some atmospheric, some lore-building.
Do NOT use hashtags, emojis, or markdown. Just spoken words. No sound effects descriptions.
Write ONLY the words the DJ speaks. Nothing else."""

DJ_CHATTER_PROMPT = """You are {dj_name}, DJ at {name} ({frequency}), broadcasting from {location} in Dimension {dimension}.

Station vibe: {vibe}

The song "{prev_track}" just ended. "{next_track}" is about to play.

Write a SHORT transition (2-3 sentences, under 50 words). React to the previous song briefly,
introduce the next one. Stay in character. Be natural — you're a DJ who does this every day in 
this weird dimension. Don't explain the world, just live in it.

Write ONLY the spoken words. No markdown, no emojis, no sound effects descriptions."""

EMERGENCY_PROMPT = """Write a short interdimensional emergency broadcast (1-2 sentences, under 40 words).
This is for a Rick and Morty-style universe. Think: Council of Ricks advisories, portal malfunctions,
Cronenberg outbreaks, temporal anomalies, void incursions. Make it sound official but absurd.

Variation #{variation}. Start with "ATTENTION" or "ADVISORY" or "WARNING".
Write ONLY the broadcast text. No markdown, no emojis."""


def call_llm(prompt: str) -> str:
    """Call Haiku via LiteLLM proxy on carbungo LAN."""
    import urllib.request
    
    payload = json.dumps({
        "model": "claude-haiku-4-5",
        "max_tokens": 200,
        "messages": [{"role": "user", "content": prompt}]
    })
    
    req = urllib.request.Request(
        "http://192.168.1.130:4000/v1/chat/completions",
        data=payload.encode(),
        headers={
            "Content-Type": "application/json",
            "Authorization": "Bearer sk-litellm-carbungo-2026"
        }
    )
    
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read())
        return data["choices"][0]["message"]["content"].strip().strip('"')


def tts(text: str, voice_id: str, output_path: str) -> bool:
    """Generate speech via ElevenLabs API."""
    import urllib.request
    
    payload = json.dumps({
        "text": text,
        "model_id": "eleven_multilingual_v2",
        "voice_settings": {
            "stability": 0.6,
            "similarity_boost": 0.75,
            "style": 0.3,
        }
    })
    
    req = urllib.request.Request(
        f"{ELEVENLABS_URL}/{voice_id}",
        data=payload.encode(),
        headers={
            "Content-Type": "application/json",
            "xi-api-key": ELEVENLABS_KEY,
        }
    )
    
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            with open(output_path, 'wb') as f:
                f.write(resp.read())
        return True
    except Exception as e:
        print(f"  ⚠ TTS error: {e}")
        return False


def generate_station_ids(station_key: str, count: int):
    """Generate N station ID bumps for a station."""
    station = STATIONS[station_key]
    out_dir = BUMPS_DIR / station_key / "station-ids"
    os.makedirs(out_dir, exist_ok=True)
    
    existing = len(list(out_dir.glob("*.mp3")))
    print(f"\n📻 Generating {count} station IDs for {station['name']} (Dimension {station['dimension']})")
    print(f"   DJ: {station['dj_name']} (voice: {station['voice_name']})")
    print(f"   Existing: {existing}")
    
    for i in range(count):
        idx = existing + i + 1
        prompt = STATION_ID_PROMPT.format(**station, variation=idx)
        
        print(f"   [{i+1}/{count}] Generating text...", end=" ", flush=True)
        text = call_llm(prompt)
        print(f"({len(text)} chars)", end=" ", flush=True)
        
        # Save text
        text_path = out_dir / f"id-{idx:03d}.txt"
        with open(text_path, 'w') as f:
            f.write(text)
        
        # Generate audio
        mp3_path = out_dir / f"id-{idx:03d}.mp3"
        print("→ TTS...", end=" ", flush=True)
        if tts(text, station["voice_id"], str(mp3_path)):
            size = os.path.getsize(mp3_path)
            print(f"✅ ({size//1024}KB)")
        else:
            print("❌")
        
        # Rate limit kindness
        time.sleep(0.5)


def generate_emergencies(count: int):
    """Generate emergency broadcast bumps."""
    out_dir = BUMPS_DIR / "shared" / "emergencies"
    os.makedirs(out_dir, exist_ok=True)
    
    existing = len(list(out_dir.glob("*.mp3")))
    # Use Laura for official broadcasts
    voice_id = "FGY2WhTYpPnrIDTdsKH5"  # Laura - quirky/sassy but works for official
    
    print(f"\n⚠️  Generating {count} emergency broadcasts")
    
    for i in range(count):
        idx = existing + i + 1
        prompt = EMERGENCY_PROMPT.format(variation=idx)
        
        print(f"   [{i+1}/{count}] Generating...", end=" ", flush=True)
        text = call_llm(prompt)
        print(f"({len(text)} chars)", end=" ", flush=True)
        
        text_path = out_dir / f"emergency-{idx:03d}.txt"
        with open(text_path, 'w') as f:
            f.write(text)
        
        mp3_path = out_dir / f"emergency-{idx:03d}.mp3"
        print("→ TTS...", end=" ", flush=True)
        if tts(text, voice_id, str(mp3_path)):
            size = os.path.getsize(mp3_path)
            print(f"✅ ({size//1024}KB)")
        else:
            print("❌")
        
        time.sleep(0.5)


def generate_dj_chatter(station_key: str, prev_track: str, next_track: str):
    """Generate a single DJ chatter transition."""
    station = STATIONS[station_key]
    out_dir = BUMPS_DIR / station_key / "dj-chatter"
    os.makedirs(out_dir, exist_ok=True)
    
    prompt = DJ_CHATTER_PROMPT.format(**station, prev_track=prev_track, next_track=next_track)
    
    print(f"🎙️  {station['dj_name']} on {station['name']}...", end=" ", flush=True)
    text = call_llm(prompt)
    print(f"({len(text)} chars)", end=" ", flush=True)
    
    # Use hash for filename
    import hashlib
    fname = hashlib.md5(f"{prev_track}-{next_track}".encode()).hexdigest()[:12]
    
    text_path = out_dir / f"chatter-{fname}.txt"
    with open(text_path, 'w') as f:
        f.write(text)
    
    mp3_path = out_dir / f"chatter-{fname}.mp3"
    print("→ TTS...", end=" ", flush=True)
    if tts(text, station["voice_id"], str(mp3_path)):
        size = os.path.getsize(mp3_path)
        print(f"✅ ({size//1024}KB)")
        return str(mp3_path)
    else:
        print("❌")
        return None


def main():
    parser = argparse.ArgumentParser(description="Generate radio bumps")
    parser.add_argument("--station", default="all", help="Station key or 'all'")
    parser.add_argument("--type", choices=["station-id", "dj-chatter", "emergency"], 
                       default="station-id")
    parser.add_argument("--count", type=int, default=5)
    parser.add_argument("--prev", help="Previous track (for dj-chatter)")
    parser.add_argument("--next", help="Next track (for dj-chatter)")
    parser.add_argument("--list-stations", action="store_true")
    args = parser.parse_args()
    
    if args.list_stations:
        for key, s in STATIONS.items():
            print(f"  {key:20s} | {s['name']:25s} | {s['dimension']:8s} | DJ: {s['dj_name']} ({s['voice_name']})")
        return
    
    if args.type == "emergency":
        generate_emergencies(args.count)
        return
    
    if args.type == "dj-chatter":
        if not args.prev or not args.next:
            print("❌ --prev and --next required for dj-chatter")
            sys.exit(1)
        generate_dj_chatter(args.station, args.prev, args.next)
        return
    
    # Station IDs
    if args.station == "all":
        for key in STATIONS:
            generate_station_ids(key, args.count)
    else:
        if args.station not in STATIONS:
            print(f"❌ Unknown station: {args.station}")
            print(f"   Available: {', '.join(STATIONS.keys())}")
            sys.exit(1)
        generate_station_ids(args.station, args.count)
    
    print("\n🎵 Done!")


if __name__ == "__main__":
    main()
