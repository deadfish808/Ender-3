#!/usr/bin/env python3
"""Procedural pixel-art asset generator for Medieval Zombie Survival.

Generates every sprite used by the game into ../assets/.
Run:  python3 generate_assets.py
Requires: Pillow
"""
import math
import os
import random

from PIL import Image

random.seed(1337)

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
ASSETS = os.path.join(ROOT, "assets")

OUTLINE = (24, 18, 28, 255)

# ---------------------------------------------------------------- palette ---
GRASS = [(46, 74, 38), (58, 92, 46), (72, 110, 54), (92, 132, 64)]
DIRT = [(74, 52, 34), (94, 68, 44), (114, 84, 54), (134, 102, 66)]
SAND = [(150, 126, 84), (172, 148, 102), (192, 168, 120), (210, 188, 140)]
WATER = [(28, 52, 86), (36, 66, 106), (46, 82, 128), (90, 130, 168)]
STONE = [(72, 72, 80), (94, 94, 102), (118, 118, 126), (142, 142, 150)]
WOOD = [(78, 54, 32), (102, 72, 42), (126, 92, 54), (150, 114, 70)]
LEAF = [(30, 58, 34), (42, 78, 42), (56, 98, 52), (74, 120, 62)]
PINE = [(24, 50, 40), (32, 66, 50), (42, 84, 60), (56, 102, 72)]
SKIN = [(150, 102, 74), (188, 134, 96), (216, 162, 118)]
ZSKIN = [(74, 96, 56), (98, 122, 70), (122, 146, 88)]
IRON = [(96, 100, 110), (140, 144, 154), (186, 190, 200)]


def new(w, h):
    return Image.new("RGBA", (w, h), (0, 0, 0, 0))


def px(im, x, y, c):
    x, y = int(x), int(y)
    if 0 <= x < im.width and 0 <= y < im.height:
        im.putpixel((x, y), c)


def rect(im, x0, y0, x1, y1, c):
    for y in range(int(y0), int(y1) + 1):
        for x in range(int(x0), int(x1) + 1):
            px(im, x, y, c)


def disc(im, cx, cy, rx, ry, c, prob=1.0, rng=None):
    rng = rng or random
    for y in range(int(cy - ry), int(cy + ry) + 1):
        for x in range(int(cx - rx), int(cx + rx) + 1):
            dx = (x - cx) / max(rx, 0.001)
            dy = (y - cy) / max(ry, 0.001)
            if dx * dx + dy * dy <= 1.0 and rng.random() <= prob:
                px(im, x, y, c)


def line(im, x0, y0, x1, y1, c, w=1):
    steps = int(max(abs(x1 - x0), abs(y1 - y0))) + 1
    for i in range(steps + 1):
        t = i / max(steps, 1)
        x = x0 + (x1 - x0) * t
        y = y0 + (y1 - y0) * t
        if w == 1:
            px(im, round(x), round(y), c)
        else:
            disc(im, x, y, w / 2, w / 2, c)


def shade(c, f):
    out = tuple(max(0, min(255, int(v * f))) for v in c[:3])
    return out + tuple(c[3:])


def outline(im, color=OUTLINE):
    src = im.load()
    out = im.copy()
    for y in range(im.height):
        for x in range(im.width):
            if src[x, y][3] != 0:
                continue
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nx, ny = x + dx, y + dy
                if 0 <= nx < im.width and 0 <= ny < im.height and src[nx, ny][3] > 60:
                    out.putpixel((x, y), color)
                    break
    return out


