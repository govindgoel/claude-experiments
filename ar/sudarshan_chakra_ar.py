import cv2
import mediapipe as mp
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision as mp_vision
from mediapipe.tasks.python.vision.hand_landmarker import HandLandmarkerResult
import numpy as np
import math
import os
import random

MODEL_PATH = os.path.join(os.path.dirname(__file__), "hand_landmarker.task")

# ── Helpers ───────────────────────────────────────────────────────────────────

def rotate_bgra(img: np.ndarray, angle: float) -> np.ndarray:
    h, w = img.shape[:2]
    M = cv2.getRotationMatrix2D((w / 2, h / 2), angle, 1.0)
    return cv2.warpAffine(img, M, (w, h), flags=cv2.INTER_LINEAR,
                          borderMode=cv2.BORDER_CONSTANT, borderValue=(0, 0, 0, 0))


def make_lateral_disc(img: np.ndarray, finger_angle_deg: float, spin_angle: float,
                      squish: float = 0.18) -> np.ndarray:
    """
    Transform a face-on circular chakra so it looks like a flat disc
    spinning laterally on the finger.

    Strategy:
      1. Spin the chakra pattern (spin_angle) — disc rotating around finger axis
      2. Squish vertically by `squish` factor — disc seen edge-on from front
      3. Rotate squished ellipse so the thin axis aligns with the finger direction
    """
    h, w = img.shape[:2]
    cx, cy = w / 2, h / 2

    # Step 1 — spin the chakra face
    M_spin = cv2.getRotationMatrix2D((cx, cy), spin_angle, 1.0)
    spun = cv2.warpAffine(img, M_spin, (w, h), flags=cv2.INTER_LINEAR,
                          borderMode=cv2.BORDER_CONSTANT, borderValue=(0, 0, 0, 0))

    # Step 2 — squish vertically (collapse the disc into a thin ellipse)
    # Translate so top edge stays centred during squish
    M_squish = np.float32([
        [1, 0, 0],
        [0, squish, cy * (1.0 - squish)]
    ])
    squished = cv2.warpAffine(spun, M_squish, (w, h), flags=cv2.INTER_LINEAR,
                              borderMode=cv2.BORDER_CONSTANT, borderValue=(0, 0, 0, 0))

    # Step 3 — rotate so thin axis aligns with finger direction
    # finger_angle_deg is measured from positive-X; the thin dim is now vertical (90°),
    # so we rotate by (finger_angle_deg - 90) to align thin dim → finger.
    tilt = finger_angle_deg - 90.0
    M_tilt = cv2.getRotationMatrix2D((cx, cy), tilt, 1.0)
    result = cv2.warpAffine(squished, M_tilt, (w, h), flags=cv2.INTER_LINEAR,
                            borderMode=cv2.BORDER_CONSTANT, borderValue=(0, 0, 0, 0))
    return result


def overlay_bgra(bg: np.ndarray, fg: np.ndarray, cx: int, cy: int):
    oh, ow = fg.shape[:2]
    x1, y1 = cx - ow // 2, cy - oh // 2
    x2, y2 = x1 + ow, y1 + oh
    bx1 = max(x1, 0); by1 = max(y1, 0)
    bx2 = min(x2, bg.shape[1]); by2 = min(y2, bg.shape[0])
    ox1, oy1 = bx1 - x1, by1 - y1
    ox2, oy2 = ox1 + (bx2 - bx1), oy1 + (by2 - by1)
    if bx2 <= bx1 or by2 <= by1:
        return
    roi = bg[by1:by2, bx1:bx2]
    src = fg[oy1:oy2, ox1:ox2]
    alpha = src[:, :, 3:4].astype(np.float32) / 255.0
    roi[:] = (src[:, :, :3] * alpha + roi * (1 - alpha)).astype(np.uint8)


# ── Authentic Sudarshan Chakra ────────────────────────────────────────────────

