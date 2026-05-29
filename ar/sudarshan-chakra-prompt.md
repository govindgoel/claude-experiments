# Sudarshan Chakra AR — Prompt Log

> The exact prompts used to build `sudarshan_chakra_ar.py` with Claude Code (Claude Sonnet 4.6).

---

## Prompt 1 — Initial Request

> Need to create an app when the camera of laptop is turned on show a sudarshan chakra on my first finger, build a plan gather requirements ask questions and build

**Claude asked:**
- Which platform/language? → Python (OpenCV + MediaPipe)
- How should it look? → Realistic textured
- Where on the finger? → Distal phalanx of first finger

**Claude built:** Initial working app using `mp.solutions.hands` (legacy API). Hit a Python 3.13 compatibility error — `mediapipe` dropped the `solutions` API in 0.10.x. Switched to the new **MediaPipe Tasks API** (`HandLandmarker`) and downloaded `hand_landmarker.task` model.

---

## Prompt 2 — Visual Upgrade

> *(User shared a screenshot of the working app and a reference image of the mythological Sudarshan Chakra)*
>
> Right now it is like this it should be as portrayed and add the background effects to sooth as per mythology of krishna

**Changes made:**
- Redesigned chakra: 5 concentric rings, 16 main spokes, 32 narrow spokes, 48 serrated teeth, glowing jewel hub
- Added pulsing **divine aura** — purple-to-gold radial glow layers
- Added **rotating light rays** (8 rays, breathing brightness)
- Added **particle sparkles** that fly upward from the chakra rim
- Added **vignette** to darken frame edges for a cosmic feel

---

## Prompt 3 — Lateral Disc Perspective

> Still the issue is it is coming as a front view the chakra should be lateral on the finger as disc inserted in finger hope you understood

**Changes made:**
- Added `make_lateral_disc()` — 3-step affine transform pipeline:
  1. **Spin** the chakra face pattern (`spin_angle`)
  2. **Squish** vertically to 18% height → becomes a thin ellipse
  3. **Tilt** the ellipse so its thin axis aligns with the finger direction
- Finger angle computed from landmark 7 (DIP) → landmark 8 (tip) via `atan2`
- Aura also squished to match disc tilt

---

## Prompt 4 — Size & Proportion Fix

> *(User shared screenshot showing chakra too large, aura spanning whole frame, particles scattered everywhere)*
>
> Do you see the problem

**Changes made:**
- Chakra radius: `seg × 3.0` → `seg × 1.4` (fits snugly on finger)
- Aura canvas padding: `1.6×` → `0.5×` size
- Aura glow layers: max radius `2.8×` → `1.45×` (hugs the disc)
- Light rays: length `2.0×` → `1.3×`
- Particles: spawn radius `0.6–2.0×` → `0.85–1.15×` (rim only), size 2–5 → 1–3

---

## Key Technical Decisions

| Decision | Reason |
|----------|--------|
| MediaPipe Tasks API over legacy `solutions` | `solutions` removed in mediapipe 0.10+ for Python 3.13 |
| Landmarks 7 + 8 for distal phalanx | DIP joint (7) to fingertip (8) defines the top finger segment |
| 3-step affine transform for disc | Spin → Squish → Tilt is the correct decomposition for a perspective lateral disc |
| Squish factor 0.18 | Visually matches a disc viewed from ~80° angle without disappearing |
| Additive chakra cache by pixel size | Avoids regenerating the complex chakra drawing every frame |
