# CLAUDE.md — Medieval Zombie Survival

Isometric medieval zombie survival game (Project Zomboid-inspired) for
**Godot 4.3+**. Everything — art, audio, world, UI — is generated or built in
code. This file is the working context for continuing development.

## Quick orientation

- `project.godot` boots `scenes/Menu.tscn` (sandbox difficulty + background
  picker) → `scenes/Main.tscn` (root script `scripts/world/World.gd` builds
  the entire game at runtime; there are no other scene files).
- The map is **static**: fixed seeds in `World.gd` (`rng.seed`, noise seeds),
  with a hand-placed town (center, ~tile 48,48) and a walled city with castle
  (north, tiles 56..86 x 10..38). Tiles are isometric 64x32 world units.
- Design pillars: **no pausing**, **no enemy health bars or damage numbers**,
  noise attracts zombies, smart play (stealth, bows, rain windows, fire
  warmth, bandages) beats button mashing. Difficulty knobs live on the main
  menu and persist to `user://settings.cfg`.

## Architecture map

| Area | Files |
|---|---|
| Global state, input map, sandbox settings, backgrounds, SFX | `scripts/autoload/Game.gd` |
| Items, recipes, buildable defs | `scripts/autoload/ItemDB.gd` |
| Skill trees (Fighter/Archer/Mage) | `scripts/autoload/SkillTreeDB.gd` |
| One-shot FX, spritesheet helpers, decals, corpse/bobber | `scripts/autoload/FXLib.gd` |
| World gen, town/city, population, weather, noise heat, blending | `scripts/world/World.gd` |
| Player (movement, 3 weapon classes + fishing tool, survival stats, inventory, durability) | `scripts/player/Player.gd` |
| Zombie AI (walker/runner/brute, lurch, noise hearing, avoidance) | `scripts/enemies/Zombie.gd` |
| Player-built structures incl. gardens, doors, spikes | `scripts/world/Structure.gd` |
| Pre-built town buildings (multi-tile, lights, smoke) | `scripts/world/Building.gd` |
| Harvestables, props, city walls | `scripts/world/ResourceNode.gd` |
| UI (all built in code with `UIKit` styleboxes) | `scripts/ui/*` |
| Dev tools | `scripts/debug/Screenshots.gd`, `scripts/debug/Simulator.gd` |

## Critical invariants (break these and things silently misalign)

1. **All textures are 2x resolution, rendered at half scale.** Every
   `Sprite2D`/`AnimatedSprite2D` gets `scale = Vector2(0.5, 0.5)` and sprite
   `offset` values are in **2x texture pixels** (i.e., double the world-pixel
   offset). The TileMapLayers use `tile_size = 128x64` with node
   `scale = 0.5`. Never call `tilemap.map_to_local()` directly from outside —
   use `World.tile_to_world()` / `World.world_to_tile()`.
2. **Terrain atlas layout contract** (`tools/generate_assets.py`
   `build_terrain_atlas()` ↔ `World.gd` constants): indices 0-2 grass, 3-4
   dirt, 5 sand, 6 water (animated; 7-8 are its frames — never `create_tile`
   them), 9-10 cobbles, 11-26 fringe overlays ordered
   `[grass, dirt, sand, stone] x [nw, ne, sw, se]`.
3. **Character sheet layout** (`char_sheet()` ↔ `Player.build_char_frames()`):
   64x96 cells (after Scale2x), 9 cols x 6 rows; rows 0-2 = S/E/N with walk
   f0-5 + idle f6-7; rows 3-5 = attack_melee 0-2, attack_bow 3-5,
   attack_staff 6-8 (zombies repeat a lunge in all three slots). West = E
   flipped.
4. **Buildings**: node origin = south corner of the footprint diamond; in
   `Building.gd` the south point in texture space is `(64*w, tex_h - 4)`.
5. Y-sorted `entities` node holds everything living/standing; `decals` (blood,
   clutter) sits between ground and entities.

## GDScript gotchas already hit (don't repeat)

- `var x := untyped_expr` → **parse error** when the source is an untyped
  variable (e.g. duck-typed `player`). A failed parse in a preloaded script
  silently aborts the *caller's* `_ready` with only a console SCRIPT ERROR.
  Type the variable explicitly: `var d: float = ...`.
- Use `set_anchors_and_offsets_preset(...)`, not `set_anchors_preset(...)`,
  for programmatic full-rect Controls under a plain Control parent.
- `TileSetAtlasSource` must be added to the TileSet **before** creating tiles
  that need physics data.
- `StringName` lacks String methods: `String(_sprite.animation).begins_with()`.

## Workflows

```bash
# regenerate ALL pixel art (Scale2x pipeline) and SFX
python3 tools/generate_assets.py && python3 tools/generate_sfx.py

# headless validation (use an ABSOLUTE --path; cwd tricks have bitten before)
godot --headless --path /abs/path/to/medieval-zombie-survival --import
godot --headless --path /abs/... --quit-after 500   # boots to menu only!

# screenshots (menu auto-starts the game when MZS_SHOT_DIR is set)
MZS_SHOT_DIR=/tmp/shots xvfb-run -a -s "-screen 0 1280x720x24" \
  godot --path /abs/... --rendering-driver opengl3 --audio-driver Dummy
# writes 00_main_menu .. 08_city_overview, then quits

# balance sims: a bot plays the real game via Input actions (see docs/BALANCE.md)
MZS_SIM=gather MZS_SIM_DAYS=4 MZS_SIM_SPEED=16 \
  godot --headless --path /abs/... --audio-driver Dummy
# modes: idle | gather | hunt; prints SIM,... CSV rows + SIMEND summary
```

After any gameplay/art change: regenerate assets if the generator changed →
`--import` → headless run grepping for `SCRIPT ERROR` → screenshot pass →
(for balance work) re-run the three sims and compare against the table in
`docs/BALANCE.md`. Keep `docs/screenshots/` refreshed from the shot run.

## Balance state (verified by sims, Normal settings, 4-day runs)

idle play dies at the first horde night (night 4) — intended; the
gather loop is food-positive and survives indefinitely; hunting is viable but
dies if caught at night with empty reserves. If you touch hunger, bleeding,
night population, or horde timing, re-run the sims. Method + numbers:
`docs/BALANCE.md`.

## Backlog (rough priority)

1. Container looting & building interiors (search cupboards instead of smashing)
2. Skill-by-doing (swing swords to level swords; fishing levels fishing)
3. Zombie corpse looting + corpse burning (piles attract zombies)
4. Boarding up doorways with planks; castle interior with boss brute pack + treasure
5. NPC survivor in the tavern (trading/quests); ambient critters beyond crows
6. Save/load mid-run; minimap; gamepad support
7. Per-district population memory (city refills from edges, not uniformly)
8. Standalone exports (Windows/Linux) via Godot export templates

## Conventions

- GDScript: tabs, typed where inference fails, `##` doc comments on classes,
  snake_case; UI through `UIKit` helpers; sounds via `Game.play_sfx(name)`.
- Pixel art: muted palette in `generate_assets.py` (GRASS/DIRT/STONE/...),
  1px outline via `outline()`, soft shadows via `with_shadow()`, every sprite
  through `save()` (auto Scale2x except `NO_UPSCALE` set).
- Noise values: loud actions call `Game.world.alert_zombies(pos, radius)` —
  melee 130, bow 60, staff 200, explosion 480, build 150, door 90, sprint 90.
  Rain multiplies radii by 0.65. Noise also feeds the migration heat map.
