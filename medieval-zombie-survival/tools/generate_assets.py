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
WATER = [(27, 41, 56), (34, 51, 69), (43, 64, 84), (68, 92, 112)]
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


def scale2x(im):
    """Pixel-art-aware 2x upscale (Scale2x): doubles resolution while
    smoothing diagonals, keeping the hand-pixelled look."""
    w, h = im.size
    sp = im.load()
    out = Image.new("RGBA", (w * 2, h * 2))
    op = out.load()

    def g(x, y):
        if x < 0 or y < 0 or x >= w or y >= h:
            return (0, 0, 0, 0)
        return sp[x, y]

    for y in range(h):
        for x in range(w):
            P = sp[x, y]
            A = g(x, y - 1)
            B = g(x + 1, y)
            C = g(x - 1, y)
            D = g(x, y + 1)
            e0 = e1 = e2 = e3 = P
            if C == A and C != D and A != B:
                e0 = A
            if A == B and A != C and B != D:
                e1 = B
            if D == C and D != B and C != A:
                e2 = C
            if B == D and B != A and D != C:
                e3 = D
            op[2 * x, 2 * y] = e0
            op[2 * x + 1, 2 * y] = e1
            op[2 * x, 2 * y + 1] = e2
            op[2 * x + 1, 2 * y + 1] = e3
    return out


# these are sampled at native size by the engine (lights, UI overlay, OS icon)
NO_UPSCALE = {"fx/light.png", "fx/vignette.png", "../icon.png", "tiles/terrain_atlas.png"}


