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

# ------------------------------------------------ palette (muted, gritty) ---
GRASS = [(42, 53, 35), (52, 65, 42), (63, 78, 49), (76, 92, 57)]
DIRT = [(60, 47, 36), (76, 60, 45), (92, 74, 55), (108, 88, 66)]
SAND = [(118, 104, 78), (136, 121, 92), (152, 137, 106), (168, 152, 120)]
WATER = [(22, 34, 48), (28, 43, 60), (35, 53, 73), (58, 80, 100)]
STONE = [(56, 56, 62), (74, 74, 81), (94, 94, 102), (116, 116, 124)]
WOOD = [(60, 46, 33), (78, 60, 43), (96, 76, 54), (116, 94, 67)]
LEAF = [(26, 40, 28), (35, 52, 35), (45, 65, 43), (57, 80, 52)]
PINE = [(20, 34, 29), (27, 45, 38), (35, 57, 47), (46, 72, 58)]
SKIN = [(124, 92, 72), (152, 117, 91), (176, 140, 110)]
ZSKIN = [(68, 78, 56), (86, 98, 68), (104, 118, 80)]
IRON = [(82, 86, 94), (116, 120, 128), (152, 156, 164)]


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


def with_shadow(im, cx, cy, rx, ry, alpha=70):
    """Composite a soft ground shadow beneath an already-outlined sprite."""
    base = new(im.width, im.height)
    disc(base, cx, cy, rx, ry, (12, 10, 18, alpha))
    disc(base, cx, cy, rx * 0.6, ry * 0.6, (12, 10, 18, min(255, alpha + 35)))
    base.alpha_composite(im)
    return base


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


def terrain_tile(ramp, seed, tufts=0, tuft_color=None, waves=False, wave_seed=None):
    im = new(TILE_W, TILE_H)
    rng = random.Random(seed)
    for y in range(TILE_H):
        for x in range(TILE_W):
            if not in_diamond(x, y):
                continue
            n = value_noise(x, y, seed, scale=0.22)
            n += (rng.random() - 0.5) * 0.12
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
            if edge > 0.88:
                c = shade(c, 0.82 if y > TILE_H / 2 else 1.08)
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
        wrng = random.Random(wave_seed if wave_seed is not None else seed)
        for _ in range(6):
            wx = wrng.randint(10, TILE_W - 18)
            wy = wrng.randint(6, TILE_H - 7)
            if in_diamond(wx, wy) and in_diamond(wx + 6, wy):
                for i in range(wrng.randint(4, 7)):
                    px(im, wx + i, wy, WATER[3] + (255,))
                if wrng.random() < 0.5:
                    px(im, wx + 1, wy + 1, WATER[2] + (255,))
    return im


