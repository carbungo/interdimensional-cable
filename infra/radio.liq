# Interdimensional Cable Radio — Liquidsoap Configuration
# Broadcasting from dimensions unknown since 2026.

settings.log.level := 3

# ─── Music Sources ───────────────────────────────────────

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
# Pattern: play ~4 songs, then a bump

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

radio = rotate(
  weights=[5, 4, 3, 3, 2, 1],
  [
    gormax_with_bumps,
    void_with_bumps,
    neon_with_bumps,
    portal_with_bumps,
    synthwave_mix,
    emergency_bumps,
  ]
)

# ─── Output to Icecast ──────────────────────────────────
# Use fallback with blank() to ensure infallible source
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
  fallible=true,
  radio
)
