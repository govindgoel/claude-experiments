# Finger Connect AR — Prompt Log

> The exact prompts used to build `finger_connect_ar.py` with Claude Code (Claude Sonnet 4.6).

---

## Prompt 1 — Initial Request

> Now create a new experiment where if I keep my both hands fingers facing each other with a distance then connect random particle lines and ability to create random patterns

**Claude designed:**
- Both hands tracked simultaneously (`num_hands=2`)
- All 10 fingertips detected (landmarks 4, 8, 12, 16, 20 on each hand)
- 4 switchable effect modes on keys `1`–`4`
- Persistent motion trail canvas with decay (long-exposure feel)
- Additive blend over webcam feed for glow effect
- `SPACE` to randomise palette + regenerate pattern

**Modes built:**
| Mode | Effect |
|------|--------|
| 1 | **Plasma Streams** — `PlasmaParticle` class with wobble, speed, fade |
| 2 | **Lightning Arcs** — jagged path with flicker + random branches |
| 3 | **Spirograph Web** — hypotrochoid formula per fingertip + midpoint |
| 4 | **Constellation Net** — drifting nodes that connect to nearby fingertips |

---

## Prompt 2 — Zig-zag Lines (attempted, then reverted)

> Along with particles make multi color lines that connect fingers in a zig zag pattern

**What was built:** `draw_zigzag()` — sine-wave based multi-colour animated line,
wired into all 4 modes with matching + diagonal cross-links.

---

## Prompt 3 — Revert

> Revert your last changes

All zig-zag additions removed. Modes restored to their original glowing-line behaviour.

---

## Key Technical Decisions

| Decision | Reason |
|----------|--------|
| Trail canvas with `* 0.78` decay | Simulates long-exposure photography; older frames fade naturally |
| Additive blend (`np.clip(frame + trail)`) | Bright effects glow without washing out the webcam image |
| `PlasmaParticle` tracks `p1`/`p2` each frame | Particles follow moving fingers instead of flying off |
| Lightning regenerated every N frames per finger | Different flicker rates per finger avoids uniform strobing |
| Spirograph uses hypotrochoid formula | `(R-r)cos(θ) + d·cos((R-r)/r · θ)` gives authentic spirograph curves |
| Constellation nodes bounce off frame bounds | Keeps the web visible without nodes escaping the frame |
| `SPACE` clears all pools/caches | Instant clean slate — new palette starts fresh without ghost particles |

---

## Effect Architecture

```
Webcam frame
    │
    ▼
trail canvas (decays 0.78× per frame)
    │  ← mode 1: PlasmaParticle.draw()
    │  ← mode 2: render_lightning()
    │  ← mode 3: SpirographWeb.draw()
    │  ← mode 4: ConstellationNet.draw()
    │
    ▼
composite = clip(frame + trail, 0, 255)   ← additive glow blend
    │
    ▼
HUD text overlay → imshow
```