def make_chakra(size: int) -> np.ndarray:
    img = np.zeros((size, size, 4), dtype=np.uint8)
    cx = cy = size // 2

    R = size // 2 - 2
    # Ring radii proportions (from outer to inner)
    r1 = R          # outermost serrated edge
    r2 = int(R * 0.88)
    r3 = int(R * 0.78)
    r4 = int(R * 0.62)
    r5 = int(R * 0.48)
    r6 = int(R * 0.30)
    r7 = int(R * 0.14)  # hub gem

    GOLD1  = (20,  190, 255, 255)   # bright gold
    GOLD2  = (0,   150, 210, 255)   # deep gold
    AMBER  = (10,  170, 240, 255)
    WHITE  = (220, 240, 255, 255)
    DARK   = (0,    80, 140, 220)

    # ── Background disc fill (dark amber base) ──
    cv2.circle(img, (cx, cy), r2, (0, 100, 160, 230), -1, cv2.LINE_AA)

    # ── Spoke fills (16 petals between r5 and r3) ──
    spokes = 16
    for i in range(spokes):
        a1 = 2*math.pi*i/spokes + math.pi/spokes*0.12
        a2 = 2*math.pi*i/spokes + math.pi/spokes*0.88
        steps = 12
        pts = []
        for s in range(steps+1):
            a = a1 + (a2-a1)*s/steps
            pts.append([int(cx+r5*math.cos(a)), int(cy+r5*math.sin(a))])
        for s in range(steps, -1, -1):
            a = a1 + (a2-a1)*s/steps
            pts.append([int(cx+r3*math.cos(a)), int(cy+r3*math.sin(a))])
        cv2.fillPoly(img, [np.array(pts, np.int32)], GOLD2)

    # ── 32 narrow outer spokes (r5 → r2) ──
    for i in range(32):
        a1 = 2*math.pi*i/32 + math.pi/32*0.2
        a2 = 2*math.pi*i/32 + math.pi/32*0.8
        steps = 8
        pts = []
        for s in range(steps+1):
            a = a1+(a2-a1)*s/steps
            pts.append([int(cx+r5*math.cos(a)), int(cy+r5*math.sin(a))])
        for s in range(steps, -1, -1):
            a = a1+(a2-a1)*s/steps
            pts.append([int(cx+r2*math.cos(a)), int(cy+r2*math.sin(a))])
        cv2.fillPoly(img, [np.array(pts, np.int32)], (*AMBER[:3], 150))

    # ── Concentric rings ──
    for r, thick, col in [
        (r2, 5, GOLD1), (r3, 3, GOLD2), (r4, 2, AMBER),
        (r5, 3, GOLD1), (r6, 2, GOLD2),
    ]:
        cv2.circle(img, (cx, cy), r, col, thick, cv2.LINE_AA)

    # ── Spoke lines ──
    for i in range(spokes):
        a = 2*math.pi*i/spokes
        x1_ = int(cx + r6*math.cos(a)); y1_ = int(cy + r6*math.sin(a))
        x2_ = int(cx + r4*math.cos(a)); y2_ = int(cy + r4*math.sin(a))
        cv2.line(img, (x1_, y1_), (x2_, y2_), GOLD1, 2, cv2.LINE_AA)

    # ── Outer serrated teeth ──
    teeth = 48
    for i in range(teeth):
        a1 = 2*math.pi*i/teeth
        amid = 2*math.pi*(i+0.5)/teeth
        a2 = 2*math.pi*(i+1)/teeth
        p1 = (int(cx+r2*math.cos(a1)),    int(cy+r2*math.sin(a1)))
        p2 = (int(cx+(r1+2)*math.cos(amid)), int(cy+(r1+2)*math.sin(amid)))
        p3 = (int(cx+r2*math.cos(a2)),    int(cy+r2*math.sin(a2)))
        cv2.fillPoly(img, [np.array([p1,p2,p3], np.int32)], GOLD1)

    # ── Gem hub ──
    cv2.circle(img, (cx, cy), r6, GOLD2, -1, cv2.LINE_AA)
    cv2.circle(img, (cx, cy), r7, WHITE, -1, cv2.LINE_AA)
    # jewel facets
    for i in range(8):
        a = 2*math.pi*i/8
        x_ = int(cx + r7*0.6*math.cos(a)); y_ = int(cy + r7*0.6*math.sin(a))
        cv2.line(img, (cx, cy), (x_, y_), (*GOLD1[:3], 180), 1, cv2.LINE_AA)
    cv2.circle(img, (cx, cy), r7, GOLD1, 2, cv2.LINE_AA)
    cv2.circle(img, (cx, cy), r6, GOLD1, 3, cv2.LINE_AA)

    # ── Edge highlight ──
    cv2.circle(img, (cx, cy), r1, GOLD1, 2, cv2.LINE_AA)

    return img


