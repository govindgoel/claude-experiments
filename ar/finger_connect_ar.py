"""
Finger Connect AR
─────────────────
Hold both hands up with fingertips facing each other.
Particle streams, lightning arcs, and evolving geometric patterns
emerge in the space between your fingers.

Controls:
  Q        — quit
  SPACE    — randomise pattern / colour palette
  1–4      — switch effect mode
             1 = Plasma streams   (default)
             2 = Lightning arcs
             3 = Spirograph web
             4 = Constellation net
"""

import cv2
import mediapipe as mp
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision as mp_vision
import numpy as np
import math, random, os, time

MODEL_PATH = os.path.join(os.path.dirname(__file__), "hand_landmarker.task")

# Fingertip landmark indices (thumb→pinky)
TIPS = [4, 8, 12, 16, 20]

# ── Colour palettes ───────────────────────────────────────────────────────────
PALETTES = [
    [(0,200,255),(50,255,180),(200,255,50),(255,180,0),(255,50,120)],   # gold-green
    [(255,50,200),(200,0,255),(100,50,255),(50,150,255),(0,220,255)],   # purple-blue
    [(0,255,100),(0,220,50),(50,255,200),(100,255,100),(200,255,50)],   # matrix green
    [(0,100,255),(0,50,200),(50,0,255),(100,0,200),(150,50,255)],       # deep blue
    [(255,100,0),(255,150,50),(255,200,100),(200,255,100),(150,255,150)],# fire
]

# ── Helpers ───────────────────────────────────────────────────────────────────

def lerp(a, b, t):
    return a + (b - a) * t

def dist2d(p, q):
    return math.hypot(p[0]-q[0], p[1]-q[1])

def draw_glowing_line(img, p1, p2, color, thickness=2, glow_layers=3):
    """Draw a line with additive glow."""
    for i in range(glow_layers, 0, -1):
        alpha = 0.3 + 0.7 * (1 - i / glow_layers)
        col = tuple(int(c * alpha) for c in color)
        cv2.line(img, p1, p2, col, thickness + i * 2, cv2.LINE_AA)
    cv2.line(img, p1, p2, color, thickness, cv2.LINE_AA)

def draw_glow_circle(img, center, radius, color, thickness=2):
    for i in range(3, 0, -1):
        alpha = 0.25 * (1 - i/4)
        col = tuple(int(c * alpha) for c in color)
        cv2.circle(img, center, radius + i*2, col, thickness + i, cv2.LINE_AA)
    cv2.circle(img, center, radius, color, thickness, cv2.LINE_AA)



# ── Plasma particle stream ────────────────────────────────────────────────────

class PlasmaParticle:
    def __init__(self, p1, p2, color):
        self.reset(p1, p2, color)

    def reset(self, p1, p2, color):
        self.p1 = p1
        self.p2 = p2
        self.t = random.uniform(0, 1)
        self.speed = random.uniform(0.008, 0.025)
        self.direction = random.choice([-1, 1])
        self.wobble_amp = random.uniform(4, 18)
        self.wobble_freq = random.uniform(2, 6)
        self.wobble_phase = random.uniform(0, math.pi * 2)
        self.size = random.randint(2, 6)
        self.color = color
        self.life = 1.0
        self.fade_speed = random.uniform(0.015, 0.035)

    def update(self):
        self.t += self.speed * self.direction
        self.life -= self.fade_speed
        if self.t > 1 or self.t < 0 or self.life <= 0:
            return False
        return True

    def draw(self, img):
        # Base position on the line
        bx = lerp(self.p1[0], self.p2[0], self.t)
        by = lerp(self.p1[1], self.p2[1], self.t)

        # Perpendicular wobble
        dx = self.p2[0] - self.p1[0]
        dy = self.p2[1] - self.p1[1]
        length = max(1, math.hypot(dx, dy))
        px = -dy / length
        py =  dx / length
        wobble = self.wobble_amp * math.sin(self.t * self.wobble_freq * math.pi + self.wobble_phase)
        x = int(bx + px * wobble)
        y = int(by + py * wobble)

        a = self.life
        col = tuple(int(c * a) for c in self.color)
        for gi in range(3, 0, -1):
            gc = tuple(int(c * a * 0.3) for c in self.color)
            cv2.circle(img, (x, y), self.size + gi * 2, gc, -1, cv2.LINE_AA)
        cv2.circle(img, (x, y), self.size, col, -1, cv2.LINE_AA)


# ── Lightning arc ─────────────────────────────────────────────────────────────

