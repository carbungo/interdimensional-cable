# 🛸 Interdimensional Cable Radio

24/7 AI-powered multiverse radio station. Tune into broadcasts from across the multiverse.

## Architecture

```
┌─────────────┐    ┌──────────────┐    ┌──────────┐    ┌─────────────┐
│  YouTube     │───▶│  Analyzer    │───▶│ Library  │───▶│ Liquidsoap  │
│  (yt-dlp)   │    │  (essentia)  │    │ (tagged) │    │  (mixer)    │
└─────────────┘    └──────────────┘    └──────────┘    └──────┬──────┘
                                                              │
┌─────────────┐                                               │
│ ElevenLabs  │──▶ Ads / Station IDs / Bumps ────────────────▶│
└─────────────┘                                               │
                                                        ┌─────▼──────┐
                                                        │  Icecast   │
                                                        │  (stream)  │
                                                        └─────┬──────┘
                                                              │
                                                        ┌─────▼──────┐
                                                        │  Web UI    │
                                                        │  (radio.   │
                                                        │ clicksy.me)│
                                                        └────────────┘
```

## Components

### Ingest (`ingest/`)
- `download.py` — yt-dlp wrapper, pulls copyright-free playlists
- `analyze.py` — essentia-based audio analysis (BPM, key, genre, mood, energy)
- `catalog.py` — manages the track database with metadata + dimension/station assignments

### Stream Engine (`stream/`)
- `radio.liq` — Liquidsoap script: playlist rotation, crossfades, ad insertion, station switching
- `icecast.xml` — Icecast2 config

### Ads (`ads/`)
- ElevenLabs-voiced interdimensional advertisements
- Station IDs, bumps, fake emergency broadcasts
- Integration with existing ad pipeline

### Web UI (`web/`)
- Cable box interface with CRT scan lines
- Embedded audio player
- Channel display, waveform visualizer
- Currently tuned dimension/station info

### Infrastructure (`infra/`)
- Docker Compose for Icecast + Liquidsoap
- k8s manifests for web UI
- CI/CD pipeline

## Stations

Tracks are auto-assigned to stations based on audio analysis:

| Station | Dimension | Genre/Mood Profile |
|---|---|---|
| Neon Drift FM | K-22β | Synthwave, high energy, electronic |
| The Void Lounge | C-137 | Lo-fi, chill, ambient |
| Cronenberg Classic | R-2ω | Rock, high BPM, aggressive |
| Council Elevator Music | Σ-12 | Jazz, smooth, mid-tempo |
| Portal Static | NULL | Glitch, experimental, atonal |
| Blips & Hits | J-19ζ7 | Pop, upbeat, danceable |

## Quick Start

```bash
# 1. Download copyright-free music
python3 ingest/download.py --playlist "PLAYLIST_URL"

# 2. Analyze and categorize
python3 ingest/analyze.py --input music/ --output library/

# 3. Start the stream
docker compose up -d

# 4. Listen
open http://radio.clicksy.me
```

## Tech Stack

- **Liquidsoap** — audio stream programming
- **Icecast** — stream server
- **essentia** — music information retrieval
- **yt-dlp** — content acquisition
- **ElevenLabs** — voiced ads and station IDs
- **Next.js / SvelteKit** — web UI (TBD)

## License

MIT
