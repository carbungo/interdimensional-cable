# Interdimensional Cable Radio — Liquidsoap Configuration
# Smart playlist mode: tracks ordered by BPM/key/energy/timbre compatibility.
# NO crossfade — skip-safe. Individual tracks use fade.in/fade.out for smooth edges.

settings.log.level := 3

# ─── Telnet Server (admin control) ──────────────────────
settings.server.telnet := true
settings.server.telnet.port := 1234
settings.server.telnet.bind_addr := "0.0.0.0"

# ─── Filename → Metadata Extractor ──────────────────────
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

# ─── Source Builder ──────────────────────────────────────
# No crossfade — clean skips, no buffering artifacts.
# Pre-ordered playlists ensure compatible neighbors.
# fade.initial adds a gentle 2s fade-in when a new track starts.
def make_smart_source(path)
  src = map_metadata(fix_metadata, playlist(
    mode="normal",
    loop=true,
    reload_mode="watch",
    path
  ))
  fade.in(duration=2., src)
end

# ─── Music Sources ───────────────────────────────────────

gormax_music = make_smart_source("/playlists/gormax-fm.m3u")
void_music = make_smart_source("/playlists/void-lounge.m3u")
neon_music = make_smart_source("/playlists/neon-drift.m3u")
portal_music = make_smart_source("/playlists/portal-static.m3u")
synthwave_music = make_smart_source("/playlists/council-radio.m3u")
mall_music = make_smart_source("/playlists/vaporwave.m3u")

# ─── Bumps & Station IDs ────────────────────────────────

gormax_bumps = playlist(mode="randomize", reload_mode="watch", "/bumps/gormax-fm/station-ids")
void_bumps = playlist(mode="randomize", reload_mode="watch", "/bumps/void-lounge/station-ids")
neon_bumps = playlist(mode="randomize", reload_mode="watch", "/bumps/neon-drift/station-ids")
portal_bumps = playlist(mode="randomize", reload_mode="watch", "/bumps/portal-static/station-ids")
emergency_bumps = playlist(mode="randomize", reload_mode="watch", "/bumps/shared/emergencies")

# ─── Per-Station Assembly (4 songs → 1 bump) ────────────

gormax_radio = rotate(weights=[4, 1], [gormax_music, gormax_bumps])
void_radio = rotate(weights=[4, 1], [void_music, void_bumps])
neon_radio = rotate(weights=[4, 1], [neon_music, neon_bumps])
portal_radio = rotate(weights=[4, 1], [portal_music, portal_bumps])
council_radio = rotate(weights=[5, 2, 1], [synthwave_music, emergency_bumps, emergency_bumps])
mall_radio = rotate(weights=[6, 1], [mall_music, emergency_bumps])

# ─── Channel Surfing Mix (legacy /stream) ────────────────

surfing = rotate(
  weights=[5, 4, 3, 3, 2, 3, 1],
  [gormax_radio, void_radio, neon_radio, portal_radio, synthwave_music, mall_radio, emergency_bumps]
)

# ─── Output: Per-Station Mounts ──────────────────────────

output.icecast(id="out_gormax", %mp3(bitrate=320), host="icecast", port=8000, password="crab-source-2026",
  mount="/gormax-fm", name="GORMAX FM", description="Hauling grooves across the void", genre="Space Funk", fallible=true, gormax_radio)

output.icecast(id="out_void", %mp3(bitrate=320), host="icecast", port=8000, password="crab-source-2026",
  mount="/void-lounge", name="The Void Lounge", description="Reality is negotiable here", genre="Lofi / Ambient", fallible=true, void_radio)

output.icecast(id="out_neon", %mp3(bitrate=320), host="icecast", port=8000, password="crab-source-2026",
  mount="/neon-drift", name="Neon Drift FM", description="Neon-soaked beats from the grid", genre="NCS / Electronic", fallible=true, neon_radio)

output.icecast(id="out_portal", %mp3(bitrate=320), host="icecast", port=8000, password="crab-source-2026",
  mount="/portal-static", name="Portal Static", description="Frequencies between frequencies", genre="Lofi Jazz", fallible=true, portal_radio)

output.icecast(id="out_council", %mp3(bitrate=320), host="icecast", port=8000, password="crab-source-2026",
  mount="/council-radio", name="Council Radio Σ-12", description="Mandatory listening by decree", genre="Synthwave", fallible=true, council_radio)

output.icecast(id="out_mall", %mp3(bitrate=320), host="icecast", port=8000, password="crab-source-2026",
  mount="/mall-fm", name="MALL∞ FM", description="Echoes from the eternal mall", genre="Vaporwave / Future Funk", fallible=true, mall_radio)

output.icecast(id="out_stream", %mp3(bitrate=320), host="icecast", port=8000, password="crab-source-2026",
  mount="/stream", name="Interdimensional Cable Radio", description="Broadcasting from dimensions unknown.",
  genre="Interdimensional", url="https://radio.clicksy.me", public=true, fallible=true, surfing)