def make_lightning(p1, p2, segments=12, jitter=20):
    """Generate a jagged lightning path between p1 and p2."""
    pts = [p1]
    for i in range(1, segments):
        t = i / segments
        bx = lerp(p1[0], p2[0], t)
        by = lerp(p1[1], p2[1], t)
        dx = p2[0] - p1[0]; dy = p2[1] - p1[1]
        length = max(1, math.hypot(dx, dy))
        px = -dy / length; py = dx / length
        offset = random.uniform(-jitter, jitter)
        pts.append((int(bx + px * offset), int(by + py * offset)))
    pts.append(p2)
    return pts

def draw_lightning(img, p1, p2, color, frame):
    if frame % 3 == 0:  # regenerate every 3 frames for flicker
        return make_lightning(p1, p2)
    return None

def render_lightning(img, pts, color):
    for i in range(len(pts) - 1):
        # glow
        cv2.line(img, pts[i], pts[i+1], tuple(c//3 for c in color), 6, cv2.LINE_AA)
        cv2.line(img, pts[i], pts[i+1], tuple(c//2 for c in color), 3, cv2.LINE_AA)
        cv2.line(img, pts[i], pts[i+1], color, 1, cv2.LINE_AA)


# ── Spirograph web ────────────────────────────────────────────────────────────

class SpirographWeb:
    def __init__(self):
        self.phase = 0.0
        self.r1 = random.uniform(0.3, 0.7)
        self.r2 = random.uniform(0.1, 0.4)
        self.k  = random.choice([3, 4, 5, 6, 7, 8])
        self.d  = random.uniform(0.2, 0.9)

    def randomise(self):
        self.r1 = random.uniform(0.3, 0.7)
        self.r2 = random.uniform(0.1, 0.4)
        self.k  = random.choice([3, 4, 5, 6, 7, 8])
        self.d  = random.uniform(0.2, 0.9)

    def draw(self, img, center, radius, color, t):
        pts = []
        steps = 360
        R = self.r1 * radius
        r = self.r2 * radius
        d = self.d  * r
        for i in range(steps + 1):
            theta = 2 * math.pi * i / steps + t * 0.3
            x = int(center[0] + (R - r) * math.cos(theta) + d * math.cos((R - r) / max(1, r) * theta))
            y = int(center[1] + (R - r) * math.sin(theta) - d * math.sin((R - r) / max(1, r) * theta))
            pts.append((x, y))
        for i in range(len(pts) - 1):
            alpha = 0.4 + 0.6 * abs(math.sin(i / steps * math.pi))
            col = tuple(int(c * alpha) for c in color)
            cv2.line(img, pts[i], pts[i+1], col, 1, cv2.LINE_AA)


# ── Constellation net ─────────────────────────────────────────────────────────

class ConstellationNet:
    def __init__(self):
        self.nodes: list[list] = []   # [x, y, vx, vy]
        self.max_nodes = 40
        self.connect_dist = 120

    def seed(self, center, radius, n=6):
        for _ in range(n):
            angle = random.uniform(0, 2 * math.pi)
            d = random.uniform(0, radius)
            x = center[0] + d * math.cos(angle)
            y = center[1] + d * math.sin(angle)
            vx = random.uniform(-0.8, 0.8)
            vy = random.uniform(-0.8, 0.8)
            self.nodes.append([x, y, vx, vy])

    def update(self, bounds):
        for n in self.nodes:
            n[0] += n[2]; n[1] += n[3]
            if n[0] < 0 or n[0] > bounds[0]: n[2] *= -1
            if n[1] < 0 or n[1] > bounds[1]: n[3] *= -1
        if len(self.nodes) > self.max_nodes:
            self.nodes = self.nodes[-self.max_nodes:]

    def draw(self, img, color, hand_pts):
        # Draw edges between close nodes
        for i, a in enumerate(self.nodes):
            for b in self.nodes[i+1:]:
                d = math.hypot(a[0]-b[0], a[1]-b[1])
                if d < self.connect_dist:
                    alpha = 1.0 - d / self.connect_dist
                    col = tuple(int(c * alpha * 0.7) for c in color)
                    cv2.line(img, (int(a[0]), int(a[1])), (int(b[0]), int(b[1])), col, 1, cv2.LINE_AA)

        # Connect hand fingertips to nearby nodes
        for hp in hand_pts:
            for n in self.nodes:
                d = math.hypot(hp[0]-n[0], hp[1]-n[1])
                if d < self.connect_dist * 1.5:
                    alpha = 1.0 - d / (self.connect_dist * 1.5)
                    col = tuple(int(c * alpha) for c in color)
                    cv2.line(img, hp, (int(n[0]), int(n[1])), col, 1, cv2.LINE_AA)

        # Draw nodes
        for n in self.nodes:
            cv2.circle(img, (int(n[0]), int(n[1])), 2, color, -1, cv2.LINE_AA)


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    base_opts = mp_python.BaseOptions(model_asset_path=MODEL_PATH)
    opts = mp_vision.HandLandmarkerOptions(
        base_options=base_opts, num_hands=2,
        min_hand_detection_confidence=0.6,
        min_hand_presence_confidence=0.5,
        min_tracking_confidence=0.5,
    )
    landmarker = mp_vision.HandLandmarker.create_from_options(opts)

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Cannot open camera."); return

    h_cap = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    w_cap = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))

    mode = 1          # 1=plasma 2=lightning 3=spirograph 4=constellation
    palette_idx = 0
    frame_count = 0
    t = 0.0

    # Plasma particles pool (keyed by pair index)
    plasma_pools: dict[int, list] = {}
    MAX_PLASMA = 12   # particles per finger pair

    # Lightning path cache
    lightning_cache: dict[int, list] = {}

    # Spirograph per pair
    spiro = SpirographWeb()

    # Constellation
    constellation = ConstellationNet()

    # Trail canvas (for motion blur / persistence effect)
    trail = np.zeros((h_cap, w_cap, 3), dtype=np.uint8)

    print("Finger Connect AR  |  Q=quit  SPACE=randomise  1-4=mode")

    while True:
        ret, frame = cap.read()
        if not ret: break

        frame = cv2.flip(frame, 1)
        h, w = frame.shape[:2]

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_img = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        result = landmarker.detect(mp_img)

        # Decay trail
        trail = (trail * 0.78).astype(np.uint8)

        palette = PALETTES[palette_idx % len(PALETTES)]

        hands_tips = []   # list of dicts: {tip_idx: (x,y)}
        if result.hand_landmarks:
            for lm in result.hand_landmarks:
                tips = {}
                for ti in TIPS:
                    tips[ti] = (int(lm[ti].x * w), int(lm[ti].y * h))
                hands_tips.append(tips)

        two_hands = len(hands_tips) == 2

        if two_hands:
            left_tips  = hands_tips[0]
            right_tips = hands_tips[1]

            # All fingertip pairs: left finger i ↔ right finger j
            pairs = []
            for li, lt in enumerate(TIPS):
                for ri, rt in enumerate(TIPS):
                    p1 = left_tips[lt]
                    p2 = right_tips[rt]
                    d  = dist2d(p1, p2)
                    pairs.append((li * 5 + ri, p1, p2, d,
                                  palette[li % len(palette)],
                                  palette[ri % len(palette)]))

            # ── Midpoint for spirograph / constellation centre ──
            all_pts = list(left_tips.values()) + list(right_tips.values())
            mid_x = int(sum(p[0] for p in all_pts) / len(all_pts))
            mid_y = int(sum(p[1] for p in all_pts) / len(all_pts))
            mid   = (mid_x, mid_y)

            # Hand spread (for sizing effects)
            spread = int(max(dist2d(left_tips[TIPS[0]], right_tips[TIPS[0]]),
                             dist2d(left_tips[TIPS[4]], right_tips[TIPS[4]])) / 2)
            spread = max(60, min(spread, 300))

            if mode == 1:
                # ── PLASMA STREAMS ──────────────────────────────────────────
                # Only connect matching fingers (tip-to-tip) + cross-links
                connect_pairs = [(0, palette[0]), (1, palette[1]),
                                 (2, palette[2]), (3, palette[3]), (4, palette[4])]
                for fi, col in connect_pairs:
                    p1 = left_tips[TIPS[fi]]
                    p2 = right_tips[TIPS[fi]]
                    d  = dist2d(p1, p2)
                    # Draw the guide beam
                    intensity = max(0, 1 - d / 600)
                    beam_col = tuple(int(c * intensity * 0.35) for c in col)
                    draw_glowing_line(trail, p1, p2, beam_col, thickness=1, glow_layers=2)

                    # Manage particle pool
                    if fi not in plasma_pools:
                        plasma_pools[fi] = []
                    pool = plasma_pools[fi]
                    # Spawn
                    if len(pool) < MAX_PLASMA and frame_count % 2 == 0:
                        pool.append(PlasmaParticle(p1, p2, col))
                    # Update positions
                    alive = []
                    for p in pool:
                        p.p1 = p1; p.p2 = p2   # track moving fingers
                        if p.update():
                            p.draw(trail)
                            alive.append(p)
                    plasma_pools[fi] = alive

                # Glow dots on fingertips
                for fi, col in connect_pairs:
                    glow_r = int(8 + 4 * math.sin(t * 0.1 + fi))
                    draw_glow_circle(trail, left_tips[TIPS[fi]],  glow_r, col)
                    draw_glow_circle(trail, right_tips[TIPS[fi]], glow_r, col)


            elif mode == 2:
                # ── LIGHTNING ARCS ──────────────────────────────────────────
                for fi in range(5):
                    p1  = left_tips[TIPS[fi]]
                    p2  = right_tips[TIPS[fi]]
                    col = palette[fi]
                    key = fi

                    # Regenerate arc every few frames (flicker effect)
                    if frame_count % max(1, (fi + 2)) == 0 or key not in lightning_cache:
                        segs = random.randint(8, 20)
                        jit  = random.randint(10, 35)
                        lightning_cache[key] = make_lightning(p1, p2, segs, jit)

                    render_lightning(trail, lightning_cache[key], col)

                    # Endpoint flash
                    flash = int(6 + 4 * abs(math.sin(t * 0.3 + fi)))
                    cv2.circle(trail, p1, flash, col, -1, cv2.LINE_AA)
                    cv2.circle(trail, p2, flash, col, -1, cv2.LINE_AA)

                    # Random branch arcs
                    if frame_count % 8 == fi:
                        branch_start_t = random.uniform(0.2, 0.8)
                        bx = int(lerp(p1[0], p2[0], branch_start_t))
                        by = int(lerp(p1[1], p2[1], branch_start_t))
                        end_x = bx + random.randint(-60, 60)
                        end_y = by + random.randint(-60, 60)
                        bpts = make_lightning((bx, by), (end_x, end_y), 5, 15)
                        render_lightning(trail, bpts, tuple(c//2 for c in col))


            elif mode == 3:
                # ── SPIROGRAPH WEB ──────────────────────────────────────────
                for fi in range(5):
                    col = palette[fi]
                    c1  = left_tips[TIPS[fi]]
                    c2  = right_tips[TIPS[fi]]
                    for centre, r_scale in [(c1, 0.5), (c2, 0.5), (mid, 1.0)]:
                        spiro.r1 = 0.4 + 0.25 * math.sin(t * 0.02 + fi)
                        spiro.k  = 3 + fi
                        spiro.d  = 0.4 + 0.4 * abs(math.sin(t * 0.015))
                        spiro.draw(trail, centre, int(spread * r_scale), col, t + fi * 0.7)

                # Connect fingertips with glowing lines
                for fi in range(5):
                    draw_glowing_line(trail,
                                      left_tips[TIPS[fi]], right_tips[TIPS[fi]],
                                      palette[fi], thickness=1, glow_layers=2)

            elif mode == 4:
                # ── CONSTELLATION NET ───────────────────────────────────────
                # Seed nodes near each fingertip
                all_hand_pts = list(left_tips.values()) + list(right_tips.values())
                if frame_count % 4 == 0:
                    seed_pt = random.choice(all_hand_pts)
                    constellation.seed(seed_pt, spread // 2, n=2)
                constellation.update((w, h))
                constellation.draw(trail, palette[frame_count % 5], all_hand_pts)

                # Draw fingertip-to-fingertip lines
                for fi in range(5):
                    p1  = left_tips[TIPS[fi]]
                    p2  = right_tips[TIPS[fi]]
                    col = palette[fi]
                    draw_glowing_line(trail, p1, p2, col, thickness=1, glow_layers=1)
                    cv2.circle(trail, p1, 5, col, -1, cv2.LINE_AA)
                    cv2.circle(trail, p2, 5, col, -1, cv2.LINE_AA)

        # ── Composite trail onto frame ──────────────────────────────────────
        # Additive blend: frame + trail (clamped)
        composite = np.clip(frame.astype(np.int32) + trail.astype(np.int32), 0, 255).astype(np.uint8)

        # ── HUD ────────────────────────────────────────────────────────────
        mode_names = {1:"Plasma Streams", 2:"Lightning Arcs",
                      3:"Spirograph Web", 4:"Constellation Net"}
        status = f"Mode {mode}: {mode_names[mode]}  |  SPACE=new pattern  Q=quit"
        cv2.putText(composite, status, (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 255), 2)

        if not two_hands:
            msg = "Raise both hands, fingertips facing each other"
            cv2.putText(composite, msg, (10, h - 20),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (100, 150, 255), 2)

        cv2.imshow("Finger Connect AR", composite)

        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break
        elif key == ord(' '):
            palette_idx = (palette_idx + 1) % len(PALETTES)
            spiro.randomise()
            constellation.nodes.clear()
            plasma_pools.clear()
            lightning_cache.clear()
        elif key == ord('1'): mode = 1; plasma_pools.clear()
        elif key == ord('2'): mode = 2; lightning_cache.clear()
        elif key == ord('3'): mode = 3; spiro.randomise()
        elif key == ord('4'): mode = 4; constellation.nodes.clear()

        t += 1
        frame_count += 1

    cap.release()
    cv2.destroyAllWindows()
    landmarker.close()


if __name__ == "__main__":
    main()
