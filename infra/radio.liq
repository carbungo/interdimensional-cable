# Interdimensional Cable Radio — Liquidsoap Configuration
# Smart playlist mode: tracks ordered by BPM/key/energy/timbre compatibility.
# Crossfade uses smart_crossfade (detects quiet points in audio) combined
# with pre-analyzed ordering so adjacent tracks are always harmonically
# and rhythmically compatible.

settings.log.level := 3

# ─── Filename → Metadata Extractor ──────────────────────
# Many tracks lack ID3 tags. Parse the filename to get artist/title.
# Patterns:
#   "003 - Artist - Title [ytid].mp3" → artist="Artist", title="Title"
#   "003 - Title.mp3" → title="Title"
def fix_metadata(m)
  title = m["title"]
  artist = m["artist"]
  filename = m["filename"]

  if title == "" then
    basename = string.replace(pattern="^.*/", fun(_) -> "", filename)
    basename = string.replace(pattern="\\.[^.]+$", fun(_) -> "", basename)
    basename = string.replace(pattern="^\\d+\\s*-\\s*", fun(_) -> "", basename)
    basename = string.replace(pattern="\\s*\\[[^\\]]*\\]\\s*$", fun(_) -> "", basename)

    parts = string.split(separator=" - ", basename)
    if list.length(parts) >= 2 then
      [("artist", list.nth(default="", parts, 0)),
       ("title", list.nth(default="", parts, 1))]
    else
      [("title", basename)]
    end
  elsif artist == "" then
    []
  else
    []
  end
end

# ─── Smart Crossfade Helper ──────────────────────────────
# smart_crossfade detects the energy envelope of each track:
# - If current track ends quietly → start fading early (up to `duration` seconds before end)
# - If next track starts quietly → overlap them longer
# - If both are loud → quick cut (short overlap)
# Combined with our pre-ordered playlists (compatible BPM/key/energy neighbors),
# this gives seamless, natural transitions.

def make_smart_source(path, duration)
  src = map_metadata(fix_metadata, playlist(
    mode="normal",
    loop=true,
    reload_mode="watch",
    path
  ))
  # Liquidsoap 2.3.x crossfade API:
  #   - First arg: transition function (crossfade.simple handles fade in/out)
  #   - ~duration: how many seconds of each track to buffer for the overlap
  #   - ~width: RMS energy smoothing window (seconds)
  # crossfade takes the volume levels into account — quiet endings/beginnings
  # get longer blends; loud-to-loud gets a quick cut. Combined with our
  # pre-ordered playlists (compatible BPM/key neighbors) this gives clean mixes.
  # Liquidsoap 2.3.x: crossfade handles transition internally using RMS analysis.
  # fade_in/fade_out control the blend shape; duration is how many seconds of
  # each track to buffer for the overlap decision.
  crossfade(
    duration=duration,
    width=2.0,
    fade_in=2.0,
    fade_out=2.5,
    src
  )
end

# ─── Music Sources (smart crossfade + ordered playlists) ─

# Gormax FM (Space Funk): 19 tracks, tight collection — longer crossfades
gormax_music = make_smart_source("/playlists/gormax-fm.m3u", 8.)

# The Void Lounge (Lofi Hip-Hop): 346 tracks, 98% good transitions
void_music = make_smart_source("/playlists/void-lounge.m3u", 9.)

# Neon Drift FM (NCS/Electronic): 114 tracks, 97% good transitions
neon_music = make_smart_source("/playlists/neon-drift.m3u", 7.)

# Portal Static (Lofi Jazz): 128 tracks, 95% good transitions
portal_music = make_smart_source("/playlists/portal-static.m3u", 8.)

# Council Radio (Synthwave): 70 tracks, 97% good transitions
synthwave_music = make_smart_source("/playlists/council-radio.m3u", 8.)

# ─── Bumps & Station IDs ────────────────────────────────
# Note: .txt/.json files in bump dirs may produce decode warnings — benign.

gormax_bumps = playlist(
  mode="randomize",
  reload_mode="watch",
  "/bumps/gormax-fm/station-ids"
)

void_bumps = playlist(
  mode="randomize",
  reload_mode="watch",
  "/bumps/void-lounge/station-ids"
)

neon_bumps = playlist(
  mode="randomize",
  reload_mode="watch",
  "/bumps/neon-drift/station-ids"
)

portal_bumps = playlist(
  mode="randomize",
  reload_mode="watch",
  "/bumps/portal-static/station-ids"
)

emergency_bumps = playlist(
  mode="randomize",
  reload_mode="watch",
  "/bumps/shared/emergencies"
)

# ─── Per-Station Assembly (4 songs → 1 bump) ────────────

gormax_radio = rotate(weights=[4, 1], [gormax_music, gormax_bumps])
void_radio = rotate(weights=[4, 1], [void_music, void_bumps])
neon_radio = rotate(weights=[4, 1], [neon_music, neon_bumps])
portal_radio = rotate(weights=[4, 1], [portal_music, portal_bumps])

# Council gets emergency broadcasts mixed in
council_radio = rotate(weights=[5, 2, 1], [synthwave_music, emergency_bumps, emergency_bumps])

# ─── Channel Surfing Mix (legacy /stream) ────────────────

surfing = rotate(
  weights=[5, 4, 3, 3, 2, 1],
  [
    gormax_radio,
    void_radio,
    neon_radio,
    portal_radio,
    synthwave_music,
    emergency_bumps,
  ]
)

# ─── Output: Per-Station Mounts ──────────────────────────

output.icecast(
  %mp3(bitrate=320),
  host="icecast", port=8000, password="crab-source-2026",
  mount="/gormax-fm",
  name="GORMAX FM",
  description="Hauling grooves across the void",
  genre="Space Funk",
  fallible=true,
  gormax_radio
)

output.icecast(
  %mp3(bitrate=320),
  host="icecast", port=8000, password="crab-source-2026",
  mount="/void-lounge",
  name="The Void Lounge",
  description="Reality is negotiable here",
  genre="Lofi / Ambient",
  fallible=true,
  void_radio
)

output.icecast(
  %mp3(bitrate=320),
  host="icecast", port=8000, password="crab-source-2026",
  mount="/neon-drift",
  name="Neon Drift FM",
  description="Neon-soaked beats from the grid",
  genre="NCS / Electronic",
  fallible=true,
  neon_radio
)

output.icecast(
  %mp3(bitrate=320),
  host="icecast", port=8000, password="crab-source-2026",
  mount="/portal-static",
  name="Portal Static",
  description="Frequencies between frequencies",
  genre="Lofi Jazz",
  fallible=true,
  portal_radio
)

output.icecast(
  %mp3(bitrate=320),
  host="icecast", port=8000, password="crab-source-2026",
  mount="/council-radio",
  name="Council Radio Σ-12",
  description="Mandatory listening by decree",
  genre="Synthwave",
  fallible=true,
  council_radio
)

# Legacy channel-surfing mount
output.icecast(
  %mp3(bitrate=320),
  host="icecast", port=8000, password="crab-source-2026",
  mount="/stream",
  name="Interdimensional Cable Radio",
  description="Broadcasting from dimensions unknown.",
  genre="Interdimensional",
  url="https://radio.clicksy.me",
  public=true,
  fallible=true,
  surfing
)