# ── Divine Aura / Glow layer ──────────────────────────────────────────────────

def make_aura(size: int, t: float) -> np.ndarray:
    """Pulsing cosmic aura — purple/gold radial gradient with light rays."""
    # Aura canvas is only slightly larger than the chakra itself
    pad = int(size * 0.5)
    total = size + pad * 2
    img = np.zeros((total, total, 4), dtype=np.uint8)
    cx = cy = total // 2
    r_chakra = size // 2

    # Radial glow layers — tight around the disc
    layers = [
        (int(r_chakra * 1.45), (180, 50, 220), 30),   # outer purple
        (int(r_chakra * 1.28), (200, 80, 255), 45),
        (int(r_chakra * 1.15), (150, 100, 255), 60),
        (int(r_chakra * 1.06), (80,  160, 255), 80),
        (int(r_chakra * 1.01), (60,  200, 255), 100),
    ]
    for radius, color_bgr, base_alpha in layers:
        pulse = base_alpha + int(10 * math.sin(t * 0.08))
        for dr in range(0, max(1, radius // 5)):
            a = max(0, int(pulse * (1 - dr / (radius / 5))))
            cv2.circle(img, (cx, cy), radius - dr, (*color_bgr, a), 1, cv2.LINE_AA)

    # Short light rays confined within the aura canvas
    ray_angle_offset = t * 0.3
    for i in range(8):
        angle = math.radians(i * 45 + ray_angle_offset)
        length = int(r_chakra * (1.3 + 0.15 * math.sin(t * 0.05 + i)))
        brightness = int(40 + 20 * math.sin(t * 0.06 + i * 0.5))
        for offset in range(-2, 3):
            a_off = angle + math.radians(offset * 0.5)
            xe = int(cx + length * math.cos(a_off))
            ye = int(cy + length * math.sin(a_off))
            alpha_ray = max(0, brightness - abs(offset) * 10)
            cv2.line(img, (cx, cy), (xe, ye), (200, 200, 255, alpha_ray), 1, cv2.LINE_AA)

    return img


# ── Particle sparkles ─────────────────────────────────────────────────────────

class Particle:
    def __init__(self, cx: int, cy: int, radius: int):
        self.reset(cx, cy, radius)

    def reset(self, cx: int, cy: int, radius: int):
        angle = random.uniform(0, 2 * math.pi)
        # Spawn at rim of chakra only
        dist  = random.uniform(radius * 0.85, radius * 1.15)
        self.x = cx + dist * math.cos(angle)
        self.y = cy + dist * math.sin(angle)
        self.vx = random.uniform(-0.5, 0.5)
        self.vy = random.uniform(-1.2, -0.2)
        self.life = random.randint(15, 35)
        self.max_life = self.life
        self.size = random.randint(1, 3)
        self.color = random.choice([
            (50, 200, 255), (100, 150, 255), (200, 180, 255), (255, 255, 200)
        ])

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.life -= 1

    def draw(self, frame: np.ndarray):
        alpha = self.life / self.max_life
        col = tuple(int(c * alpha) for c in self.color)
        px, py = int(self.x), int(self.y)
        if 0 <= px < frame.shape[1] and 0 <= py < frame.shape[0]:
            cv2.circle(frame, (px, py), self.size, col, -1, cv2.LINE_AA)
            # sparkle cross
            if self.size >= 3:
                cv2.line(frame, (px-self.size, py), (px+self.size, py),
                         tuple(int(c * alpha * 0.7) for c in self.color), 1)
                cv2.line(frame, (px, py-self.size), (px, py+self.size),
                         tuple(int(c * alpha * 0.7) for c in self.color), 1)


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    base_opts = mp_python.BaseOptions(model_asset_path=MODEL_PATH)
    opts = mp_vision.HandLandmarkerOptions(
        base_options=base_opts, num_hands=1,
        min_hand_detection_confidence=0.6,
        min_hand_presence_confidence=0.6,
        min_tracking_confidence=0.5,
    )
    landmarker = mp_vision.HandLandmarker.create_from_options(opts)

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Cannot open camera.")
        return

    chakra_cache: dict[int, np.ndarray] = {}
    angle = 0.0
    SPIN_SPEED = 3.5
    frame_count = 0

    # Particles
    particles: list[Particle] = []
    MAX_PARTICLES = 30
    last_cx = last_cy = last_r = 0

    print("Sudarshan Chakra AR  |  Q to quit")

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        frame = cv2.flip(frame, 1)
        h, w = frame.shape[:2]

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_img = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        result: HandLandmarkerResult = landmarker.detect(mp_img)

        hand_detected = bool(result.hand_landmarks)

        if hand_detected:
            lm = result.hand_landmarks[0]
            dip = lm[7]; tip = lm[8]
            dip_px = (int(dip.x * w), int(dip.y * h))
            tip_px = (int(tip.x * w), int(tip.y * h))
            cx = (dip_px[0] + tip_px[0]) // 2
            cy = (dip_px[1] + tip_px[1]) // 2
            seg = int(math.hypot(tip_px[0]-dip_px[0], tip_px[1]-dip_px[1]))
            # Chakra radius = ~1.4× the distal phalanx segment length (tight fit on finger)
            chakra_r = max(28, int(seg * 1.4))
            last_cx, last_cy, last_r = cx, cy, chakra_r

            # Finger direction angle in image (degrees, OpenCV convention)
            dx = tip_px[0] - dip_px[0]
            dy = tip_px[1] - dip_px[1]
            finger_angle_deg = math.degrees(math.atan2(dy, dx))

            # ── Draw aura (compact — only 1.2× chakra size in each direction) ──
            aura = make_aura(chakra_r * 2, frame_count)
            aura_disc = make_lateral_disc(aura, finger_angle_deg, 0, squish=0.22)
            overlay_bgra(frame, aura_disc, cx, cy)

            # ── Draw chakra as lateral disc ──
            size = chakra_r * 2
            if size not in chakra_cache:
                chakra_cache[size] = make_chakra(size)
            disc = make_lateral_disc(chakra_cache[size], finger_angle_deg, angle)
            overlay_bgra(frame, disc, cx, cy)

            # ── Spawn particles ──
            if frame_count % 2 == 0 and len(particles) < MAX_PARTICLES:
                particles.append(Particle(cx, cy, chakra_r))

        # ── Update & draw particles ──
        alive = []
        for p in particles:
            p.update()
            if p.life > 0:
                p.draw(frame)
                alive.append(p)
        particles = alive

        angle = (angle + SPIN_SPEED) % 360
        frame_count += 1

        # ── Subtle vignette (cosmic feel) ──
        vignette = np.zeros_like(frame, dtype=np.float32)
        rows, cols = frame.shape[:2]
        Y, X = np.ogrid[:rows, :cols]
        dist_from_center = np.sqrt((X - cols/2)**2 + (Y - rows/2)**2)
        max_dist = math.sqrt((cols/2)**2 + (rows/2)**2)
        mask = (dist_from_center / max_dist) ** 2.2
        mask = np.clip(mask * 0.55, 0, 1)
        frame = (frame.astype(np.float32) * (1 - mask[:, :, np.newaxis])).astype(np.uint8)

        cv2.putText(frame, "Sudarshan Chakra  |  Q to quit",
                    (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (80, 160, 255), 2)
        cv2.imshow("Sudarshan Chakra AR", frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()
    landmarker.close()


if __name__ == "__main__":
    main()