def save(im, rel):
    path = os.path.join(ASSETS, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    im.save(path)
    print("wrote", rel)


# ----------------------------------------------------------------- terrain --
TILE_W, TILE_H = 64, 32


def in_diamond(x, y, w=TILE_W, h=TILE_H):
    nx = (x + 0.5) / w * 2 - 1
    ny = (y + 0.5) / h * 2 - 1
    return abs(nx) + abs(ny) <= 1.0


def value_noise(x, y, seed, scale=0.35):
    n = math.sin(x * 1.31 * scale + seed * 12.9) + math.sin(y * 1.77 * scale + seed * 7.1)
    n += math.sin((x + y) * 0.83 * scale + seed * 3.7)
    return (n / 3.0 + 1.0) / 2.0


def terrain_tile(ramp, seed, tufts=0, tuft_color=None, waves=False):
    im = new(TILE_W, TILE_H)
    rng = random.Random(seed)
    for y in range(TILE_H):
        for x in range(TILE_W):
            if not in_diamond(x, y):
                continue
            n = value_noise(x, y, seed)
            n += (rng.random() - 0.5) * 0.22
            if n < 0.30:
                c = ramp[0]
            elif n < 0.55:
                c = ramp[1]
            elif n < 0.82:
                c = ramp[2]
            else:
                c = ramp[3]
            # bottom edges read darker, top edges catch light
            edge = abs((x + 0.5) / TILE_W * 2 - 1) + abs((y + 0.5) / TILE_H * 2 - 1)
            if edge > 0.86:
                c = shade(c, 0.78 if y > TILE_H / 2 else 1.12)
            px(im, x, y, c + (255,))
    for _ in range(tufts):
        tx = rng.randint(14, TILE_W - 14)
        ty = rng.randint(8, TILE_H - 8)
        if in_diamond(tx, ty):
            col = tuft_color or ramp[3]
            px(im, tx, ty, col + (255,))
            px(im, tx, ty - 1, col + (255,))
            if rng.random() < 0.5:
                px(im, tx + 1, ty, shade(col + (255,), 0.85))
    if waves:
        for _ in range(5):
            wx = rng.randint(10, TILE_W - 18)
            wy = rng.randint(6, TILE_H - 7)
            if in_diamond(wx, wy) and in_diamond(wx + 6, wy):
                for i in range(rng.randint(4, 7)):
                    px(im, wx + i, wy, WATER[3] + (255,))
    return im


def build_terrain_atlas():
    # atlas layout (col,row): see World.gd TILES mapping
    cells = [
        terrain_tile(GRASS, 1, tufts=7),
        terrain_tile(GRASS, 2, tufts=5),
        terrain_tile(GRASS, 3, tufts=9),
        terrain_tile(DIRT, 4),
        terrain_tile(DIRT, 5),
        terrain_tile(SAND, 6),
        terrain_tile(WATER, 7, waves=True),
        terrain_tile(WATER, 8, waves=True),
        terrain_tile(STONE, 9),
        terrain_tile(STONE, 10),
    ]
    cols = 5
    rows = (len(cells) + cols - 1) // cols
    atlas = new(cols * TILE_W, rows * TILE_H)
    for i, c in enumerate(cells):
        atlas.paste(c, ((i % cols) * TILE_W, (i // cols) * TILE_H))
    save(atlas, "tiles/terrain_atlas.png")


# ------------------------------------------------------------------- props --
def draw_canopy(im, cx, cy, r, ramp, rng):
    blobs = [(cx, cy, r, r * 0.8)]
    for _ in range(4):
        a = rng.random() * math.tau
        blobs.append((cx + math.cos(a) * r * 0.55, cy + math.sin(a) * r * 0.45,
                      r * rng.uniform(0.45, 0.7), r * rng.uniform(0.4, 0.6)))
    for bx, by, brx, bry in blobs:
        disc(im, bx, by, brx, bry, ramp[1] + (255,))
    # shadow lower-right, light upper-left
    for bx, by, brx, bry in blobs:
        disc(im, bx + brx * 0.3, by + bry * 0.35, brx * 0.7, bry * 0.6, ramp[0] + (255,), prob=0.55, rng=rng)
        disc(im, bx - brx * 0.3, by - bry * 0.4, brx * 0.55, bry * 0.5, ramp[2] + (255,), prob=0.6, rng=rng)
        disc(im, bx - brx * 0.35, by - bry * 0.5, brx * 0.3, bry * 0.3, ramp[3] + (255,), prob=0.5, rng=rng)
    # leaf speckles
    for _ in range(int(r * r * 0.25)):
        a = rng.random() * math.tau
        d = rng.random()
        x = cx + math.cos(a) * r * d
        y = cy + math.sin(a) * r * 0.8 * d
        px(im, x, y, ramp[rng.randint(1, 3)] + (255,))


def tree_oak(seed):
    im = new(64, 96)
    rng = random.Random(seed)
    # trunk, feet at (32, 92)
    rect(im, 29, 58, 34, 91, WOOD[1] + (255,))
    rect(im, 33, 58, 34, 91, WOOD[0] + (255,))
    rect(im, 29, 58, 29, 91, WOOD[2] + (255,))
    # root flare
    rect(im, 27, 88, 36, 91, WOOD[1] + (255,))
    px(im, 27, 88, WOOD[2] + (255,))
    draw_canopy(im, 32, 36, 21, LEAF, rng)
    return outline(im)


def tree_pine(seed):
    im = new(64, 96)
    rng = random.Random(seed)
    rect(im, 30, 70, 33, 91, WOOD[0] + (255,))
    rect(im, 30, 70, 30, 91, WOOD[2] + (255,))
    # stacked triangle tiers
    tiers = [(20, 26, 86), (32, 22, 78), (44, 18, 68), (56, 13, 56), (66, 8, 40)]
    for ty, half, _ in tiers:
        pass
    layers = [(78, 24), (62, 20), (47, 16), (33, 12), (21, 8)]
    for base_y, half in layers:
        top_y = base_y - int(half * 1.1)
        for y in range(top_y, base_y + 1):
            t = (y - top_y) / max(base_y - top_y, 1)
            w = int(half * t)
            for x in range(32 - w, 33 + w):
                c = PINE[1]
                if x > 32 + w * 0.35:
                    c = PINE[0]
                elif x < 32 - w * 0.3 and y < base_y - 2:
                    c = PINE[2]
                if rng.random() < 0.08:
                    c = PINE[3]
                px(im, x, y, c + (255,))
    return outline(im)


def rock(seed, big=True):
    w, h = (48, 36) if big else (32, 24)
    im = new(w, h)
    rng = random.Random(seed)
    cx, cy = w // 2, h - h // 3
    disc(im, cx, cy, w * 0.42, h * 0.34, STONE[1] + (255,))
    disc(im, cx - w * 0.18, cy - h * 0.18, w * 0.26, h * 0.24, STONE[2] + (255,))
    disc(im, cx + w * 0.2, cy + h * 0.05, w * 0.2, h * 0.2, STONE[0] + (255,), prob=0.8, rng=rng)
    disc(im, cx - w * 0.22, cy - h * 0.26, w * 0.12, h * 0.1, STONE[3] + (255,), prob=0.7, rng=rng)
    for _ in range(6):
        x = rng.randint(int(w * 0.2), int(w * 0.8))
        y = rng.randint(int(h * 0.35), int(h * 0.85))
        px(im, x, y, STONE[0] + (255,))
        px(im, x + 1, y, STONE[0] + (255,))
    return outline(im)


def berry_bush(with_berries=True, seed=5):
    im = new(40, 30)
    rng = random.Random(seed)
    draw_canopy(im, 20, 18, 10, LEAF, rng)
    if with_berries:
        for _ in range(8):
            x = 20 + rng.randint(-9, 9)
            y = 17 + rng.randint(-6, 5)
            px(im, x, y, (182, 40, 48, 255))
            px(im, x + 1, y, (216, 70, 70, 255))
    return outline(im)


def mushroom_patch(seed=9):
    im = new(26, 18)
    rng = random.Random(seed)
    for i, (mx, my, r) in enumerate([(8, 12, 4), (17, 13, 3), (13, 9, 3)]):
        rect(im, mx - 1, my, mx, my + 4, (214, 200, 180, 255))
        disc(im, mx, my - 1, r, r * 0.6, (160, 58, 44, 255))
        disc(im, mx - 1, my - 2, r * 0.5, r * 0.35, (196, 84, 64, 255), prob=0.8, rng=rng)
        px(im, mx, my - 2, (230, 220, 210, 255))
    return outline(im)


def ruin_wall(seed):
    im = new(64, 64)
    rng = random.Random(seed)
    draw_iso_block(im, height=int(18 + rng.random() * 14), ramp=STONE, pattern="stone",
                   jagged=True, rng=rng, moss=True)
    return outline(im)


# ------------------------------------------------------------- iso blocks ---
def draw_iso_block(im, height, ramp, pattern, jagged=False, rng=None, moss=False,
                   door_hole=False, door_open=False):
    """Draw an isometric block with a 64x32 diamond footprint, faces extruded
    upward by `height`. Image must be 64x64; footprint occupies bottom 32 rows."""
    rng = rng or random.Random(1)
    base_top = im.height - TILE_H  # y of footprint diamond top
    jag = [0] * 64
    if jagged:
        v = 0
        for x in range(64):
            if rng.random() < 0.2:
                v = rng.randint(0, 10)
            jag[x] = v

    def face_color(x, y, left):
        base = ramp[2] if left else ramp[1]
        if pattern == "stone":
            # coursed blocks
            row = (y // 6)
            off = (row % 2) * 5
            if (y % 6) == 0 or ((x + off) % 11) == 0:
                return shade(base + (255,), 0.62)
            n = value_noise(x, y, 3.0)
            c = base + (255,)
            if n > 0.72:
                c = ramp[3] + (255,)
            elif n < 0.3:
                c = shade(c, 0.85)
            return c
        else:  # wood planks
            if (y % 5) == 0:
                return shade(base + (255,), 0.6)
            n = value_noise(x * 2.0, y, 7.0)
            c = base + (255,)
            if n > 0.75:
                c = ramp[3] + (255,)
            elif n < 0.28:
                c = ramp[0] + (255,)
            return c

    # vertical faces: for each column x of the footprint diamond, the face
    # spans from (top edge of diamond at x) - height .. (bottom edge at x)
    for x in range(64):
        nx = (x + 0.5) / 64 * 2 - 1  # -1..1
        half = (1 - abs(nx)) * (TILE_H / 2)  # vertical half-extent of diamond
        cy = base_top + TILE_H / 2
        y_bot = cy + half
        h = max(0, height - jag[x])
        y_top = cy - half if x in (0, 63) else cy + half - 0.001  # placeholder
        # front faces are the *lower* edges of the diamond
        y_face_top = cy + half - h - half * 2  # top of face follows upper edge - height
        # Simpler: extrude the whole diamond column upward
        y0 = cy - half - h
        for y in range(int(math.ceil(y0)), int(y_bot) + 1):
            if y < int(math.ceil(y0)) + int(half * 2):
                pass
            left = x < 32
            yy = y - int(y0)
            c = face_color(x, yy, left)
            px(im, x, y, c)
    # top face: diamond at elevation `height`
    for y in range(TILE_H):
        for x in range(64):
            if in_diamond(x, y):
                h = height - jag[x]
                n = value_noise(x, y, 11.0)
                c = ramp[3] if n > 0.6 else ramp[2]
                if pattern == "wood" and ((x + y * 2) % 9) == 0:
                    c = ramp[1]
                if moss and rng.random() < 0.12:
                    c = LEAF[2]
                px(im, x, base_top + y - h, c + (255,))
    # shade lower edges of footprint
    for y in range(TILE_H):
        for x in range(64):
            if in_diamond(x, y) and not in_diamond(x, y + 1):
                px(im, x, base_top + y, shade(ramp[0] + (255,), 0.8))
    if door_hole:
        # dark archway opening on the front (south) corner
        cx = 32
        for y in range(im.height - 26, im.height - 6):
            wdt = 7 if y > im.height - 22 else 5
            for x in range(cx - wdt, cx + wdt + 1):
                if door_open:
                    px(im, x, y, (0, 0, 0, 0))
                else:
                    c = WOOD[1] if (x % 4) else WOOD[0]
                    px(im, x, y, c + (255,))
        if not door_open:
            px(im, cx + 4, im.height - 16, (220, 190, 90, 255))  # handle


def wooden_wall():
    im = new(64, 64)
    draw_iso_block(im, 26, WOOD, "wood")
    return outline(im)


def stone_wall():
    im = new(64, 64)
    draw_iso_block(im, 30, STONE, "stone")
    return outline(im)


def door(open_state):
    im = new(64, 64)
    draw_iso_block(im, 28, WOOD, "wood", door_hole=True, door_open=open_state)
    return outline(im)


def barricade():
    im = new(64, 48)
    rng = random.Random(8)
    # crossed planks
    for sx, sy, ex, ey in [(8, 40, 54, 14), (10, 14, 56, 40), (4, 30, 60, 26)]:
        line(im, sx, sy, ex, ey, WOOD[1] + (255,), w=5)
        line(im, sx, sy - 2, ex, ey - 2, WOOD[2] + (255,), w=2)
    for _ in range(14):
        x = rng.randint(6, 57)
        y = rng.randint(14, 40)
        px(im, x, y, WOOD[0] + (255,))
    # nails
    for x, y in [(31, 26), (20, 32), (44, 22)]:
        px(im, x, y, IRON[2] + (255,))
    return outline(im)


def spike_trap():
    im = new(64, 40)
    rng = random.Random(4)
    # dirt base diamond
    for y in range(TILE_H):
        for x in range(64):
            if in_diamond(x, y):
                n = value_noise(x, y, 21.0)
                c = DIRT[1] if n < 0.6 else DIRT[2]
                px(im, x, y + 8, c + (255,))
    for sx, sy in [(18, 26), (28, 30), (40, 27), (33, 20), (22, 18), (44, 19), (14, 22)]:
        h = rng.randint(10, 15)
        for i in range(h):
            t = i / h
            wdt = max(0, int(2.6 * (1 - t)))
            for x in range(sx - wdt, sx + wdt + 1):
                c = IRON[1] if x <= sx else IRON[0]
                px(im, x, sy - i + 8, c + (255,))
        px(im, sx, sy - h + 8, IRON[2] + (255,))
    return outline(im)


def campfire_sheet():
    sheet = new(40 * 4, 44)
    for f in range(4):
        im = new(40, 44)
        rng = random.Random(30 + f)
        # stone ring
        for a in range(12):
            ang = a / 12 * math.tau
            x = 20 + math.cos(ang) * 13
            y = 34 + math.sin(ang) * 6
            disc(im, x, y, 2.4, 1.8, STONE[1 + (a % 2)] + (255,))
        # logs
        line(im, 12, 36, 27, 30, WOOD[1] + (255,), w=3)
        line(im, 13, 30, 28, 36, WOOD[2] + (255,), w=3)
        # flame (flickers per frame)
        fh = 16 + (f % 2) * 3 + rng.randint(0, 2)
        for i in range(fh):
            t = i / fh
            wdt = max(1, int(6 * (1 - t) * (0.8 + 0.4 * math.sin(f + i))))
            for x in range(20 - wdt, 20 + wdt + 1):
                d = abs(x - 20) / max(wdt, 1)
                if d < 0.45 and t > 0.15:
                    c = (255, 232, 120, 255)
                elif d < 0.8:
                    c = (240, 150, 40, 255)
                else:
                    c = (200, 80, 24, 255)
                px(im, x + rng.randint(-1, 1) if t > 0.6 else x, 30 - i, c)
        # embers
        for _ in range(3):
            px(im, 20 + rng.randint(-7, 7), 16 - rng.randint(0, 6), (255, 200, 90, 255))
        sheet.paste(outline(im), (f * 40, 0))
    return sheet


def workbench():
    im = new(64, 52)
    # table top diamond
    for y in range(20):
        for x in range(56):
            if in_diamond(x, y, 56, 20):
                n = value_noise(x, y, 17.0)
                c = WOOD[2] if n < 0.7 else WOOD[3]
                if ((x + y * 2) % 7) == 0:
                    c = WOOD[1]
                px(im, x + 4, y + 8, c + (255,))
    # top edge
    for y in range(20):
        for x in range(56):
            if in_diamond(x, y, 56, 20) and not in_diamond(x, y + 1, 56, 20):
                px(im, x + 4, y + 9, WOOD[0] + (255,))
                px(im, x + 4, y + 10, WOOD[1] + (255,))
    # legs
    for lx, ly in [(10, 18), (54, 18), (32, 26)]:
        rect(im, lx - 1, ly + 8, lx + 1, ly + 24, WOOD[1] + (255,))
        rect(im, lx + 1, ly + 8, lx + 1, ly + 24, WOOD[0] + (255,))
    # tools on top
    line(im, 22, 12, 30, 16, IRON[2] + (255,))  # saw
    rect(im, 38, 12, 41, 14, IRON[1] + (255,))  # hammer head
    line(im, 39, 15, 39, 19, WOOD[3] + (255,))
    return outline(im)


def chest(open_state=False):
    im = new(36, 32)
    # iso box
    draw = [(4, 14, 31, 28)]
    rect(im, 5, 16, 30, 28, WOOD[1] + (255,))
    rect(im, 5, 16, 30, 17, WOOD[2] + (255,))
    for x in range(5, 31, 6):
        line(im, x, 16, x, 28, WOOD[0] + (255,))
    # lid
    if open_state:
        rect(im, 4, 6, 31, 10, WOOD[2] + (255,))
        rect(im, 6, 12, 29, 15, (30, 24, 20, 255))  # dark interior
        px(im, 14, 13, (240, 210, 110, 255))
        px(im, 20, 14, (240, 210, 110, 255))
    else:
        rect(im, 4, 11, 31, 15, WOOD[2] + (255,))
        rect(im, 4, 11, 31, 12, WOOD[3] + (255,))
    # gold band + lock
    rect(im, 16, 11 if not open_state else 16, 19, 28, (170, 140, 60, 255))
    rect(im, 16, 18, 19, 21, (220, 190, 90, 255))
    return outline(im)


# -------------------------------------------------------------- characters --
DIRS = ["s", "e", "n"]


def draw_humanoid(im, ox, oy, facing, pose, opts):
    """Draw a 32x48 character with feet at (ox+16, oy+46).

    pose: ('idle',0) ('walk',0..3) ('attack',0..1)
    opts: dict(skin, hair, tunic, pants, hood, zombie)
    """
    skin = opts["skin"]
    tunic = opts["tunic"]
    pants = opts["pants"]
    hair = opts["hair"]
    zombie = opts.get("zombie", False)
    cx = ox + 16
    feet = oy + 46
    kind, f = pose
    lift_l = lift_r = 0
    swing = 0
    if kind == "walk":
        lift_l = [0, 2, 0, 0][f]
        lift_r = [0, 0, 0, 2][f]
        swing = [0, 1, 0, -1][f]
    hunch = 2 if zombie else 0

    leg_top = feet - 9
    body_top = leg_top - 13
    head_top = body_top - 11 + hunch

    def vrect(x0, y0, x1, y1, c):
        rect(im, x0, y0, x1, y1, c)

    # --- legs ---
    for side, lift in ((-1, lift_l), (1, lift_r)):
        lx = cx + (2 if side > 0 else -4)
        vrect(lx, leg_top, lx + 2, feet - lift, pants[1])
        vrect(lx + (2 if side > 0 else 0), leg_top, lx + 2, feet - lift, pants[0])
        # boots
        vrect(lx, feet - 2 - lift, lx + 2, feet - lift, (52, 40, 30, 255))

    # --- torso / tunic ---
    bw = 6
    vrect(cx - bw, body_top, cx + bw - 1, leg_top + 1, tunic[1])
    vrect(cx + 2, body_top, cx + bw - 1, leg_top + 1, tunic[0])      # right shadow
    vrect(cx - bw, body_top, cx - bw + 1, leg_top - 3, tunic[2])     # left light
    # belt
    vrect(cx - bw, leg_top - 2, cx + bw - 1, leg_top - 1, (60, 44, 30, 255))
    px(im, cx, leg_top - 2, (200, 170, 80, 255))  # buckle
    if zombie:
        rng = random.Random(f * 7 + (3 if facing == "e" else 5))
        for _ in range(5):
            tx = cx + rng.randint(-bw + 1, bw - 2)
            ty = rng.randint(body_top + 1, leg_top)
            px(im, tx, ty, shade(tunic[0], 0.55))
        # exposed wound
        px(im, cx - 3, body_top + 4, (140, 40, 40, 255))
        px(im, cx - 2, body_top + 4, (180, 60, 50, 255))

    # --- arms ---
    arm_y = body_top + 1
    if zombie and facing in ("s", "e"):
        # arms reaching forward/down
        if facing == "s":
            for adx in (-bw - 1, bw):
                vrect(cx + adx, arm_y + 4, cx + adx + 1, arm_y + 13 + swing, tunic[1])
                vrect(cx + adx, arm_y + 12 + swing, cx + adx + 1, arm_y + 14 + swing, skin[1])
        else:
            vrect(cx + 4, arm_y + 3, cx + 10, arm_y + 4, skin[1])
            vrect(cx + 3, arm_y + 2, cx + 6, arm_y + 3, tunic[1])
    else:
        for side in (-1, 1):
            ax = cx + (bw if side > 0 else -bw - 2)
            sw = swing * side
            if kind == "attack":
                sw = -3 if side > 0 else 1
            vrect(ax, arm_y + sw, ax + 1, arm_y + 8 + sw, tunic[1] if not zombie else tunic[0])
            vrect(ax, arm_y + 9 + sw, ax + 1, arm_y + 11 + sw, skin[1])
        if kind == "attack" and f == 1 and facing in ("s", "e"):
            # weapon swipe arm extended
            wx = cx + (bw + 2 if facing == "e" else 6)
            wy = arm_y + (2 if facing == "e" else 8)
            line(im, cx + bw, arm_y + 2, wx + 4, wy + 4, skin[1])

    # --- head ---
    hw = 4
    vrect(cx - hw, head_top, cx + hw - 1, head_top + 8, skin[1])
    vrect(cx + 2, head_top, cx + hw - 1, head_top + 8, skin[0])
    vrect(cx - hw, head_top + 1, cx - hw + 1, head_top + 6, skin[2])
    if facing == "n":
        # back of head: hair covers
        vrect(cx - hw, head_top, cx + hw - 1, head_top + 5, hair[1])
        vrect(cx + 1, head_top, cx + hw - 1, head_top + 5, hair[0])
    else:
        # hair top
        vrect(cx - hw, head_top - 1, cx + hw - 1, head_top + 1, hair[1])
        vrect(cx - hw, head_top - 1, cx - 1, head_top + 2, hair[1])
        vrect(cx + 2, head_top - 1, cx + hw - 1, head_top + 1, hair[0])
        eye = (200, 40, 40, 255) if zombie else (30, 26, 34, 255)
        if facing == "s":
            px(im, cx - 2, head_top + 4, eye)
            px(im, cx + 1, head_top + 4, eye)
            if zombie:
                px(im, cx - 1, head_top + 7, (90, 30, 30, 255))  # gaping mouth
        else:  # e profile
            px(im, cx + 2, head_top + 4, eye)
            px(im, cx + hw - 1, head_top + 5, shade(skin[0], 0.9))
    if opts.get("hood") and facing != "n":
        vrect(cx - hw - 1, head_top - 2, cx + hw, head_top + 2, tunic[1])
        vrect(cx - hw - 1, head_top + 2, cx - hw, head_top + 6, tunic[0])
        vrect(cx + hw - 1, head_top + 2, cx + hw, head_top + 6, tunic[0])


def char_sheet(opts):
    """Rows: 0..2 walk S/E/N (4 frames), 3..5 attack S/E/N (2 frames)."""
    fw, fh = 32, 48
    sheet = new(fw * 4, fh * 6)
    for row, facing in enumerate(DIRS):
        for f in range(4):
            cell = new(fw, fh)
            draw_humanoid(cell, 0, 0, facing, ("walk", f), opts)
            sheet.paste(outline(cell), (f * fw, row * fh))
    for row, facing in enumerate(DIRS):
        for f in range(2):
            cell = new(fw, fh)
            draw_humanoid(cell, 0, 0, facing, ("attack", f), opts)
            sheet.paste(outline(cell), (f * fw, (row + 3) * fh))
    return sheet


PLAYER_OPTS = dict(
    skin=[s + (255,) for s in SKIN],
    hair=[(54, 38, 26, 255), (84, 60, 38, 255)],
    tunic=[(36, 56, 88, 255), (52, 78, 116, 255), (74, 102, 142, 255)],
    pants=[(58, 46, 36, 255), (84, 68, 52, 255)],
    hood=False,
)

ZOMBIE_OPTS = dict(
    skin=[s + (255,) for s in ZSKIN],
    hair=[(40, 46, 32, 255), (58, 64, 44, 255)],
    tunic=[(56, 48, 44, 255), (78, 66, 58, 255), (98, 86, 74, 255)],
    pants=[(48, 42, 36, 255), (66, 58, 48, 255)],
    zombie=True,
)


# ------------------------------------------------------------------- items --
def icon_base():
    return new(18, 18)


def make_item_icons():
    icons = {}

    im = icon_base()  # wood
    line(im, 2, 13, 14, 5, WOOD[2] + (255,), w=3)
    line(im, 2, 12, 13, 5, WOOD[3] + (255,), w=1)
    line(im, 4, 16, 15, 9, WOOD[1] + (255,), w=3)
    px(im, 14, 5, WOOD[3] + (255,))
    icons["wood"] = im

    im = icon_base()  # stone
    disc(im, 9, 11, 6, 5, STONE[1] + (255,))
    disc(im, 7, 9, 3.4, 2.6, STONE[2] + (255,))
    px(im, 6, 8, STONE[3] + (255,))
    icons["stone"] = im

    im = icon_base()  # fiber
    for i, x in enumerate(range(4, 15, 2)):
        line(im, x, 15, x + (-2 if i % 2 else 2), 4 + (i % 3), GRASS[2 + (i % 2)] + (255,))
    icons["fiber"] = im

    im = icon_base()  # flint
    for y in range(4, 15):
        t = (y - 4) / 10
        wdt = int(4 * (1 - abs(t - 0.4) * 1.6))
        for x in range(9 - wdt, 9 + wdt + 1):
            c = (40, 42, 50, 255) if x > 8 else (70, 74, 86, 255)
            px(im, x, y, c)
    px(im, 7, 6, (110, 116, 130, 255))
    icons["flint"] = im

    im = icon_base()  # iron scrap
    for pts in [((3, 12), (8, 4), (12, 9), (7, 14))]:
        a, b, c, d = pts
        line(im, *a, *b, IRON[1] + (255,), w=3)
        line(im, *b, *c, IRON[1] + (255,), w=3)
    px(im, 8, 8, IRON[2] + (255,))
    px(im, 12, 12, IRON[0] + (255,))
    rect(im, 11, 11, 14, 14, IRON[1] + (255,))
    icons["iron_scrap"] = im

    im = icon_base()  # cloth
    rect(im, 3, 5, 14, 13, (190, 174, 142, 255))
    rect(im, 3, 5, 14, 6, (212, 198, 168, 255))
    rect(im, 3, 9, 14, 9, (160, 144, 116, 255))
    rect(im, 12, 5, 14, 13, (160, 144, 116, 255))
    icons["cloth"] = im

    im = icon_base()  # essence
    disc(im, 9, 9, 5, 5, (120, 70, 190, 255))
    disc(im, 8, 8, 3, 3, (160, 110, 230, 255))
    px(im, 7, 7, (220, 190, 255, 255))
    for x, y in [(9, 2), (16, 9), (9, 16), (2, 9)]:
        px(im, x, y, (170, 130, 240, 255))
    icons["essence"] = im

    im = icon_base()  # berries
    for bx, by in [(6, 10), (11, 9), (8, 13)]:
        disc(im, bx, by, 2.4, 2.4, (182, 40, 48, 255))
        px(im, bx - 1, by - 1, (226, 90, 90, 255))
    line(im, 9, 3, 9, 7, GRASS[1] + (255,))
    line(im, 9, 4, 13, 3, GRASS[2] + (255,))
    icons["berries"] = im

    im = icon_base()  # mushroom
    rect(im, 8, 9, 10, 14, (214, 200, 180, 255))
    disc(im, 9, 8, 5.4, 3.4, (160, 58, 44, 255))
    px(im, 7, 6, (230, 220, 210, 255))
    px(im, 11, 7, (230, 220, 210, 255))
    icons["mushroom"] = im

    im = icon_base()  # plank
    for i in range(3):
        rect(im, 3, 4 + i * 4, 15, 6 + i * 4, WOOD[2] + (255,))
        rect(im, 3, 6 + i * 4, 15, 6 + i * 4, WOOD[0] + (255,))
    icons["plank"] = im

    im = icon_base()  # rope
    disc(im, 9, 9, 5.4, 5.4, (180, 150, 100, 255))
    disc(im, 9, 9, 2.4, 2.4, (0, 0, 0, 0))
    for a in range(8):
        ang = a / 8 * math.tau
        px(im, 9 + math.cos(ang) * 4, 9 + math.sin(ang) * 4, (140, 112, 70, 255))
    icons["rope"] = im

    im = icon_base()  # arrow
    line(im, 3, 14, 13, 4, WOOD[3] + (255,))
    line(im, 13, 4, 15, 2, IRON[2] + (255,))
    px(im, 14, 2, IRON[2] + (255,))
    px(im, 15, 3, IRON[2] + (255,))
    for o in (0, 1):
        px(im, 3 + o, 12 - o, (200, 60, 60, 255))
        px(im, 5 + o, 14 - o, (200, 60, 60, 255))
    icons["arrow"] = im

    im = icon_base()  # health salve
    rect(im, 5, 7, 12, 15, (90, 140, 90, 255))
    rect(im, 5, 7, 12, 8, (120, 175, 115, 255))
    rect(im, 7, 4, 10, 6, (150, 130, 100, 255))
    px(im, 8, 11, (220, 240, 220, 255))
    px(im, 9, 11, (220, 240, 220, 255))
    px(im, 8, 10, (220, 240, 220, 255))
    px(im, 8, 12, (220, 240, 220, 255))
    icons["salve"] = im

    im = icon_base()  # stew
    disc(im, 9, 11, 6.4, 4, (120, 80, 50, 255))
    disc(im, 9, 10, 5, 2.6, (150, 100, 56, 255))
    rect(im, 3, 11, 15, 13, (190, 174, 142, 255))
    rect(im, 3, 13, 15, 13, (150, 134, 106, 255))
    for sx in (6, 11):
        px(im, sx, 5, (200, 200, 210, 200))
        px(im, sx + 1, 3, (200, 200, 210, 150))
    icons["stew"] = im

    def sword(blade, guard):
        s = icon_base()
        line(s, 5, 12, 13, 4, blade[1] + (255,), w=2)
        line(s, 6, 11, 13, 4, blade[2] + (255,))
        line(s, 3, 10, 7, 14, guard + (255,), w=2)
        line(s, 3, 14, 5, 12, WOOD[1] + (255,), w=2)
        px(s, 2, 15, (220, 190, 90, 255))
        return s

    icons["wooden_sword"] = sword(WOOD, (120, 90, 50))
    icons["iron_sword"] = sword(IRON, (190, 160, 70))

    def bow(col):
        s = icon_base()
        for t in range(20):
            ang = -math.pi / 2.4 + t / 19 * (math.pi / 1.2)
            x = 9 + math.cos(ang) * 6.4
            y = 9 + math.sin(ang) * 6.4
            px(s, x, y, col[2] + (255,))
            px(s, x + 1, y, col[1] + (255,))
        line(s, 11, 2, 11, 16, (210, 205, 190, 255))
        return s

    icons["wooden_bow"] = bow(WOOD)
    lb = bow(WOOD)
    px(lb, 4, 9, IRON[2] + (255,))
    px(lb, 5, 9, IRON[2] + (255,))
    icons["longbow"] = lb

    def staff(orb):
        s = icon_base()
        line(s, 5, 16, 12, 5, WOOD[2] + (255,), w=2)
        disc(s, 13, 4, 2.6, 2.6, orb)
        px(s, 12, 3, (255, 255, 255, 220))
        return s

    icons["apprentice_staff"] = staff((90, 140, 220, 255))
    icons["arcane_staff"] = staff((160, 90, 230, 255))

    # buildable icons (small front views)
    im = icon_base()
    for i in range(4):
        rect(im, 3 + i * 3, 4, 4 + i * 3, 14, WOOD[2 if i % 2 else 1] + (255,))
    rect(im, 3, 4, 14, 4, WOOD[3] + (255,))
    icons["wooden_wall"] = im

    im = icon_base()
    for ry, off in [(4, 0), (8, 3), (12, 0)]:
        for bx in range(3):
            x0 = 3 + bx * 5 - off
            rect(im, max(3, x0), ry, min(14, x0 + 3), ry + 3, STONE[2] + (255,))
            rect(im, max(3, x0), ry + 3, min(14, x0 + 3), ry + 3, STONE[0] + (255,))
    icons["stone_wall"] = im

    im = icon_base()
    rect(im, 4, 5, 13, 15, WOOD[1] + (255,))
    disc(im, 9, 6, 4.4, 3, WOOD[1] + (255,))
    for x in (6, 9, 12):
        line(im, x, 4, x, 15, WOOD[0] + (255,))
    px(im, 12, 10, (220, 190, 90, 255))
    icons["wooden_door"] = im

    im = icon_base()
    line(im, 3, 14, 14, 4, WOOD[2] + (255,), w=2)
    line(im, 3, 4, 14, 14, WOOD[1] + (255,), w=2)
    icons["barricade"] = im

    im = icon_base()
    for sx in (5, 9, 13):
        for i in range(8):
            wdt = 1 if i < 4 else 0
            for x in range(sx - wdt, sx + wdt + 1):
                px(im, x, 14 - i, IRON[1 if x == sx else 0] + (255,))
        px(im, sx, 6, IRON[2] + (255,))
    icons["spike_trap"] = im

    im = icon_base()
    for i in range(9):
        t = i / 9
        wdt = max(1, int(4 * (1 - t)))
        for x in range(9 - wdt, 9 + wdt + 1):
            c = (255, 232, 120, 255) if abs(x - 9) < 2 and t > 0.2 else (240, 150, 40, 255)
            px(im, x, 13 - i, c)
    line(im, 4, 15, 14, 15, WOOD[1] + (255,), w=2)
    icons["campfire"] = im

    im = icon_base()
    rect(im, 3, 6, 14, 8, WOOD[2] + (255,))
    rect(im, 3, 8, 14, 8, WOOD[0] + (255,))
    rect(im, 4, 9, 5, 15, WOOD[1] + (255,))
    rect(im, 12, 9, 13, 15, WOOD[1] + (255,))
    px(im, 7, 5, IRON[2] + (255,))
    px(im, 10, 4, IRON[1] + (255,))
    icons["workbench"] = im

    for name, im in icons.items():
        save(outline(im), "items/%s.png" % name)


# --------------------------------------------------------------------- fx ---
def fx_assets():
    # slash arc, 3 frames 36x36
    sheet = new(36 * 3, 36)
    for f in range(3):
        im = new(36, 36)
        a0 = -1.1 + f * 0.55
        for t in range(26):
            ang = a0 + t / 25 * 1.5
            for r, c in ((14, (255, 255, 255, 230)), (12, (220, 230, 255, 170)), (15, (200, 215, 245, 120))):
                px(im, 18 + math.cos(ang) * r, 18 + math.sin(ang) * r, c)
        sheet.paste(im, (f * 36, 0))
    save(sheet, "fx/slash.png")

    # arrow projectile (pointing right)
    im = new(20, 6)
    line(im, 1, 3, 15, 3, WOOD[3] + (255,))
    line(im, 15, 3, 18, 3, IRON[2] + (255,))
    px(im, 17, 2, IRON[2] + (255,))
    px(im, 17, 4, IRON[2] + (255,))
    px(im, 2, 2, (200, 60, 60, 255))
    px(im, 3, 1, (200, 60, 60, 255))
    px(im, 2, 4, (200, 60, 60, 255))
    px(im, 3, 5, (200, 60, 60, 255))
    save(im, "fx/arrow.png")

    # firebolt: 3 frames 14x14
    sheet = new(14 * 3, 14)
    for f in range(3):
        im = new(14, 14)
        r = 4 + (f % 2)
        disc(im, 7, 7, r + 1.4, r + 1.4, (200, 80, 24, 160))
        disc(im, 7, 7, r, r, (240, 150, 40, 255))
        disc(im, 6, 6, r * 0.55, r * 0.55, (255, 232, 120, 255))
        sheet.paste(im, (f * 14, 0))
    save(sheet, "fx/firebolt.png")

    # frost shard
    sheet = new(14 * 3, 14)
    for f in range(3):
        im = new(14, 14)
        r = 4 + (f % 2)
        disc(im, 7, 7, r + 1.2, r + 1.2, (90, 140, 220, 150))
        disc(im, 7, 7, r, r, (140, 190, 245, 255))
        disc(im, 6, 6, r * 0.5, r * 0.5, (230, 245, 255, 255))
        sheet.paste(im, (f * 14, 0))
    save(sheet, "fx/frostbolt.png")

    # blood splat: 3 frames 24x24
    sheet = new(24 * 3, 24)
    for f in range(3):
        im = new(24, 24)
        rng = random.Random(60 + f)
        for _ in range(10 + f * 6):
            a = rng.random() * math.tau
            d = rng.random() * (3 + f * 3)
            x = 12 + math.cos(a) * d
            y = 12 + math.sin(a) * d * 0.6
            c = (140, 30, 34, 255) if rng.random() < 0.6 else (180, 50, 48, 255)
            px(im, x, y, c)
            if rng.random() < 0.4:
                px(im, x + 1, y, c)
        sheet.paste(im, (f * 24, 0))
    save(sheet, "fx/blood.png")

    # explosion: 4 frames 40x40
    sheet = new(40 * 4, 40)
    for f in range(4):
        im = new(40, 40)
        rng = random.Random(80 + f)
        r = 6 + f * 4.5
        disc(im, 20, 20, r, r * 0.9, (200, 80, 24, 200 - f * 40), prob=0.85, rng=rng)
        disc(im, 20, 20, r * 0.7, r * 0.65, (240, 150, 40, 230 - f * 40), prob=0.8, rng=rng)
        if f < 3:
            disc(im, 19, 19, r * 0.4, r * 0.4, (255, 232, 120, 255), prob=0.9, rng=rng)
        sheet.paste(im, (f * 40, 0))
    save(sheet, "fx/explosion.png")

    # radial light texture for PointLight2D
    size = 256
    im = new(size, size)
    for y in range(size):
        for x in range(size):
            d = math.hypot(x - size / 2, y - size / 2) / (size / 2)
            a = max(0.0, 1.0 - d)
            a = a * a
            v = int(255 * a)
            px(im, x, y, (255, 255, 255, v))
    save(im, "fx/light.png")

    # ghost marker for build mode handled via modulate; arrow done above


def project_icon():
    im = new(128, 128)
    rng = random.Random(99)
    # night sky
    for y in range(128):
        for x in range(128):
            t = y / 128
            c = (int(24 + 18 * t), int(22 + 16 * t), int(48 + 26 * t), 255)
            px(im, x, y, c)
    for _ in range(40):
        px(im, rng.randint(0, 127), rng.randint(0, 70), (220, 224, 240, 255))
    disc(im, 100, 26, 14, 14, (226, 228, 210, 255))
    disc(im, 95, 22, 11, 11, (24, 22, 48, 255))
    # ground
    for y in range(96, 128):
        for x in range(128):
            px(im, x, y, GRASS[(x * 7 + y * 13) % 3] + (255,))
    # zombie (big)
    big = new(32, 48)
    draw_humanoid(big, 0, 0, "s", ("walk", 1), ZOMBIE_OPTS)
    big = outline(big).resize((64, 96), Image.NEAREST)
    im.alpha_composite(big, (32, 18))
    save(im, "../icon.png")


# ---------------------------------------------------------------- main ------
def main():
    build_terrain_atlas()
    save(tree_oak(11), "props/tree_oak.png")
    save(tree_oak(12), "props/tree_oak2.png")
    save(tree_pine(13), "props/tree_pine.png")
    save(rock(21, True), "props/rock_big.png")
    save(rock(22, False), "props/rock_small.png")
    save(berry_bush(True), "props/bush_berry.png")
    save(berry_bush(False, seed=6), "props/bush_empty.png")
    save(mushroom_patch(), "props/mushrooms.png")
    save(ruin_wall(31), "props/ruin_wall.png")
    save(ruin_wall(32), "props/ruin_wall2.png")
    save(chest(False), "props/chest_closed.png")
    save(chest(True), "props/chest_open.png")

    save(char_sheet(PLAYER_OPTS), "chars/player_sheet.png")
    save(char_sheet(ZOMBIE_OPTS), "chars/zombie_sheet.png")

    save(wooden_wall(), "buildables/wooden_wall.png")
    save(stone_wall(), "buildables/stone_wall.png")
    save(door(False), "buildables/door_closed.png")
    save(door(True), "buildables/door_open.png")
    save(barricade(), "buildables/barricade.png")
    save(spike_trap(), "buildables/spike_trap.png")
    save(campfire_sheet(), "buildables/campfire.png")
    save(workbench(), "buildables/workbench.png")

    make_item_icons()
    fx_assets()
    project_icon()
    print("done")


if __name__ == "__main__":
    main()
