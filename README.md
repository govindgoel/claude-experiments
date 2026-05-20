# Claude Experiments 🧪

A collection of real-time AR experiments built with Python, OpenCV, and MediaPipe — all created using [Claude Code](https://claude.ai/code).

---

## Experiments

### 1. Sudarshan Chakra AR
> `sudarshan_chakra_ar.py`

Real-time augmented reality overlay of the mythological **Sudarshan Chakra** (weapon of Lord Krishna) on your index finger using your laptop camera.

**Features**
- Detects your index finger's distal phalanx in real-time
- Renders an ornate golden chakra as a **lateral spinning disc** (perpendicular to finger, not face-on)
- Pulsing divine aura with purple-to-gold cosmic glow
- Rotating light rays and particle sparkles
- Auto-scales to finger size and tracks finger tilt

**Run**
```bash
python3 sudarshan_chakra_ar.py
```
Press `Q` to quit.

---

### 2. Finger Connect AR
> `finger_connect_ar.py`

Hold both hands up with fingertips facing each other — the space between your fingers comes alive with energy effects.

**Features**
- Tracks all 10 fingertips across both hands simultaneously
- 4 switchable effect modes
- Persistent motion trail (long-exposure style)
- Additive glow blending over live webcam feed

**Modes**

| Key | Mode | Description |
|-----|------|-------------|
| `1` | Plasma Streams | Glowing particles flow along wobbling beams between matching fingertips |
| `2` | Lightning Arcs | Jagged flickering arcs with random branches between fingers |
| `3` | Spirograph Web | Evolving spirograph patterns bloom from each fingertip |
| `4` | Constellation Net | Star nodes spawn from fingertips and form a drifting connected web |
| `SPACE` | Randomise | Switch colour palette and regenerate the current pattern |

**Run**
```bash
python3 finger_connect_ar.py
```
Press `Q` to quit.

---

## Tech Stack

| Layer | Library | Purpose |
|-------|---------|---------|
| Hand tracking | [MediaPipe](https://ai.google.dev/edge/mediapipe/solutions/vision/hand_landmarker) 0.10+ | 21-point hand landmark detection |
| Computer vision | [OpenCV](https://opencv.org/) | Camera capture, drawing, alpha blending |
| Numerics | [NumPy](https://numpy.org/) | Matrix transforms, pixel manipulation |
| Language | Python 3.13 | — |
| AI assistant | [Claude Code](https://claude.ai/code) | Entire codebase generated via Claude Sonnet 4.6 |

---

## Setup

```bash
# Create a virtual environment
python3 -m venv .
source bin/activate

# Install dependencies
pip install opencv-python mediapipe numpy

# The hand landmark model is included (hand_landmarker.task)
```

Requires a working webcam. Tested on macOS with an M2 Pro.

---

*Built with [Claude Code](https://claude.ai/code) by Anthropic*