def save(im, rel):
    path = os.path.join(ASSETS, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if rel not in NO_UPSCALE:
        im = scale2x(im)
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


def terrain_tile(ramp, seed, tufts=0, tuft_color=None, waves=False, wave_seed=None,
                 tw=TILE_W, th=TILE_H, nscale=0.22):
    im = new(tw, th)
    rng = random.Random(seed)
    for y in range(th):
        for x in range(tw):
            if not in_diamond(x, y, tw, th):
                continue
            n = value_noise(x, y, seed, scale=nscale)
            n += (rng.random() - 0.5) * 0.12
            if n < 0.18:
                c = ramp[0]
            elif n < 0.55:
                c = ramp[1]
            elif n < 0.88:
                c = ramp[2]
            else:
                c = ramp[3]
            px(im, x, y, c + (255,))
    for _ in range(tufts):
        tx = rng.randint(tw // 5, tw - tw // 5)
        ty = rng.randint(th // 4, th - th // 4)
        if in_diamond(tx, ty, tw, th):
            col = tuft_color or ramp[3]
            px(im, tx, ty, col + (255,))
            px(im, tx, ty - 1, col + (255,))
            if rng.random() < 0.5:
                px(im, tx + 1, ty, shade(col + (255,), 0.85))
    if waves:
        wrng = random.Random(wave_seed if wave_seed is not None else seed)
        for _ in range(6 * tw // TILE_W):
            wx = wrng.randint(tw // 6, tw - tw // 4)
            wy = wrng.randint(th // 5, th - th // 5)
            if in_diamond(wx, wy, tw, th) and in_diamond(wx + 6, wy, tw, th):
                for i in range(wrng.randint(4, 7)):
                    px(im, wx + i, wy, WATER[3] + (255,))
                if wrng.random() < 0.5:
                    px(im, wx + 1, wy + 1, WATER[2] + (255,))
    return im


def cobble_tile(seed, tw=TILE_W, th=TILE_H):
    """Rounded cobblestones with dark grout, clipped to the iso diamond."""
    im = new(tw, th)
    rng = random.Random(seed)
    grout = shade(STONE[0] + (255,), 0.62)
    for y in range(th):
        for x in range(tw):
            if in_diamond(x, y, tw, th):
                px(im, x, y, grout)
    for row, y in enumerate(range(2, th - 1, 5)):
        off = (row % 2) * 4 + rng.randint(-1, 1)
        for x in range(3 + off, tw - 2, 8):
            jx = x + rng.randint(-1, 1)
            jy = y + rng.randint(-1, 1)
            tone = rng.choice([STONE[1], STONE[1], STONE[2], STONE[2], STONE[3]])
            if rng.random() < 0.12:
                tone = shade(STONE[1], 0.85)[:3]
            disc(im, jx, jy, rng.uniform(3.2, 4.4), rng.uniform(1.9, 2.5), tone + (255,))
            px(im, jx - 1, jy - 1, shade(tone + (255,), 1.18))
            px(im, jx, jy - 1, shade(tone + (255,), 1.1))
            px(im, jx + 1, jy + 1, shade(tone + (255,), 0.8))
    # clip to diamond
    for y in range(th):
        for x in range(tw):
            if not in_diamond(x, y, tw, th):
                px(im, x, y, (0, 0, 0, 0))
    return im




FRINGE_RAMPS = {"grass": GRASS, "dirt": DIRT, "sand": SAND}


def _mat_color(x, y, kind, rng):
    if kind == "stone":
        n = value_noise(x * 0.9, y * 1.1, 19.0)
        c = STONE[2] if n > 0.5 else STONE[1]
        if rng.random() < 0.18:
            c = shade(STONE[0] + (255,), 0.8)[:3]
        return c
    ramp = FRINGE_RAMPS[kind]
    n = value_noise(x, y, {"grass": 1, "dirt": 4, "sand": 6}[kind], scale=0.13)
    n += (rng.random() - 0.5) * 0.12
    if n < 0.18:
        return ramp[0]
    if n < 0.55:
        return ramp[1]
    if n < 0.88:
        return ramp[2]
    return ramp[3]


def fringe_tile(kind, direction, seed, tw=TILE_W, th=TILE_H):
    """A transparent tile where `kind` bleeds in from one diamond edge
    (nw/ne/sw/se) with an irregular, dithered boundary."""
    im = new(tw, th)
    rng = random.Random(seed)
    for y in range(th):
        for x in range(tw):
            if not in_diamond(x, y, tw, th):
                continue
            nx = (x + 0.5) / tw * 2 - 1
            ny = (y + 0.5) / th * 2 - 1
            if direction == "nw":
                s = nx + ny + 1
                t = (nx - ny + 1) / 2
            elif direction == "ne":
                s = 1 - (nx - ny)
                t = (nx + ny + 1) / 2
            elif direction == "sw":
                s = 1 + (nx - ny)
                t = (nx + ny + 1) / 2
            else:  # se
                s = 1 - (nx + ny)
                t = (nx - ny + 1) / 2
            depth = 0.26 + 0.22 * value_noise(t * 11.0, seed * 2.0, 41.0 + seed)
            c = _mat_color(x, y, kind, rng)
            if s < depth:
                px(im, x, y, c + (255,))
            elif s < depth + 0.16 and rng.random() < 0.4:
                px(im, x, y, c + (255,))  # dithered fade
    if kind == "grass":
        for i in range(3 * tw // TILE_W):
            tx = rng.randint(8, tw - 8)
            ty = rng.randint(4, th - 5)
            if im.getpixel((tx, ty))[3] > 0:
                px(im, tx, ty - 1, GRASS[3] + (255,))
    return im


def build_terrain_atlas():
    # atlas layout (col,row): see World.gd TILES mapping.
    # Water occupies indices 6,7,8 (horizontally adjacent -> tileset animation).
    tw, th = TILE_W * 2, TILE_H * 2  # native high-res ground
    cells = [
        terrain_tile(GRASS, 1, tufts=14, tw=tw, th=th, nscale=0.11),
        terrain_tile(GRASS, 2, tufts=10, tw=tw, th=th, nscale=0.11),
        terrain_tile(GRASS, 3, tufts=18, tw=tw, th=th, nscale=0.11),
        terrain_tile(DIRT, 4, tw=tw, th=th, nscale=0.11),
        terrain_tile(DIRT, 5, tw=tw, th=th, nscale=0.11),
        terrain_tile(SAND, 6, tw=tw, th=th, nscale=0.11),
        terrain_tile(WATER, 7, waves=True, wave_seed=70, tw=tw, th=th, nscale=0.11),
        terrain_tile(WATER, 7, waves=True, wave_seed=71, tw=tw, th=th, nscale=0.11),
        terrain_tile(WATER, 7, waves=True, wave_seed=72, tw=tw, th=th, nscale=0.11),
        cobble_tile(9, tw=tw, th=th),
        cobble_tile(10, tw=tw, th=th),
    ]
    # fringe overlays, indices 11..26: mats x dirs (order must match World.gd)
    for mi, mat in enumerate(["grass", "dirt", "sand", "stone"]):
        for di, d in enumerate(["nw", "ne", "sw", "se"]):
            cells.append(fringe_tile(mat, d, 50 + mi * 4 + di, tw=tw, th=th))
    cols = 5
    rows = (len(cells) + cols - 1) // cols
    atlas = new(cols * tw, rows * th)
    for i, c in enumerate(cells):
        atlas.paste(c, ((i % cols) * tw, (i // cols) * th))
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
    draw_iso_block(im, height=int(18 + rng.random() * 14), style="stone",
                   jagged=True, rng=rng)
    return outline(im)


# ------------------------------------------------------------- iso blocks ---
SLATE = [(38, 40, 48), (52, 55, 64), (68, 72, 82), (88, 93, 104)]
PLASTER = [(118, 108, 92), (142, 132, 114), (164, 154, 134), (182, 172, 152)]
TIMBER = [(34, 27, 21), (48, 38, 29), (64, 52, 40)]
REDTILE = [(92, 42, 34), (120, 57, 44), (148, 74, 54), (174, 94, 64)]


def _stone_face(x, yy, col_h, left):
    """Irregular coursed masonry with mortar joints, bevels and moss."""
    course_h = 7
    row = yy // course_h
    off = (row * 5 + int(value_noise(row, 0, 3.0) * 4)) % 11
    bx = (x + off) % 11
    by = yy % course_h
    base = STONE[2] if left else STONE[1]
    if by == 0 or bx == 0:
        return shade(base + (255,), 0.45)  # mortar
    block_id = (x + off) // 11 + row * 13
    n = value_noise(block_id * 3.1, row * 2.7, 3.0)
    c = base + (255,)
    if n > 0.7:
        c = (STONE[3] if left else STONE[2]) + (255,)
    elif n < 0.32:
        c = shade(c, 0.84)
    # bevel: light top-left, dark bottom-right
    if by == 1 or bx == 1:
        c = shade(c, 1.14)
    elif by >= course_h - 2 or bx >= 9:
        c = shade(c, 0.82)
    # moss creeping up from the base
    if yy > col_h * 0.62:
        m = value_noise(x * 1.7, yy * 1.4, 13.0) + (yy - col_h * 0.62) / max(col_h * 0.38, 1) * 0.25
        if m > 0.86:
            c = LEAF[2] + (255,)
        elif m > 0.78:
            c = LEAF[1] + (255,)
    return c


def _timber_face(x, yy, col_h, left, face_x0, face_x1):
    """Half-timbered: plaster panels framed by dark beams with diagonal brace."""
    base = PLASTER[2] if left else PLASTER[1]
    c = base + (255,)
    n = value_noise(x * 1.8, yy * 1.6, 5.0)
    if n > 0.74:
        c = (PLASTER[3] if left else PLASTER[2]) + (255,)
    elif n < 0.3:
        c = shade(c, 0.88)
    # weather staining near the base
    if yy > col_h * 0.7 and value_noise(x * 2.3, yy, 9.0) > 0.55:
        c = shade(c, 0.8)
    beam = False
    if yy <= 2 or yy >= col_h - 3:
        beam = True  # top plate / sill
    for post in (face_x0, face_x1 - 2, 31):
        if post <= x <= post + 2:
            beam = True  # corner and edge posts
    # diagonal brace across the panel
    span = max(face_x1 - face_x0 - 6, 1)
    t = (x - face_x0 - 3) / span
    if 0.0 <= t <= 1.0:
        brace_y = (0.82 - 0.6 * t) * col_h if left else (0.22 + 0.6 * t) * col_h
        if abs(yy - brace_y) < 1.6:
            beam = True
    if beam:
        bc = TIMBER[1]
        if value_noise(x * 3.0, yy * 2.0, 7.0) > 0.7:
            bc = TIMBER[2]
        elif (x + yy) % 7 == 0:
            bc = TIMBER[0]
        return bc + (255,)
    return c


def _cap_color(x, y, material):
    """Shingled cap texture for the top diamond (slate or wood)."""
    ramp = SLATE if material == "slate" else WOOD
    row = y // 4
    off = (row % 2) * 4
    n = value_noise((x + off) * 0.9, row * 3.3, 21.0)
    c = ramp[2] if n > 0.45 else ramp[1]
    if n > 0.8:
        c = ramp[3]
    if y % 4 == 0 or ((x + off) % 8) == 0:
        c = ramp[0]
    return c + (255,)


def draw_iso_block(im, height, style, jagged=False, rng=None,
                   door_hole=False, door_open=False):
    """Isometric block, 64x32 diamond footprint, faces extruded by `height`.
    style: "stone" (masonry + slate cap) or "timber" (half-timber + shingles).
    """
    rng = rng or random.Random(1)
    base_top = im.height - TILE_H
    cy = base_top + TILE_H / 2
    jag = [0] * 64
    if jagged:
        v = 0
        for x in range(64):
            if rng.random() < 0.2:
                v = rng.randint(0, 10)
            jag[x] = v

    # vertical faces: extrude each diamond column upward
    for x in range(64):
        nx = (x + 0.5) / 64 * 2 - 1
        half = (1 - abs(nx)) * (TILE_H / 2)
        y_bot = cy + half
        h = max(0, height - jag[x])
        y0 = cy - half - h
        col_h = int(y_bot - y0)
        left = x < 32
        face_x0, face_x1 = (1, 31) if left else (33, 63)
        for y in range(int(math.ceil(y0)), int(y_bot) + 1):
            yy = y - int(y0)
            if style == "stone":
                c = _stone_face(x, yy, col_h, left)
            else:
                c = _timber_face(x, yy, col_h, left, face_x0, face_x1)
            px(im, x, y, c)
    # shingled cap on top
    cap = "slate" if style == "stone" else "wood"
    for y in range(TILE_H):
        for x in range(64):
            if in_diamond(x, y):
                h = height - jag[x]
                c = _cap_color(x, y, cap)
                if jagged and value_noise(x, y, 31.0) > 0.72:
                    c = (STONE[1] if style == "stone" else WOOD[1]) + (255,)
                px(im, x, base_top + y - h, c)
    # eave shadow under the cap + rim light along the cap edge
    cap_ramp = SLATE if cap == "slate" else WOOD
    for x in range(64):
        nx = (x + 0.5) / 64 * 2 - 1
        half = (1 - abs(nx)) * (TILE_H / 2)
        h = max(0, height - jag[x])
        y_eave = int(cy + half - h)
        px(im, x, y_eave + 1, (34, 30, 34, 255))
        if not jagged:
            px(im, x, int(cy - half - h), shade(cap_ramp[3] + (255,), 1.1))
    # shade lower edges of footprint
    base_ramp = STONE if style == "stone" else TIMBER
    for y in range(TILE_H):
        for x in range(64):
            if in_diamond(x, y) and not in_diamond(x, y + 1):
                px(im, x, base_top + y, shade(base_ramp[0] + (255,), 0.8))
    if door_hole:
        _draw_door_opening(im, cy, door_open)


def _draw_door_opening(im, cy, door_open):
    """Arched plank door (or open hole) on the south corner, with an awning."""
    cx = 32
    for x in range(cx - 8, cx + 9):
        nx = (x + 0.5) / 64 * 2 - 1
        half = (1 - abs(nx)) * (TILE_H / 2)
        y_bot = int(cy + half)
        dx = abs(x - cx)
        arch = 19 - max(0, dx - 5) * 3 - (dx * dx) // 14
        for i in range(arch):
            y = y_bot - i
            if door_open:
                px(im, x, y, (0, 0, 0, 0))
                if i == arch - 1 or dx == 8:
                    px(im, x, y, TIMBER[0] + (255,))  # inner frame
            else:
                c = WOOD[1] if (x % 3) else WOOD[0]
                if i == arch - 1:
                    c = TIMBER[0]
                px(im, x, y, c + (255,))
    if not door_open:
        px(im, cx + 5, im.height - 12, (196, 168, 76, 255))  # handle
        for hy in (im.height - 9, im.height - 17):  # hinges
            px(im, cx - 7, hy, IRON[1] + (255,))
            px(im, cx - 6, hy, IRON[2] + (255,))
    # slate awning above the door
    for x in range(cx - 10, cx + 11):
        ay = im.height - 25 + abs(x - cx) // 4
        for t in range(2):
            px(im, x, ay + t, SLATE[2 if t == 0 else 1] + (255,))
        px(im, x, ay - 1, SLATE[3] + (255,))
        px(im, x, ay + 2, (30, 26, 30, 200))  # shadow under awning


def wooden_wall():
    im = new(64, 64)
    draw_iso_block(im, 28, "timber")
    return outline(im)


def stone_wall():
    im = new(64, 64)
    draw_iso_block(im, 30, "stone")
    return outline(im)


def door(open_state):
    im = new(64, 64)
    draw_iso_block(im, 28, "timber", door_hole=True, door_open=open_state)
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
    # heavy table top (3px thick edge)
    for y in range(20):
        for x in range(56):
            if in_diamond(x, y, 56, 20):
                n = value_noise(x, y, 17.0)
                c = WOOD[2] if n < 0.7 else WOOD[3]
                if ((x + y * 2) % 7) == 0:
                    c = WOOD[1]
                px(im, x + 4, y + 8, c + (255,))
    for t in range(3):
        for y in range(20):
            for x in range(56):
                if in_diamond(x, y, 56, 20) and not in_diamond(x, y + 1, 56, 20):
                    px(im, x + 4, y + 9 + t, (WOOD[1] if t < 2 else WOOD[0]) + (255,))
    # legs with cross brace
    for lx, ly in [(10, 18), (54, 18), (32, 26)]:
        rect(im, lx - 1, ly + 8, lx + 1, ly + 24, TIMBER[1] + (255,))
        rect(im, lx + 1, ly + 8, lx + 1, ly + 24, TIMBER[0] + (255,))
        rect(im, lx - 1, ly + 8, lx - 1, ly + 24, TIMBER[2] + (255,))
    line(im, 11, 36, 31, 44, TIMBER[1] + (255,), w=2)
    line(im, 53, 36, 33, 44, TIMBER[1] + (255,), w=2)
    # tools: hammer, tongs, horseshoe
    rect(im, 38, 11, 42, 13, IRON[1] + (255,))
    px(im, 38, 11, IRON[2] + (255,))
    line(im, 40, 14, 40, 19, WOOD[3] + (255,))
    line(im, 20, 13, 27, 16, IRON[1] + (255,))
    line(im, 20, 15, 27, 16, IRON[0] + (255,))
    for a in range(8):
        ang = math.pi * (0.15 + 0.7 * a / 7)
        px(im, 48 + math.cos(ang) * 3, 16 - math.sin(ang) * 2.4, IRON[2] + (255,))
    # ember bowl with warm glow
    disc(im, 14, 16, 2.6, 1.6, (52, 44, 40, 255))
    px(im, 13, 15, (214, 120, 44, 255))
    px(im, 14, 15, (240, 168, 70, 255))
    px(im, 15, 16, (188, 92, 38, 255))
    px(im, 14, 14, (255, 208, 120, 200))
    return outline(im)


def chest(open_state=False):
    im = new(36, 32)
    rect(im, 5, 16, 30, 28, WOOD[1] + (255,))
    rect(im, 5, 16, 30, 17, WOOD[2] + (255,))
    for x in range(5, 31, 6):
        line(im, x, 16, x, 28, WOOD[0] + (255,))
    if open_state:
        rect(im, 4, 6, 31, 10, WOOD[2] + (255,))
        rect(im, 4, 6, 31, 7, WOOD[3] + (255,))
        rect(im, 6, 12, 29, 15, (26, 20, 18, 255))  # dark interior
        px(im, 14, 13, (224, 196, 104, 255))
        px(im, 20, 14, (224, 196, 104, 255))
        px(im, 17, 13, (200, 172, 90, 255))
    else:
        rect(im, 4, 11, 31, 15, WOOD[2] + (255,))
        rect(im, 4, 11, 31, 12, WOOD[3] + (255,))
    # iron corner brackets + central band
    band_top = 11 if not open_state else 16
    rect(im, 16, band_top, 19, 28, IRON[0] + (255,))
    rect(im, 17, band_top, 18, 28, IRON[1] + (255,))
    rect(im, 16, 18, 19, 21, IRON[2] + (255,))  # lock plate
    px(im, 17, 19, (40, 34, 30, 255))           # keyhole
    for bx in (5, 29):
        rect(im, bx - 1, 26, bx + 1, 28, IRON[0] + (255,))
        rect(im, bx - 1, band_top, bx + 1, band_top + 2, IRON[0] + (255,))
        px(im, bx, 27, IRON[2] + (255,))
        px(im, bx, band_top + 1, IRON[2] + (255,))
    return with_shadow(outline(im), 18, 28, 12, 3)


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

    im = icon_base()  # remedy (infection cure)
    rect(im, 6, 7, 11, 15, (96, 62, 140, 255))
    rect(im, 6, 7, 11, 8, (130, 92, 178, 255))
    rect(im, 7, 12, 8, 13, (170, 130, 220, 255))
    rect(im, 7, 4, 10, 6, (150, 130, 100, 255))
    px(im, 8, 3, (190, 170, 130, 255))
    px(im, 12, 9, (200, 170, 240, 200))
    icons["remedy"] = im

    im = icon_base()  # bandage
    disc(im, 8, 10, 5.2, 5.2, (214, 206, 192, 255))
    disc(im, 8, 10, 2.0, 2.0, (162, 152, 138, 255))
    for a in range(10):
        ang = a / 10 * math.tau
        px(im, 8 + math.cos(ang) * 3.6, 10 + math.sin(ang) * 3.6, (188, 178, 164, 255))
    rect(im, 11, 3, 15, 5, (214, 206, 192, 255))
    rect(im, 11, 5, 15, 5, (178, 168, 154, 255))
    icons["bandage"] = im

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



# ---------------------------------------------------------- town buildings --
# Large pre-built composite sprites: gabled slate roofs, half-timber and
# masonry facades, glowing windows. Footprint W x H tiles; the south corner
# of the footprint sits at image pixel (32*W, img_h - 2).

def _b_stone(fx, yy, col_h, light, sd=0.0):
    course_h = 7
    row = yy // course_h
    off = (row * 5 + int(value_noise(row, 1, 4.0 + sd) * 4)) % 12
    bx = (fx + off) % 12
    by = yy % course_h
    base = STONE[2] if light else STONE[1]
    if by == 0 or bx == 0:
        return shade(base + (255,), 0.45)
    block_id = (fx + off) // 12 + row * 17
    n = value_noise(block_id * 2.9, row * 3.1, 4.0 + sd)
    c = base + (255,)
    if n > 0.7:
        c = (STONE[3] if light else STONE[2]) + (255,)
    elif n < 0.32:
        c = shade(c, 0.85)
    if by == 1 or bx == 1:
        c = shade(c, 1.13)
    elif by >= course_h - 2 or bx >= 10:
        c = shade(c, 0.83)
    if yy > col_h * 0.66:
        m = value_noise(fx * 1.7, yy * 1.4, 14.0 + sd) + (yy - col_h * 0.66) / max(col_h * 0.34, 1) * 0.25
        if m > 0.88:
            c = LEAF[2] + (255,)
        elif m > 0.8:
            c = LEAF[1] + (255,)
    return c


def _b_timber(fx, yy, col_h, light, sd=0.0):
    base = PLASTER[2] if light else PLASTER[1]
    c = base + (255,)
    n = value_noise(fx * 1.8, yy * 1.6, 6.0 + sd)
    if n > 0.74:
        c = (PLASTER[3] if light else PLASTER[2]) + (255,)
    elif n < 0.3:
        c = shade(c, 0.88)
    if yy > col_h * 0.72 and value_noise(fx * 2.3, yy, 9.5 + sd) > 0.55:
        c = shade(c, 0.8)
    beam = yy <= 1 or yy >= col_h - 3
    if (fx % 16) < 2:
        beam = True
    seg = fx // 16
    t = (fx % 16 - 2) / 12.0
    if 0.0 <= t <= 1.0:
        by_ = (0.15 + 0.7 * (t if seg % 2 == 0 else 1.0 - t)) * col_h
        if abs(yy - by_) < 1.5:
            beam = True
    if beam:
        bc = TIMBER[1]
        if value_noise(fx * 3.0, yy * 2.0, 7.5 + sd) > 0.7:
            bc = TIMBER[2]
        elif (fx + yy) % 7 == 0:
            bc = TIMBER[0]
        return bc + (255,)
    return c


def _face_color(style, fx, yy, col_h, light, sd):
    if style == "stone":
        return _b_stone(fx, yy, col_h, light, sd)
    if style == "mixed":  # timber upper floor over stone ground floor
        split = int(col_h * 0.55)
        if yy < split:
            return _b_timber(fx, yy, split, light, sd)
        return _b_stone(fx, yy - split, col_h - split, light, sd)
    return _b_timber(fx, yy, col_h, light, sd)


def _draw_face_window(im, x_at, y_bot_fn, fx_c, wall_h, lit=True):
    w, h = 5, 8
    for dx in range(-(w // 2), w // 2 + 1):
        x = x_at(fx_c + dx)
        yb = y_bot_fn(x)
        top = yb - int(wall_h * 0.78)
        for dy in range(h):
            y = top + dy
            if dy == 0 and abs(dx) == w // 2:
                continue  # arch corners
            if dy == 0 or dy == h - 1 or abs(dx) == w // 2:
                px(im, x, y, TIMBER[0] + (255,))
            elif dx == 0 and dy >= 2:
                px(im, x, y, TIMBER[0] + (255,))  # mullion
            else:
                t = dy / h
                if lit:
                    g = (int(252 - 60 * t), int(196 - 86 * t), int(106 - 56 * t))
                else:
                    g = (40, 44, 56)
                px(im, x, y, g + (255,))
        px(im, x_at(fx_c + dx), y_bot_fn(x_at(fx_c + dx)) - int(wall_h * 0.78) + h, TIMBER[2] + (255,))


def _draw_face_door(im, x_at, y_bot_fn, fx_c, wall_h):
    w = 11
    for dx in range(-(w // 2), w // 2 + 1):
        x = x_at(fx_c + dx)
        yb = y_bot_fn(x)
        hgt = 17 - max(0, abs(dx) - 3) * 2
        for i in range(hgt):
            y = yb - i
            c = WOOD[1] if ((fx_c + dx) % 3) else WOOD[0]
            if i == hgt - 1:
                c = TIMBER[0]
            px(im, x, y, c + (255,))
    x_h = x_at(fx_c + 3)
    px(im, x_h, y_bot_fn(x_h) - 7, (196, 168, 76, 255))
    # slate awning
    for dx in range(-(w // 2) - 2, w // 2 + 3):
        x = x_at(fx_c + dx)
        ay = y_bot_fn(x) - 20
        px(im, x, ay, SLATE[3] + (255,))
        px(im, x, ay + 1, SLATE[2] + (255,))
        px(im, x, ay + 2, (30, 26, 30, 200))


def _dist_to_seg(p, a, b):
    ax, ay = a
    bx, by = b
    pxx, pyy = p
    dx, dy = bx - ax, by - ay
    l2 = dx * dx + dy * dy
    if l2 == 0:
        return math.hypot(pxx - ax, pyy - ay)
    t = max(0.0, min(1.0, ((pxx - ax) * dx + (pyy - ay) * dy) / l2))
    return math.hypot(pxx - (ax + t * dx), pyy - (ay + t * dy))


def _fill_gable(im, p0, p1, apex, style, sd, lit_window=False):
    """Triangular gable end between wall-top edge p0-p1 and the ridge apex."""
    xs = [p0[0], p1[0], apex[0]]
    ys = [p0[1], p1[1], apex[1]]
    midx = (p0[0] + p1[0]) / 2

    def sign(a, b, p):
        return (b[0] - a[0]) * (p[1] - a[1]) - (b[1] - a[1]) * (p[0] - a[0])

    for y in range(int(min(ys)), int(max(ys)) + 1):
        for x in range(int(min(xs)), int(max(xs)) + 1):
            p = (x + 0.5, y + 0.5)
            d0 = sign(p0, p1, p)
            d1 = sign(p1, apex, p)
            d2 = sign(apex, p0, p)
            neg = (d0 < 0) or (d1 < 0) or (d2 < 0)
            pos = (d0 > 0) or (d1 > 0) or (d2 > 0)
            if neg and pos:
                continue
            base = PLASTER[1] if style != "stone" else STONE[1]
            n = value_noise(x * 1.7, y * 1.5, 8.0 + sd)
            c = base + (255,)
            if n > 0.72:
                c = (PLASTER[2] if style != "stone" else STONE[2]) + (255,)
            elif n < 0.3:
                c = shade(c, 0.86)
            # timber frame: rafters along the two slopes, sill, king post
            if (_dist_to_seg(p, p0, apex) < 1.8 or _dist_to_seg(p, p1, apex) < 1.8
                    or _dist_to_seg(p, p0, p1) < 1.6 or abs(x - midx) < 1.0):
                c = TIMBER[1] + (255,)
                if (x + y) % 7 == 0:
                    c = TIMBER[0] + (255,)
            px(im, x, y, c)
    if lit_window:
        wx, wy = int(midx), int((p0[1] + p1[1]) / 2 + apex[1]) // 2
        for dx in range(-2, 3):
            for dy in range(-2, 3):
                if abs(dx) + abs(dy) <= 2:
                    px(im, wx + dx + 2, wy + dy, (250, 190, 100, 255))
                elif abs(dx) + abs(dy) == 3:
                    px(im, wx + dx + 2, wy + dy, TIMBER[0] + (255,))


def _fill_roof_plane(im, e0, e1, r0, r1, dark=1.0, ramp=None):
    """Shingle plane between eave edge e0-e1 and ridge edge r0-r1."""
    ramp = ramp or SLATE
    drop = math.hypot(r0[0] - e0[0], r0[1] - e0[1])
    rows = max(4, int(drop / 3.2))
    n_s = int(math.hypot(e1[0] - e0[0], e1[1] - e0[1]) * 2) + 1
    n_t = int(drop * 2) + 2
    for si in range(n_s + 1):
        s = si / n_s
        bx = e0[0] + (e1[0] - e0[0]) * s
        by = e0[1] + (e1[1] - e0[1]) * s
        tx = r0[0] + (r1[0] - r0[0]) * s
        ty = r0[1] + (r1[1] - r0[1]) * s
        for ti in range(n_t + 1):
            t = ti / n_t
            x = bx + (tx - bx) * t
            y = by + (ty - by) * t
            row = int(t * rows)
            colu = int(s * n_s / 2.0) + (row % 2) * 3
            n = value_noise(colu * 1.3, row * 2.7, 23.0)
            c = ramp[2] if n > 0.45 else ramp[1]
            if n > 0.82:
                c = ramp[3]
            fr = t * rows - row
            if fr < 0.22:
                c = ramp[0]
            if (colu % 6) == 0:
                c = shade(c + (255,), 0.82)[:3]
            px(im, x, y, shade(c + (255,), dark))
    line(im, r0[0], r0[1], r1[0], r1[1], shade(ramp[1] + (255,), 0.9), w=2)
    line(im, r0[0], r0[1] - 1, r1[0], r1[1] - 1, ramp[3] + (255,))


def _chimney(im, cx, base_y, height, width=10, fire=False):
    for i in range(height):
        y = base_y - i
        w = width - (i * 2) // height
        for dx in range(-w // 2, w // 2 + 1):
            fx = dx + w // 2
            c = _b_stone(fx + 3, i, height, dx < 0, sd=2.0)
            px(im, cx + dx, y, c)
    top = base_y - height
    cw = width + 2 - 2
    for dx in range(-cw // 2 - 1, cw // 2 + 2):
        px(im, cx + dx, top, STONE[3] + (255,))
        px(im, cx + dx, top + 1, STONE[1] + (255,))
    for dx in range(-cw // 2 + 1, cw // 2):
        px(im, cx + dx, top + 2, (24, 18, 20, 255))
    if fire:
        disc(im, cx, top + 1, cw / 2 - 0.5, 2.2, (224, 120, 40, 255))
        disc(im, cx, top, cw / 3, 1.6, (252, 190, 90, 255))
        for fdx, fdy in ((-2, -2), (1, -3), (3, -1), (0, -5), (-3, -4)):
            px(im, cx + fdx, top + fdy, (252, 170, 70, 230))
        for sdx, sdy in ((2, -8), (0, -11), (3, -14)):
            disc(im, cx + sdx, top + sdy, 2.2, 1.6, (70, 68, 74, 120))


def make_building(W, H, wall_h, roof_h, style="timber", sd=0.0, door_fx=None,
                  windows_left=(), windows_right=(), chimney=None, gable_window=False,
                  extra_top=18, roof_ramp=None):
    bw = (W + H) * 32
    bh = (W + H) * 16 + wall_h + roof_h + extra_top
    im = new(bw, bh)
    S = (32 * W, bh - 2)
    Wc = (S[0] - 32 * W, S[1] - 16 * W)
    Ec = (S[0] + 32 * H, S[1] - 16 * H)
    # --- left (SW) face ---
    def ybot_l(x):
        return Wc[1] + (x - Wc[0]) * 0.5
    def ybot_r(x):
        return S[1] - (x - S[0]) * 0.5
    for x in range(Wc[0], S[0]):
        yb = int(ybot_l(x))
        fx = x - Wc[0]
        for yy in range(wall_h):
            px(im, x, yb - wall_h + 1 + yy, _face_color(style, fx, yy, wall_h, True, sd))
    for x in range(S[0], Ec[0] + 1):
        yb = int(ybot_r(x))
        fx = x - S[0]
        for yy in range(wall_h):
            px(im, x, yb - wall_h + 1 + yy, _face_color(style, fx, yy, wall_h, False, sd))
    # door + windows
    if door_fx is not None:
        _draw_face_door(im, lambda fxx: Wc[0] + fxx, ybot_l, door_fx, wall_h)
    for wfx in windows_left:
        _draw_face_window(im, lambda fxx: Wc[0] + fxx, ybot_l, wfx, wall_h)
    for wfx in windows_right:
        _draw_face_window(im, lambda fxx: S[0] + fxx, ybot_r, wfx, wall_h)
    # --- roof ---
    Wt = (Wc[0], Wc[1] - wall_h)
    St = (S[0], S[1] - wall_h)
    Et = (Ec[0], Ec[1] - wall_h)
    Nt = (Wt[0] + 32 * H, Wt[1] - 16 * H)
    A = ((Wt[0] + Nt[0]) / 2, (Wt[1] + Nt[1]) / 2 - roof_h)
    B = ((St[0] + Et[0]) / 2, (St[1] + Et[1]) / 2 - roof_h)
    # eave overhang: push eave edges outward/down a bit
    def overhang(e, r, amt=3.0):
        d = (e[0] - r[0], e[1] - r[1])
        l = math.hypot(*d)
        return (e[0] + d[0] / l * amt, e[1] + d[1] / l * amt)
    Wt_o = overhang(Wt, A)
    St_o = overhang(St, B)
    Nt_o = overhang(Nt, A)
    Et_o = overhang(Et, B)
    # back plane first (mostly hidden), then gable, then front plane
    _fill_roof_plane(im, Nt_o, Et_o, A, B, dark=0.62, ramp=roof_ramp)
    _fill_gable(im, St, Et, (B[0], B[1] + 2), style, sd, lit_window=gable_window)
    _fill_roof_plane(im, Wt_o, St_o, A, B, dark=1.0, ramp=roof_ramp)
    # fascia under front eave
    line(im, Wt_o[0], Wt_o[1] + 1, St_o[0], St_o[1] + 1, TIMBER[0] + (255,))
    if chimney:
        ch_h, fire = chimney
        _chimney(im, int(B[0]), int(B[1] + 8), ch_h, 12 if fire else 8, fire=fire)
    return outline(im)


def well_sprite():
    im = new(52, 56)
    # stone ring
    for a in range(40):
        ang = a / 40 * math.tau
        x = 26 + math.cos(ang) * 14
        y = 44 + math.sin(ang) * 7
        disc(im, x, y, 2.6, 2.0, STONE[1 if a % 2 else 2] + (255,))
    disc(im, 26, 42, 9, 4.5, (16, 18, 26, 255))  # dark water hole
    px(im, 23, 41, (60, 80, 100, 255))
    # posts + tiny slate roof
    rect(im, 12, 18, 14, 40, TIMBER[1] + (255,))
    rect(im, 38, 18, 40, 40, TIMBER[1] + (255,))
    rect(im, 12, 18, 12, 40, TIMBER[2] + (255,))
    for i in range(8):
        for dx in range(-(16 - i), 17 - i):
            c = SLATE[2] if (dx + i) % 5 else SLATE[0]
            px(im, 26 + dx, 16 - i, c + (255,))
    line(im, 26, 18, 26, 30, (200, 195, 180, 255))  # rope
    rect(im, 24, 30, 28, 34, WOOD[1] + (255,))      # bucket
    rect(im, 24, 30, 28, 30, WOOD[3] + (255,))
    return with_shadow(outline(im), 26, 46, 16, 5)


def lamp_post_sprite():
    im = new(22, 58)
    rect(im, 10, 12, 12, 52, TIMBER[1] + (255,))
    rect(im, 10, 12, 10, 52, TIMBER[2] + (255,))
    disc(im, 11, 53, 5, 2.2, STONE[1] + (255,))
    # lantern box
    rect(im, 7, 4, 15, 13, TIMBER[0] + (255,))
    rect(im, 8, 5, 14, 12, (252, 196, 106, 255))
    rect(im, 9, 6, 13, 9, (255, 224, 150, 255))
    px(im, 11, 2, TIMBER[0] + (255,))
    rect(im, 10, 3, 12, 3, TIMBER[0] + (255,))
    return with_shadow(outline(im), 11, 54, 7, 2.6)


def barrel_sprite():
    im = new(26, 30)
    for y in range(6, 27):
        t = (y - 6) / 21.0
        wdt = int(9 + 2.6 * math.sin(t * math.pi))
        for dx in range(-wdt, wdt + 1):
            c = WOOD[2] if (dx + 13) % 4 else WOOD[1]
            if dx > wdt - 3:
                c = WOOD[0]
            elif dx < -wdt + 2:
                c = WOOD[3]
            px(im, 13 + dx, y, c + (255,))
    for hy in (9, 16, 23):
        for dx in range(-12, 13):
            if im.getpixel((13 + dx, hy))[3] > 0:
                px(im, 13 + dx, hy, IRON[0 if dx > 4 else 1] + (255,))
    disc(im, 13, 6, 9, 3, WOOD[1] + (255,))
    disc(im, 13, 6, 7, 2.2, WOOD[2] + (255,))
    return with_shadow(outline(im), 13, 27, 11, 3)


def crate_sprite():
    im = new(26, 26)
    rect(im, 3, 6, 22, 23, WOOD[1] + (255,))
    for x in range(3, 23, 4):
        line(im, x, 6, x, 23, WOOD[0] + (255,))
    for edge in ((3, 6, 22, 6), (3, 23, 22, 23), (3, 6, 3, 23), (22, 6, 22, 23)):
        line(im, *edge, TIMBER[1] + (255,))
    line(im, 3, 6, 22, 23, TIMBER[1] + (255,))
    line(im, 4, 6, 23, 23, TIMBER[2] + (255,))
    px(im, 4, 7, IRON[2] + (255,))
    px(im, 21, 7, IRON[2] + (255,))
    px(im, 4, 22, IRON[2] + (255,))
    px(im, 21, 22, IRON[2] + (255,))
    return with_shadow(outline(im), 13, 24, 11, 3)


def market_stall(stripe):
    im = new(56, 52)
    # table
    for y in range(14):
        for x in range(44):
            if in_diamond(x, y, 44, 14):
                c = WOOD[2] if value_noise(x, y, 31.0) < 0.7 else WOOD[3]
                px(im, x + 6, y + 30, c + (255,))
    for y in range(14):
        for x in range(44):
            if in_diamond(x, y, 44, 14) and not in_diamond(x, y + 1, 44, 14):
                px(im, x + 6, y + 31, WOOD[0] + (255,))
                px(im, x + 6, y + 32, WOOD[1] + (255,))
    # goods on the table
    for gx, gy, gc in ((18, 34, (150, 44, 40)), (21, 33, (170, 60, 48)), (24, 35, (150, 44, 40)),
                       (33, 33, (168, 150, 110)), (37, 35, (148, 130, 96))):
        disc(im, gx, gy, 1.8, 1.4, gc + (255,))
    rect(im, 30, 31, 35, 34, (160, 142, 104, 255))  # sack
    # posts
    for lx, ly in ((8, 34), (48, 34), (20, 42), (40, 42)):
        rect(im, lx - 1, ly - 22, lx, ly + 4, TIMBER[1] + (255,))
        px(im, lx - 1, ly - 22, TIMBER[2] + (255,))
    # striped awning (sloped iso sheet)
    for y in range(16):
        for x in range(48):
            if in_diamond(x, y, 48, 16):
                stripe_i = ((x + y * 2) // 5) % 2
                c = stripe if stripe_i == 0 else (210, 198, 176)
                sh = 1.0 - y / 28.0
                px(im, x + 4, y + 6 - (x // 14), shade(c + (255,), sh))
    return with_shadow(outline(im), 28, 46, 20, 5)


def castle_keep():
    """Massive crenellated stone keep, 5x4 tile footprint, with banner."""
    W, H = 5, 4
    wall_h = 62
    bw = (W + H) * 32
    bh = (W + H) * 16 + wall_h + 46
    im = new(bw, bh)
    S = (32 * W, bh - 2)
    Wc = (S[0] - 32 * W, S[1] - 16 * W)
    Ec = (S[0] + 32 * H, S[1] - 16 * H)

    def ybot_l(x):
        return Wc[1] + (x - Wc[0]) * 0.5

    def ybot_r(x):
        return S[1] - (x - S[0]) * 0.5

    for x in range(Wc[0], S[0]):
        yb = int(ybot_l(x))
        for yy in range(wall_h):
            px(im, x, yb - wall_h + 1 + yy, _b_stone(x - Wc[0], yy, wall_h, True, sd=20.0))
    for x in range(S[0], Ec[0] + 1):
        yb = int(ybot_r(x))
        for yy in range(wall_h):
            px(im, x, yb - wall_h + 1 + yy, _b_stone(x - S[0], yy, wall_h, False, sd=21.0))
    # arrow slits
    for fx_c, leftface in ((40, True), (104, True), (50, False), (100, False)):
        for lvl in (0.32, 0.62):
            for dy in range(7):
                x = (Wc[0] + fx_c) if leftface else (S[0] + fx_c)
                yb = ybot_l(x) if leftface else ybot_r(x)
                px(im, x, int(yb - wall_h * lvl) + dy, (16, 14, 18, 255))
                px(im, x + 1, int(yb - wall_h * lvl) + dy, (30, 28, 34, 255))
    # gate: tall arch on the left face center
    gate_c = S[0] - 56
    for dx in range(-8, 9):
        x = gate_c + dx
        yb = int(ybot_l(x))
        hgt = 24 - max(0, abs(dx) - 4) * 3
        for i in range(hgt):
            c = WOOD[1] if ((x + i // 9) % 3) else WOOD[0]
            if i == hgt - 1:
                c = TIMBER[0]
            if i % 7 == 6:
                c = IRON[0]  # iron bands
            px(im, x, yb - i, c + (255,))
    px(im, gate_c + 3, int(ybot_l(gate_c + 3)) - 10, (196, 168, 76, 255))
    # top walkway: fill the actual top quad (Wt, Nt, Et, St)
    Wt = (Wc[0], Wc[1] - wall_h)
    St = (S[0], S[1] - wall_h)
    Et = (Ec[0], Ec[1] - wall_h)
    Nt = (Wt[0] + 32 * H, Wt[1] - 16 * H)

    def _sign(a, b, p):
        return (b[0] - a[0]) * (p[1] - a[1]) - (b[1] - a[1]) * (p[0] - a[0])

    def _in_quad(p, q0, q1, q2, q3):
        for tri in ((q0, q1, q2), (q0, q2, q3)):
            d0 = _sign(tri[0], tri[1], p)
            d1 = _sign(tri[1], tri[2], p)
            d2 = _sign(tri[2], tri[0], p)
            neg = (d0 < 0) or (d1 < 0) or (d2 < 0)
            pos = (d0 > 0) or (d1 > 0) or (d2 > 0)
            if not (neg and pos):
                return True
        return False

    def _merlons(a, b, behind=False):
        steps = int(math.hypot(b[0] - a[0], b[1] - a[1]))
        for t10 in range(0, steps - 4, 10):
            mx = a[0] + (b[0] - a[0]) * t10 / steps
            my = a[1] + (b[1] - a[1]) * t10 / steps
            for dx in range(6):
                for dy in range(8):
                    c = _b_stone(int(mx) + dx, dy, 9, not behind, sd=24.0)
                    if behind:
                        c = shade(c, 0.8)
                    px(im, mx + dx, my - 13 + dy, c)

    # back merlons first (peek over the far edge), then deck, then front merlons
    _merlons(Wt, Nt, behind=True)
    _merlons(Nt, Et, behind=True)
    ymin = int(Nt[1])
    ymax = int(St[1])
    for y in range(ymin, ymax + 1):
        for x in range(Wt[0], Et[0] + 1):
            if _in_quad((x + 0.5, y + 0.5), Wt, Nt, Et, St):
                n = value_noise(x * 0.8, y * 1.3, 25.0)
                c = STONE[2] if n > 0.5 else STONE[1]
                if ((x + y * 2) % 9) == 0:
                    c = STONE[0]
                px(im, x, y, c + (255,))
    # central pyramid roof over an inset quad
    C = ((Wt[0] + Et[0]) / 2.0, (Wt[1] + Et[1]) / 2.0)
    inset = 0.42

    def _lerp_pt(p, q, t):
        return (p[0] + (q[0] - p[0]) * t, p[1] + (q[1] - p[1]) * t)

    iW = _lerp_pt(Wt, C, inset)
    iN = _lerp_pt(Nt, C, inset)
    iE = _lerp_pt(Et, C, inset)
    iS = _lerp_pt(St, C, inset)
    apex = (C[0], C[1] - 24)
    _fill_roof_plane(im, iW, iN, apex, apex, dark=0.55)
    _fill_roof_plane(im, iN, iE, apex, apex, dark=0.55)
    _fill_roof_plane(im, iW, iS, apex, apex, dark=1.0)
    _fill_roof_plane(im, iS, iE, apex, apex, dark=0.75)
    _merlons(Wt, St)
    _merlons(St, Et)
    # banner above the roof peak
    line(im, apex[0], apex[1], apex[0], apex[1] - 14, TIMBER[0] + (255,))
    for fy in range(5):
        for fxp in range(10 - fy * 2):
            px(im, apex[0] + 1 + fxp, apex[1] - 13 + fy, (150, 40, 38, 255))
    px(im, apex[0] + 2, apex[1] - 12, (186, 70, 56, 255))
    return outline(im)


def round_tower():
    """Cylindrical stone watchtower with a conical slate roof and pennant."""
    im = new(48, 96)
    cx = 24
    r = 15
    for y in range(34, 88):
        for dx in range(-r, r + 1):
            fx = dx + r
            yy = y - 34
            c = _b_stone(fx, yy, 54, dx < 1, sd=30.0)
            # cylindrical shading
            f = 1.0 - abs(dx / (r + 1.0)) * 0.35
            if dx > r - 4:
                f *= 0.8
            elif dx < -r + 3:
                f *= 1.08
            px(im, cx + dx, y, shade(c, f))
    # base ellipse
    disc(im, cx, 88, r + 1, 4, STONE[0] + (255,))
    # arrow slit + small lit window
    for dy in range(6):
        px(im, cx - 2, 52 + dy, (16, 14, 18, 255))
        px(im, cx - 1, 52 + dy, (30, 28, 34, 255))
    rect(im, cx + 4, 66, cx + 6, 70, (250, 192, 102, 255))
    rect(im, cx + 3, 65, cx + 7, 65, TIMBER[0] + (255,))
    # conical slate roof
    for i in range(22):
        t = i / 22.0
        wdt = int((r + 4) * (1 - t))
        y = 34 - i
        for dx in range(-wdt, wdt + 1):
            row = i // 3
            n = value_noise((dx + wdt) * 1.2, row * 2.9, 23.0)
            c = SLATE[2] if n > 0.45 else SLATE[1]
            if i % 3 == 0:
                c = SLATE[0]
            f = 1.0 - max(0, dx) / (wdt + 1.0) * 0.3
            px(im, cx + dx, y, shade(c + (255,), f))
    # pennant
    line(im, cx, 12, cx, 4, TIMBER[0] + (255,))
    for fy in range(4):
        for fxp in range(7 - fy * 2):
            px(im, cx + 1 + fxp, 5 + fy, (150, 40, 38, 255))
    return with_shadow(outline(im), cx, 89, r + 3, 5)


def fence_sprite():
    """Post-and-rail fence along the NW-SE iso axis (flip_h for the other)."""
    im = new(64, 44)
    def base_y(x):
        return 26 + (x - 4) * 12.0 / 56.0
    for px_, post_h in ((6, 13), (32, 12), (58, 13)):
        by = base_y(px_)
        rect(im, px_ - 1, by - post_h, px_ + 1, by, TIMBER[1] + (255,))
        rect(im, px_ - 1, by - post_h, px_ - 1, by, TIMBER[2] + (255,))
        px(im, px_, by - post_h, WOOD[3] + (255,))
    for rail_off in (9, 4):
        for x in range(4, 61):
            y = base_y(x) - rail_off
            c = WOOD[2] if (x % 9) else WOOD[1]
            px(im, x, y, c + (255,))
            px(im, x, y + 1, WOOD[1] + (255,))
    return with_shadow(outline(im), 32, 39, 26, 4, alpha=45)


def cart_sprite():
    im = new(56, 46)
    disc(im, 38, 34, 6.5, 6.5, TIMBER[1] + (255,))
    disc(im, 38, 34, 4.5, 4.5, WOOD[1] + (255,))
    for y in range(16):
        for x in range(40):
            if in_diamond(x, y, 40, 16):
                c = WOOD[2] if ((x + y * 2) % 7) else WOOD[1]
                px(im, x + 6, y + 18, c + (255,))
    for y in range(16):
        for x in range(40):
            if in_diamond(x, y, 40, 16) and not in_diamond(x, y + 1, 40, 16):
                px(im, x + 6, y + 19, WOOD[0] + (255,))
                px(im, x + 6, y + 20, WOOD[1] + (255,))
    rngh = random.Random(3)
    disc(im, 26, 22, 13, 6, (152, 128, 62, 255))
    disc(im, 24, 20, 9, 4.4, (176, 150, 76, 255))
    for i in range(26):
        hx = 26 + rngh.randint(-12, 12)
        hy = 21 + rngh.randint(-5, 5)
        px(im, hx, hy, (196, 170, 90, 255) if rngh.random() < 0.5 else (140, 116, 56, 255))
    disc(im, 16, 38, 7, 7, TIMBER[0] + (255,))
    disc(im, 16, 38, 5, 5, WOOD[1] + (255,))
    disc(im, 16, 38, 1.6, 1.6, IRON[1] + (255,))
    line(im, 16, 33, 16, 43, TIMBER[1] + (255,))
    line(im, 11, 38, 21, 38, TIMBER[1] + (255,))
    line(im, 44, 28, 54, 24, WOOD[2] + (255,), w=2)
    line(im, 6, 30, 2, 34, WOOD[2] + (255,), w=2)
    return with_shadow(outline(im), 28, 42, 22, 5)


def woodpile_sprite():
    im = new(42, 30)
    rngw = random.Random(5)
    for n, ring_r, by in [(4, 5, 24), (3, 4, 19), (2, 3, 14)]:
        for i in range(n):
            cx = 21 + (i - (n - 1) / 2.0) * 9
            line(im, cx, by, cx + 7, by - 4, WOOD[1] + (255,), w=2)
            disc(im, cx, by, 4, 4, WOOD[2] + (255,))
            disc(im, cx, by, 2.4, 2.4, WOOD[3] + (255,))
            px(im, cx, by, WOOD[1] + (255,))
            if rngw.random() < 0.5:
                px(im, cx - 1, by - 1, WOOD[3] + (255,))
    return with_shadow(outline(im), 21, 27, 17, 4)


def sacks_sprite():
    im = new(30, 24)
    for sx, sy, r in ((9, 16, 6), (20, 17, 5), (14, 11, 5)):
        disc(im, sx, sy, r, r * 0.9, (150, 128, 95, 255))
        disc(im, sx - 1, sy - 2, r * 0.6, r * 0.5, (172, 150, 114, 255))
        rect(im, sx - 1, sy - r - 1, sx + 1, sy - r + 1, (124, 104, 76, 255))
        px(im, sx, sy - r - 2, (104, 86, 62, 255))
    return with_shadow(outline(im), 15, 21, 12, 3)


def make_clutter():
    """Tiny ground decals scattered across the map for density."""
    out = {}
    im = new(12, 12)  # white/yellow meadow flowers
    for fx, fy in ((3, 7), (8, 5), (6, 9)):
        line(im, fx, fy, fx, fy + 2, GRASS[2] + (255,))
        px(im, fx, fy - 1, (224, 218, 200, 255))
        px(im, fx - 1, fy, (224, 218, 200, 255))
        px(im, fx + 1, fy, (224, 218, 200, 255))
        px(im, fx, fy, (208, 174, 78, 255))
    out["flower_a"] = im
    im = new(12, 12)  # red poppies
    for fx, fy in ((4, 6), (8, 9)):
        line(im, fx, fy, fx, fy + 2, GRASS[2] + (255,))
        px(im, fx, fy - 1, (160, 56, 48, 255))
        px(im, fx - 1, fy, (138, 44, 40, 255))
        px(im, fx + 1, fy, (138, 44, 40, 255))
    out["flower_b"] = im
    im = new(12, 8)  # pebbles
    for px_, py, r in ((3, 5, 1.6), (8, 4, 1.4), (6, 6, 1.2)):
        disc(im, px_, py, r, r * 0.8, STONE[1] + (255,))
        px(im, px_ - 1, py - 1, STONE[2] + (255,))
    out["pebbles"] = im
    im = new(12, 12)  # tall grass tuft
    for i, bx in enumerate((3, 5, 7, 9)):
        h = 4 + (i % 2) * 3
        line(im, bx, 11, bx + (1 if i % 2 else -1), 11 - h, GRASS[2 + (i % 2)] + (255,))
    out["tuft"] = im
    im = new(14, 10)  # fallen leaves
    rngl = random.Random(8)
    for i in range(8):
        lx, ly = rngl.randint(1, 12), rngl.randint(1, 8)
        c = (120, 96, 50, 255) if rngl.random() < 0.5 else (96, 84, 44, 255)
        px(im, lx, ly, c)
        if rngl.random() < 0.5:
            px(im, lx + 1, ly, shade(c, 0.85))
    out["leaves"] = im
    im = new(16, 10)  # dark stain / wear on roads
    rngs = random.Random(9)
    for i in range(22):
        sx, sy = rngs.randint(1, 14), rngs.randint(1, 8)
        if (sx - 8) ** 2 / 49.0 + (sy - 5) ** 2 / 16.0 <= 1.0:
            px(im, sx, sy, (30, 26, 28, rngs.randint(36, 80)))
    out["stain"] = im
    for name, img in out.items():
        save(img, "clutter/%s.png" % name)


def garden_sprites():
    """Three growth stages for the buildable garden plot."""
    def plot_base():
        im = new(64, 40)
        for y in range(TILE_H):
            for x in range(64):
                if in_diamond(x, y):
                    yy = (x + y * 2) % 8
                    c = DIRT[1] if yy < 5 else DIRT[0]
                    if value_noise(x, y, 27.0) > 0.8:
                        c = DIRT[2]
                    px(im, x, y + 8, c + (255,))
        # wooden border
        for y in range(TILE_H):
            for x in range(64):
                if in_diamond(x, y) and not in_diamond(x, y + 1):
                    px(im, x, y + 8, WOOD[1] + (255,))
                if in_diamond(x, y) and not in_diamond(x, y - 1):
                    px(im, x, y + 7, WOOD[0] + (255,))
        return im

    save(outline(plot_base()), "buildables/garden_plot.png")
    im = plot_base()
    rng = random.Random(11)
    for sx, sy in ((22, 22), (32, 18), (42, 23), (27, 27), (37, 27), (32, 23)):
        line(im, sx, sy, sx, sy - 2, GRASS[2] + (255,))
        px(im, sx - 1, sy - 2, GRASS[3] + (255,))
        px(im, sx + 1, sy - 1, GRASS[2] + (255,))
    save(outline(im), "buildables/garden_sprout.png")
    im = plot_base()
    for bx, by in ((22, 20), (33, 16), (42, 21), (28, 26)):
        draw_canopy(im, bx, by, 4, LEAF, rng)
        for i in range(4):
            fx = bx + rng.randint(-3, 3)
            fy = by + rng.randint(-2, 2)
            px(im, fx, fy, (146, 38, 42, 255))
            px(im, fx + 1, fy, (176, 62, 58, 255))
    save(outline(im), "buildables/garden_ready.png")


def crow_sheet():
    """Tiny crow: 2 ground frames (peck), 2 flight frames."""
    sheet = new(12 * 4, 12)
    for f in range(4):
        im = new(12, 12)
        if f < 2:
            # standing / pecking
            head_y = 4 if f == 0 else 6
            disc(im, 5, 8, 2.6, 1.8, (24, 22, 30, 255))      # body
            px(im, 7, 7, (38, 36, 46, 255))
            disc(im, 7 if f == 0 else 8, head_y, 1.4, 1.4, (24, 22, 30, 255))
            px(im, 9, head_y, (188, 150, 60, 255))           # beak
            px(im, 7, head_y - 1, (210, 205, 200, 255))      # eye glint
            px(im, 4, 10, (30, 28, 36, 255))
            px(im, 6, 10, (30, 28, 36, 255))
            px(im, 2, 7, (32, 30, 40, 255))                  # tail
        else:
            # flying: wings up / down
            disc(im, 6, 6, 2.4, 1.5, (24, 22, 30, 255))
            px(im, 8, 5, (188, 150, 60, 255))
            wing_y = 2 if f == 2 else 9
            line(im, 5, 6, 2, wing_y, (30, 28, 38, 255), w=2)
            line(im, 7, 6, 10, wing_y, (30, 28, 38, 255), w=2)
        sheet.paste(outline(im), (f * 12, 0))
    return sheet


def make_town_buildings():
    save(make_building(3, 3, 30, 26, "timber", sd=0.0, door_fx=48,
                       windows_left=(20,), windows_right=(28, 62), chimney=(16, False)),
         "buildings/cottage_a.png")
    save(make_building(3, 3, 30, 24, "timber", sd=5.0, door_fx=40,
                       windows_left=(70,), windows_right=(30,), chimney=None,
                       gable_window=True, roof_ramp=REDTILE),
         "buildings/cottage_b.png")
    save(make_building(5, 3, 38, 30, "mixed", sd=9.0, door_fx=80,
                       windows_left=(28, 52, 120), windows_right=(30, 62),
                       chimney=(18, False), gable_window=True, roof_ramp=REDTILE),
         "buildings/tavern.png")
    save(make_building(4, 3, 32, 24, "stone", sd=13.0, door_fx=64,
                       windows_left=(30,), windows_right=(40,), chimney=(34, True)),
         "buildings/forge.png")
    save(castle_keep(), "buildings/castle_keep.png")
    save(round_tower(), "buildings/round_tower.png")
    save(make_building(6, 3, 40, 30, "mixed", sd=17.0, door_fx=96,
                       windows_left=(30, 60, 140, 170), windows_right=(30, 62),
                       chimney=(20, False), gable_window=True, roof_ramp=REDTILE),
         "buildings/manor.png")
    save(well_sprite(), "buildings/well.png")
    save(lamp_post_sprite(), "buildings/lamp_post.png")
    garden_sprites()
    save(crow_sheet(), "props/crow.png")
    save(fence_sprite(), "props/fence.png")
    save(cart_sprite(), "props/cart.png")
    save(woodpile_sprite(), "props/woodpile.png")
    save(sacks_sprite(), "props/sacks.png")
    make_clutter()
    save(market_stall((150, 44, 40)), "props/stall_red.png")
    save(market_stall((178, 142, 54)), "props/stall_yellow.png")
    save(barrel_sprite(), "props/barrel.png")
    save(crate_sprite(), "props/crate.png")


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

    make_town_buildings()
    make_item_icons()
    fx_assets()
    project_icon()
    print("done")


if __name__ == "__main__":
    main()