def build_terrain_atlas():
    # atlas layout (col,row): see World.gd TILES mapping.
    # Water occupies indices 6,7,8 (horizontally adjacent -> tileset animation).
    cells = [
        terrain_tile(GRASS, 1, tufts=7),
        terrain_tile(GRASS, 2, tufts=5),
        terrain_tile(GRASS, 3, tufts=9),
        terrain_tile(DIRT, 4),
        terrain_tile(DIRT, 5),
        terrain_tile(SAND, 6),
        terrain_tile(WATER, 7, waves=True, wave_seed=70),
        terrain_tile(WATER, 7, waves=True, wave_seed=71),
        terrain_tile(WATER, 7, waves=True, wave_seed=72),
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
    return with_shadow(outline(im), 32, 90, 14, 4)


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
    return with_shadow(outline(im), 32, 90, 12, 3.5)


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
    return with_shadow(outline(im), cx, h - 3, w * 0.44, h * 0.16)


def berry_bush(with_berries=True, seed=5):
    im = new(40, 30)
    rng = random.Random(seed)
    draw_canopy(im, 20, 18, 10, LEAF, rng)
    if with_berries:
        for _ in range(8):
            x = 20 + rng.randint(-9, 9)
            y = 17 + rng.randint(-6, 5)
            px(im, x, y, (146, 38, 42, 255))
            px(im, x + 1, y, (176, 62, 58, 255))
    return with_shadow(outline(im), 20, 26, 12, 3)


def mushroom_patch(seed=9):
    im = new(26, 18)
    rng = random.Random(seed)
    for i, (mx, my, r) in enumerate([(8, 12, 4), (17, 13, 3), (13, 9, 3)]):
        rect(im, mx - 1, my, mx, my + 4, (214, 200, 180, 255))
        disc(im, mx, my - 1, r, r * 0.6, (132, 56, 44, 255))
        disc(im, mx - 1, my - 2, r * 0.5, r * 0.35, (158, 76, 58, 255), prob=0.8, rng=rng)
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
# Sheet layout (32x48 cells, 9 columns x 6 rows):
#   rows 0-2 (S/E/N): walk cols 0-5, idle cols 6-7
#   rows 3-5 (S/E/N): attack anims, 3 frames each:
#       player: melee cols 0-2, bow cols 3-5, staff cols 6-8
#       zombie: lunge repeated in all three slots
DIRS = ["s", "e", "n"]
BOOT = (52, 40, 30, 255)
BELT = (60, 44, 30, 255)
GOLD = (200, 170, 80, 255)
STRING = (215, 210, 195, 255)
ARC = (240, 245, 255, 170)


def _gait(kind, f):
    """Returns (ph, bob, lunge) for a pose."""
    walk = kind == "walk"
    ph = f * math.pi / 3.0 if walk else 0.0
    if walk:
        bob = -1 if f % 3 != 0 else 0
    elif kind == "idle":
        bob = 1 if f == 1 else 0
    else:
        bob = 0
    lunge = (0, 3, 1)[f] if kind == "lunge" else 0
    return ph, bob, lunge


def _draw_s(im, o, kind, f, mirror_n=False):
    skin, hair, tunic, pants = o["skin"], o["hair"], o["tunic"], o["pants"]
    zombie = o.get("zombie", False)
    ph, bob, lunge = _gait(kind, f)
    walk = kind == "walk"
    cx, feet, hip = 16, 45, 36
    hunch = 2 if zombie else 0
    # legs
    lift_l = max(0, round(2.0 * math.sin(ph))) if walk else 0
    lift_r = max(0, round(2.0 * math.sin(ph + math.pi))) if walk else 0
    for lx, lift in ((cx - 4, lift_l), (cx + 1, lift_r)):
        rect(im, lx, hip, lx + 2, feet - lift, pants[1])
        rect(im, lx + 2, hip, lx + 2, feet - lift, pants[0])
        rect(im, lx, feet - 1 - lift, lx + 2, feet - lift, BOOT)
    # torso
    t_top = 24 + bob + hunch
    rect(im, cx - 6, t_top, cx + 5, hip + 1, tunic[1])
    rect(im, cx + 3, t_top, cx + 5, hip + 1, tunic[0])
    rect(im, cx - 6, t_top, cx - 5, hip - 2, tunic[2])
    rect(im, cx - 6, t_top, cx + 5, t_top, tunic[2])
    rect(im, cx - 6, hip - 2, cx + 5, hip - 1, BELT)
    px(im, cx, hip - 2, GOLD)
    if zombie:
        rng = random.Random(f * 13 + 5)
        for _ in range(6):
            px(im, cx + rng.randint(-5, 4), rng.randint(t_top + 1, hip - 3), shade(tunic[0], 0.55))
        px(im, cx - 3, t_top + 4, (140, 40, 40, 255))
        px(im, cx - 2, t_top + 4, (180, 60, 50, 255))
    # arms
    a_y = t_top + 1
    if zombie:
        ext = 9 + lunge
        for ax in (cx - 8, cx + 6):
            rect(im, ax, a_y + 3, ax + 1, a_y + ext, tunic[0])
            rect(im, ax, a_y + ext + 1, ax + 1, a_y + ext + 2, skin[1])
    else:
        sw_l = round(1.5 * math.sin(ph + math.pi)) if walk else 0
        sw_r = round(1.5 * math.sin(ph)) if walk else 0
        for ax, sw in ((cx - 8, sw_l), (cx + 6, sw_r)):
            rect(im, ax, a_y + sw, ax + 1, a_y + 7 + sw, tunic[1])
            rect(im, ax, a_y + 8 + sw, ax + 1, a_y + 9 + sw, skin[1])
    # head
    h_top = t_top - 11
    rect(im, cx - 4, h_top + 1, cx + 3, h_top + 10, skin[1])
    rect(im, cx + 2, h_top + 1, cx + 3, h_top + 10, skin[0])
    rect(im, cx - 4, h_top + 2, cx - 4, h_top + 8, skin[2])
    rect(im, cx - 4, h_top - 1, cx + 3, h_top + 2, hair[1])
    rect(im, cx + 1, h_top - 1, cx + 3, h_top + 2, hair[0])
    px(im, cx - 3, h_top - 1, shade(hair[1], 1.25))
    rect(im, cx - 4, h_top + 2, cx - 4, h_top + 4, hair[1])
    rect(im, cx + 3, h_top + 2, cx + 3, h_top + 4, hair[0])
    if mirror_n:
        # back view: hair covers the whole head
        rect(im, cx - 4, h_top - 1, cx + 3, h_top + 7, hair[1])
        rect(im, cx + 1, h_top - 1, cx + 3, h_top + 7, hair[0])
        px(im, cx - 3, h_top, shade(hair[1], 1.25))
        return
    eye = (205, 45, 45, 255) if zombie else (30, 26, 34, 255)
    px(im, cx - 3, h_top + 5, eye)
    px(im, cx + 2, h_top + 5, eye)
    if zombie:
        rng = random.Random(9)
        for _ in range(3):
            px(im, cx + rng.randint(-3, 2), h_top - 1, (0, 0, 0, 0))
        rect(im, cx - 1, h_top + 8, cx, h_top + 9, (90, 30, 30, 255))
    else:
        px(im, cx - 1, h_top + 8, skin[0])


def _draw_e(im, o, kind, f):
    skin, hair, tunic, pants = o["skin"], o["hair"], o["tunic"], o["pants"]
    zombie = o.get("zombie", False)
    ph, bob, lunge = _gait(kind, f)
    walk = kind == "walk"
    attack = kind in ("melee", "bow", "staff", "lunge")
    cx, feet, hip = 16, 45, 36
    hunch = 2 if zombie else 0
    sx = lunge + (1 if zombie else 0)
    # legs, back leg first (darker)
    for ph_off, leg_c, boot_c in ((math.pi, pants[0], shade(BOOT, 0.8)), (0.0, pants[1], BOOT)):
        if walk:
            dx = round(3.2 * math.sin(ph + ph_off))
            lift = max(0, round(2.0 * math.cos(ph + ph_off)))
        else:
            dx = -3 if ph_off > 0 else 2
            lift = 0
        fx, fy = cx + dx, feet - lift
        line(im, cx, hip + 1, fx, fy - 1, leg_c, w=2)
        rect(im, fx - 1, fy - 1, fx + 1, fy, boot_c)
    t_top = 24 + bob + hunch
    # far arm behind torso
    if zombie:
        line(im, cx + sx - 1, t_top + 2, cx + sx + 6 + lunge, t_top + 7, tunic[0], w=2)
        px(im, cx + sx + 7 + lunge, t_top + 7, skin[0])
    elif walk:
        sw_far = round(2.4 * math.sin(ph + math.pi))
        line(im, cx + sx, t_top + 2, cx + sx + sw_far, t_top + 9, tunic[0], w=2)
        px(im, cx + sx + sw_far, t_top + 10, skin[0])
    # torso
    rect(im, cx - 4 + sx, t_top, cx + 3 + sx, hip + 1, tunic[1])
    rect(im, cx - 4 + sx, t_top, cx - 3 + sx, hip - 1, tunic[0])
    rect(im, cx + 2 + sx, t_top, cx + 3 + sx, hip - 2, tunic[2])
    rect(im, cx - 4 + sx, hip - 2, cx + 3 + sx, hip - 1, BELT)
    if zombie:
        rng = random.Random(f * 11 + 3)
        for _ in range(5):
            px(im, cx + sx + rng.randint(-3, 2), rng.randint(t_top + 1, hip - 3), shade(tunic[0], 0.55))
    # head profile
    h_top = t_top - 11
    hx = cx - 3 + sx + (2 if zombie else 0)
    rect(im, hx, h_top + 1, hx + 7, h_top + 10, skin[1])
    rect(im, hx + 1, h_top + 10, hx + 6, h_top + 10, skin[0])
    px(im, hx + 8, h_top + 6, skin[1])  # nose
    px(im, hx + 8, h_top + 5, skin[2])
    rect(im, hx - 1, h_top - 1, hx + 6, h_top + 2, hair[1])
    rect(im, hx - 1, h_top + 2, hx + 2, h_top + 8, hair[1])
    rect(im, hx - 1, h_top + 4, hx, h_top + 9, hair[0])
    px(im, hx + 1, h_top - 1, shade(hair[1], 1.25))
    eye = (205, 45, 45, 255) if zombie else (30, 26, 34, 255)
    px(im, hx + 6, h_top + 5, eye)
    if zombie:
        px(im, hx + 6, h_top + 9, (90, 30, 30, 255))
    # near arm
    if zombie:
        line(im, cx + sx, t_top + 3, cx + sx + 8 + lunge, t_top + 6, tunic[1], w=2)
        rect(im, cx + sx + 8 + lunge, t_top + 5, cx + sx + 9 + lunge, t_top + 7, skin[1])
    elif not attack:
        sw = round(2.6 * math.sin(ph)) if walk else 0
        line(im, cx + 1 + sx, t_top + 2, cx + 1 + sx + sw, t_top + 10, tunic[1], w=2)
        rect(im, cx + sx + sw, t_top + 9, cx + 1 + sx + sw, t_top + 11, skin[1])


# ------------------------------------------------------ weapon overlays -----
def _arm_to(im, o, sx, sy, hx, hy):
    line(im, sx, sy, hx, hy, o["tunic"][1], w=2)
    rect(im, hx - 1, hy - 1, hx, hy, o["skin"][1])


def _sword(im, o, facing, f, bob):
    if facing == "s":
        poses = [((24, 21), (29, 12)), ((22, 30), (9, 39)), ((13, 36), (6, 41))]
        shoulder = (22, 26)
        arc = ((27, 16), (25, 22), (20, 28), (14, 33))
    elif facing == "e":
        poses = [((12, 24), (6, 16)), ((24, 27), (31, 25)), ((23, 31), (29, 35))]
        shoulder = (17, 27)
        arc = ((19, 19), (24, 20), (28, 22))
    else:
        poses = [((8, 21), (3, 13)), ((16, 12), (24, 8)), ((24, 18), (29, 13))]
        shoulder = (11, 26)
        arc = ((6, 14), (13, 9), (21, 8))
    hand, tip = poses[f]
    hand = (hand[0], hand[1] + bob)
    tip = (tip[0], tip[1] + bob)
    _arm_to(im, o, shoulder[0], shoulder[1] + bob, hand[0], hand[1])
    line(im, hand[0], hand[1], tip[0], tip[1], IRON[1] + (255,), w=2)
    line(im, hand[0], hand[1] - 1, tip[0], tip[1] - 1, IRON[2] + (255,))
    px(im, hand[0], hand[1], GOLD)
    if f == 1:
        for ax, ay in arc:
            px(im, ax, ay + bob, ARC)


def _bow(im, o, facing, f, bob):
    if facing == "e":
        bx, by = 22, 27 + bob
        for i in range(-10, 11):
            ang = i / 10 * 1.15
            x = bx + round(3.5 * math.cos(ang))
            y = by + round(8 * math.sin(ang))
            px(im, x, y, WOOD[2] + (255,))
            px(im, x - 1, y, WOOD[1] + (255,))
        ex = bx + round(3.5 * math.cos(1.15))
        ey1, ey2 = by - round(8 * math.sin(1.15)), by + round(8 * math.sin(1.15))
        if f == 0:
            line(im, ex, ey1, 14, by, STRING)
            line(im, ex, ey2, 14, by, STRING)
            line(im, 14, by, 25, by, WOOD[3] + (255,))
            px(im, 26, by, IRON[2] + (255,))
            _arm_to(im, o, 16, 26 + bob, 14, by)
        else:
            line(im, ex, ey1, ex, ey2, STRING)
            _arm_to(im, o, 16, 26 + bob, 20, by)
            if f == 1:
                px(im, 27, by, ARC)
                px(im, 29, by, ARC)
    else:
        ydir = 1 if facing == "s" else -1
        by = (32 + bob) if facing == "s" else (19 + bob)
        for x in range(8, 25):
            y = by + ydir * round(3.0 * math.cos((x - 16) / 8.0 * 1.25))
            px(im, x, y, WOOD[2] + (255,))
            px(im, x, y - ydir, WOOD[1] + (255,))
        if f == 0:
            mid = by - ydir * 4
            line(im, 8, by + ydir, 16, mid, STRING)
            line(im, 24, by + ydir, 16, mid, STRING)
            line(im, 16, mid, 16, by + ydir * 3, WOOD[3] + (255,))
            px(im, 16, by + ydir * 4, IRON[2] + (255,))
        else:
            line(im, 8, by + ydir, 24, by + ydir, STRING)
            if f == 1:
                px(im, 16, by + ydir * 5, ARC)
                px(im, 16, by + ydir * 7, ARC)


def _staff(im, o, facing, f, bob):
    orb = (110, 160, 235, 255)
    if facing == "e":
        cfgs = [((19, 38), (23, 18)), ((17, 36), (28, 20)), ((19, 38), (24, 20))]
        shoulder = (17, 27)
    elif facing == "s":
        cfgs = [((24, 40), (24, 16)), ((23, 42), (21, 20)), ((24, 40), (24, 18))]
        shoulder = (22, 27)
    else:
        cfgs = [((8, 40), (8, 16)), ((9, 42), (11, 20)), ((8, 40), (8, 18))]
        shoulder = (11, 27)
    base, top = cfgs[f]
    line(im, base[0], base[1] + bob, top[0], top[1] + bob, WOOD[2] + (255,), w=2)
    line(im, base[0] + 1, base[1] + bob, top[0] + 1, top[1] + bob, WOOD[0] + (255,))
    mid = ((base[0] + top[0]) // 2, (base[1] + top[1]) // 2 + bob)
    _arm_to(im, o, shoulder[0], shoulder[1] + bob, mid[0], mid[1])
    disc(im, top[0], top[1] + bob - 2, 2.4, 2.4, orb)
    px(im, top[0] - 1, top[1] + bob - 3, (235, 245, 255, 255))
    if f == 1:
        for gx, gy in ((4, 0), (-4, -1), (0, 4), (3, -4), (-3, 3)):
            px(im, top[0] + gx, top[1] + bob - 2 + gy, (170, 200, 255, 210))


def draw_char(im, facing, kind, f, o):
    weapon = {"melee": _sword, "bow": _bow, "staff": _staff}.get(kind)
    _, bob, _ = _gait(kind, f)
    pre = weapon is not None and facing == "n" and kind in ("bow", "staff")
    if pre:
        weapon(im, o, facing, f, bob)
    if facing == "e":
        _draw_e(im, o, kind, f)
    else:
        _draw_s(im, o, kind, f, mirror_n=(facing == "n"))
    if weapon is not None and not pre:
        weapon(im, o, facing, f, bob)


def render_cell(facing, kind, f, opts):
    im = new(32, 48)
    draw_char(im, facing, kind, f, opts)
    out = outline(im)
    base = new(32, 48)
    disc(base, 16, 45, 8, 2.6, (12, 10, 18, 80))
    base.alpha_composite(out)
    return base


def char_sheet(opts):
    fw, fh, cols = 32, 48, 9
    sheet = new(fw * cols, fh * 6)
    for row, facing in enumerate(DIRS):
        for f in range(6):
            sheet.paste(render_cell(facing, "walk", f, opts), (f * fw, row * fh))
        for f in range(2):
            sheet.paste(render_cell(facing, "idle", f, opts), ((6 + f) * fw, row * fh))
    attack_kinds = ["lunge", "lunge", "lunge"] if opts.get("zombie") else ["melee", "bow", "staff"]
    for row, facing in enumerate(DIRS):
        for ki, kind in enumerate(attack_kinds):
            for f in range(3):
                sheet.paste(render_cell(facing, kind, f, opts), ((ki * 3 + f) * fw, (row + 3) * fh))
    return sheet


# weathered leather jerkin + dark hood tones: survivor, not hero
PLAYER_OPTS = dict(
    skin=[s + (255,) for s in SKIN],
    hair=[(44, 32, 24, 255), (66, 48, 34, 255)],
    tunic=[(50, 41, 33, 255), (68, 56, 44, 255), (86, 72, 56, 255)],
    pants=[(42, 38, 36, 255), (58, 52, 48, 255)],
    hood=False,
)

ZOMBIE_OPTS = dict(
    skin=[s + (255,) for s in ZSKIN],
    hair=[(36, 40, 30, 255), (50, 55, 40, 255)],
    tunic=[(46, 41, 38, 255), (62, 55, 49, 255), (78, 70, 61, 255)],
    pants=[(40, 36, 32, 255), (54, 48, 42, 255)],
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
        disc(im, bx, by, 2.4, 2.4, (146, 38, 42, 255))
        px(im, bx - 1, by - 1, (186, 78, 72, 255))
    line(im, 9, 3, 9, 7, GRASS[1] + (255,))
    line(im, 9, 4, 13, 3, GRASS[2] + (255,))
    icons["berries"] = im

    im = icon_base()  # mushroom
    rect(im, 8, 9, 10, 14, (214, 200, 180, 255))
    disc(im, 9, 8, 5.4, 3.4, (132, 56, 44, 255))
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

    # vignette overlay (stretched fullscreen by the HUD)
    size = 320
    im = new(size, int(size * 9 / 16))
    h = im.height
    for y in range(h):
        for x in range(size):
            dx = (x - size / 2) / (size / 2)
            dy = (y - h / 2) / (h / 2)
            d = (dx * dx + dy * dy) ** 0.5
            a = int(150 * max(0.0, d - 0.62) / 0.75)
            px(im, x, y, (8, 6, 12, min(a, 150)))
    save(im, "fx/vignette.png")


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
    draw_char(big, "s", "walk", 1, ZOMBIE_OPTS)
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
