# Interdimensional Cable Radio — Liquidsoap Configuration
# Broadcasting from dimensions unknown since 2026.

settings.log.level := 3

# ─── Music Sources ───────────────────────────────────────
# Each playlist = one station's music pool, shuffled

gormax = playlist(
  mode="randomize",
  reload_mode="watch",
  "/music/space-funk"
)

void_lounge = playlist(
  mode="randomize",
  reload_mode="watch",
  "/music/lofi-hiphop"
)

neon_drift = playlist(
  mode="randomize",
  reload_mode="watch",
  "/music/ncs"
)

portal_static = playlist(
  mode="randomize",
  reload_mode="watch",
  "/music/lofi-jazz"
)

synthwave_mix = playlist(
  mode="randomize",
  reload_mode="watch",
  "/music/synthwave"
)

# ─── Bumps & Station IDs ────────────────────────────────
# Each station has pre-generated IDs that rotate

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

# ─── Station Assembly ────────────────────────────────────
# Pattern: play 3-5 songs, then a bump, occasionally an emergency

# Rotate: play song, bump every ~4 tracks
gormax_with_bumps = rotate(
  weights=[4, 1],
  [gormax, gormax_bumps]
)

void_with_bumps = rotate(
  weights=[4, 1],
  [void_lounge, void_bumps]
)

neon_with_bumps = rotate(
  weights=[4, 1],
  [neon_drift, neon_bumps]
)

portal_with_bumps = rotate(
  weights=[4, 1],
  [portal_static, portal_bumps]
)

# ─── Channel Surfing ─────────────────────────────────────
# The interdimensional experience: switch stations periodically
# Each "channel" plays 3-6 tracks with bumps, then we flip

radio = rotate(
  weights=[5, 4, 3, 3, 2, 1],
  [
    gormax_with_bumps,      # Space funk (featured, more weight)
    void_with_bumps,        # Lofi chill
    neon_with_bumps,        # NCS energy
    portal_with_bumps,      # Lofi jazz mystery
    synthwave_mix,          # Synthwave (no bumps yet)
    emergency_bumps,        # Rare emergency broadcasts
  ]
)

# Fallback to silence if everything fails
safe_radio = fallback(track_sensitive=false, [radio, blank()])

# ─── Crossfade ───────────────────────────────────────────
# Smooth transitions between tracks
radio_faded = crossfade(
  duration=3.0,
  fade_in=1.5,
  fade_out=1.5,
  safe_radio
)

# ─── Output to Icecast ──────────────────────────────────
output.icecast(
  %mp3(bitrate=192),
  host="icecast",
  port=8000,
  password="crab-source-2026",
  mount="/stream",
  name="Interdimensional Cable Radio",
  description="Broadcasting from dimensions unknown.",
  genre="Interdimensional",
  url="https://radio.clicksy.me",
  public=true,
  radio_faded
)
