extends Node2D
## Main scene: procedural isometric island, day/night cycle, zombie spawning.

const MAP_SIZE := 96
const TILE := Vector2i(64, 32)

# terrain atlas indices (5 columns); water is one animated tile (frames 6-8)
const T_GRASS := [0, 1, 2]
const T_DIRT := [3, 4]
const T_SAND := 5
const T_WATER := 6
const T_STONE := [9, 10]

const ZOMBIE_CAP := 50

# terrain blending: higher priority materials bleed onto lower neighbors
const MAT_PRIORITY := {"grass": 4, "stone": 3, "dirt": 2, "sand": 1, "water": 0}
const FRINGE_BASE := 11
const FRINGE_MATS := ["grass", "dirt", "sand", "stone"]
# neighbor offset -> fringe direction index (nw/ne/sw/se), also overlay layer
const FRINGE_DIRS := {
	Vector2i(-1, 0): 0,  # neighbor up-left bleeds over our NW edge
	Vector2i(0, -1): 1,  # up-right -> NE
	Vector2i(0, 1): 2,   # down-left -> SW
	Vector2i(1, 0): 3,   # down-right -> SE
}

var tilemap: TileMapLayer
var overlays: Array = []        # 4 fringe TileMapLayers (nw/ne/sw/se)
var terrain_mat: Dictionary = {}  # Vector2i -> "grass"/"dirt"/"sand"/"water"/"stone"
var decals: Node2D
var entities: Node2D
var build_manager: Node2D
var hud: CanvasLayer
var canvas_mod: CanvasModulate

var walkable: Dictionary = {}   # Vector2i -> bool (terrain passable)
var occupied: Dictionary = {}   # Vector2i -> Node (structure / resource)

var rng := RandomNumberGenerator.new()
var _spawn_timer := 0.0
var _groan_timer := 0.0


const TOWN_CENTER := Vector2i(48, 48)
const TOWN_RECT_MIN := Vector2i(38, 38)
const TOWN_RECT_MAX := Vector2i(58, 58)
const CITY_MIN := Vector2i(56, 10)
const CITY_MAX := Vector2i(86, 38)


func _ready() -> void:
	Game.world = self
	rng.seed = 1370053  # the world is a fixed, static place
	_build_tilemap()
	decals = Node2D.new()
	decals.name = "Decals"
	add_child(decals)
	entities = Node2D.new()
	entities.name = "Entities"
	entities.y_sort_enabled = true
	add_child(entities)
	_generate_terrain()
	_scatter_resources()
	_build_ruins()
	_build_town()
	_build_city()
	_apply_blending()
	_scatter_clutter()
	_scatter_pickups()
	_spawn_player()
	build_manager = preload("res://scripts/world/BuildManager.gd").new()
	add_child(build_manager)
	canvas_mod = CanvasModulate.new()
	canvas_mod.color = Color.WHITE
	add_child(canvas_mod)
	hud = preload("res://scripts/ui/HUD.gd").new()
	add_child(hud)
	Game.day_started.connect(func(d): hud.announce("Day %d" % d, Color(1, 0.95, 0.7)))
	Game.night_started.connect(func(_d): hud.announce("Night falls... the dead stir", Color(0.7, 0.75, 1.0)))
	Game.level_gained.connect(func(l): hud.announce("Level %d — skill point earned [K]" % l, Color(0.6, 1.0, 0.6)))
	hud.announce("Day 1 — gather, craft, build. Survive the night.", Color(1, 0.95, 0.7))
	if OS.get_environment("MZS_SHOT_DIR") != "":
		add_child(preload("res://scripts/debug/Screenshots.gd").new())


func _process(delta: float) -> void:
	Game.advance_time(delta)
	_update_ambient()
	_spawn_timer -= delta
	if _spawn_timer <= 0.0:
		_spawn_timer = 2.5
		_try_spawn_zombie()
	_groan_timer -= delta
	if _groan_timer <= 0.0:
		_groan_timer = rng.randf_range(6.0, 14.0)
		if get_tree().get_nodes_in_group("zombies").size() > 0:
			Game.play_sfx("zombie", -12.0, 0.2)


# ------------------------------------------------------------- tilemap ------
func _build_tilemap() -> void:
	var ts := TileSet.new()
	ts.tile_shape = TileSet.TILE_SHAPE_ISOMETRIC
	ts.tile_layout = TileSet.TILE_LAYOUT_DIAMOND_DOWN
	ts.tile_size = TILE
	ts.add_physics_layer()
	ts.set_physics_layer_collision_layer(0, 1)
	ts.set_physics_layer_collision_mask(0, 0)
	var src := TileSetAtlasSource.new()
	src.texture = load("res://assets/tiles/terrain_atlas.png")
	src.texture_region_size = TILE
	ts.add_source(src, 0)
	var tile_ids := [0, 1, 2, 3, 4, 5, 6, 9, 10]
	for f_idx in range(FRINGE_BASE, FRINGE_BASE + 16):
		tile_ids.append(f_idx)
	for i in tile_ids:  # 7, 8 are water animation frames
		var coords := Vector2i(i % 5, i / 5)
		src.create_tile(coords)
		if i == T_WATER:
			src.set_tile_animation_columns(coords, 0)
			src.set_tile_animation_frames_count(coords, 3)
			for f in 3:
				src.set_tile_animation_frame_duration(coords, f, 0.5)
			var td := src.get_tile_data(coords, 0)
			td.add_collision_polygon(0)
			td.set_collision_polygon_points(0, 0, PackedVector2Array([
				Vector2(-32, 0), Vector2(0, -16), Vector2(32, 0), Vector2(0, 16),
			]))
	tilemap = TileMapLayer.new()
	tilemap.name = "Ground"
	tilemap.tile_set = ts
	add_child(tilemap)
	for d in 4:
		var ov := TileMapLayer.new()
		ov.name = "Fringe%d" % d
		ov.tile_set = ts
		add_child(ov)
		overlays.append(ov)


func _atlas(i: int) -> Vector2i:
	return Vector2i(i % 5, i / 5)


func _generate_terrain() -> void:
	var height := FastNoiseLite.new()
	height.seed = 91201
	height.frequency = 0.035
	var detail := FastNoiseLite.new()
	detail.seed = 4417
	detail.frequency = 0.13
	for x in MAP_SIZE:
		for y in MAP_SIZE:
			var tile := Vector2i(x, y)
			var e := height.get_noise_2d(x, y)
			var border: int = min(min(x, y), min(MAP_SIZE - 1 - x, MAP_SIZE - 1 - y))
			if border < 6:
				e -= (6 - border) * 0.13
			var idx: int
			if e < -0.38:
				idx = T_WATER
				walkable[tile] = false
				terrain_mat[tile] = "water"
			elif e < -0.30:
				idx = T_SAND
				walkable[tile] = true
				terrain_mat[tile] = "sand"
			elif detail.get_noise_2d(x, y) > 0.42:
				idx = T_DIRT[absi(x * 3 + y * 5) % 2]
				walkable[tile] = true
				terrain_mat[tile] = "dirt"
			else:
				idx = T_GRASS[absi(x * 11 + y * 17) % 3]
				walkable[tile] = true
				terrain_mat[tile] = "grass"
			tilemap.set_cell(tile, 0, _atlas(idx))


func _scatter_resources() -> void:
	var forest := FastNoiseLite.new()
	forest.seed = 77003
	forest.frequency = 0.07
	var center := Vector2i(MAP_SIZE / 2, MAP_SIZE / 2)
	for x in MAP_SIZE:
		for y in MAP_SIZE:
			var tile := Vector2i(x, y)
			if not walkable.get(tile, false) or occupied.has(tile):
				continue
			if Vector2(tile - center).length() < 5.0:
				continue
			var f := forest.get_noise_2d(x, y)
			var roll := rng.randf()
			var kind := ""
			if f > 0.18:
				if roll < 0.30:
					kind = "tree_oak" if rng.randf() < 0.55 else "tree_pine"
				elif roll < 0.33:
					kind = "mushrooms"
				elif roll < 0.35:
					kind = "bush"
			else:
				if roll < 0.012:
					kind = "tree_oak"
				elif roll < 0.030:
					kind = "rock_big" if rng.randf() < 0.5 else "rock_small"
				elif roll < 0.045:
					kind = "bush"
			if kind != "":
				_spawn_resource(kind, tile)


func _spawn_resource(kind: String, tile: Vector2i) -> void:
	var node := preload("res://scripts/world/ResourceNode.gd").new()
	node.setup(kind, tile)
	node.position = tilemap.map_to_local(tile)
	entities.add_child(node)
	occupied[tile] = node


func _build_ruins() -> void:
	for r in 3:
		var cx := rng.randi_range(14, MAP_SIZE - 15)
		var cy := rng.randi_range(14, MAP_SIZE - 15)
		if Vector2(cx - TOWN_CENTER.x, cy - TOWN_CENTER.y).length() < 20.0:
			continue
		if cx > CITY_MIN.x - 8 and cy < CITY_MAX.y + 8:
			continue
		var ok := true
		for dx in range(-3, 4):
			for dy in range(-3, 4):
				if not walkable.get(Vector2i(cx + dx, cy + dy), false):
					ok = false
		if not ok:
			continue
		for dx in range(-2, 3):
			for dy in range(-2, 3):
				var tile := Vector2i(cx + dx, cy + dy)
				tilemap.set_cell(tile, 0, _atlas(T_STONE[absi(dx * 3 + dy) % 2]))
				terrain_mat[tile] = "stone"
				var node: Node = occupied.get(tile)
				if node:
					occupied.erase(tile)
					node.queue_free()
				var on_edge: bool = absi(dx) == 2 or absi(dy) == 2
				if on_edge and rng.randf() < 0.55:
					_spawn_resource("ruin_wall" if rng.randf() < 0.5 else "ruin_wall2", tile)
		for c in rng.randi_range(1, 2):
			var ct := Vector2i(cx + rng.randi_range(-1, 1), cy + rng.randi_range(-1, 1))
			if not occupied.has(ct):
				var chest := preload("res://scripts/world/Chest.gd").new()
				chest.position = tilemap.map_to_local(ct)
				entities.add_child(chest)
				occupied[ct] = chest


func _scatter_pickups() -> void:
	var loot := ["wood", "wood", "wood", "stone", "stone", "flint", "berries", "mushroom", "fiber"]
	for i in 70:
		var tile := Vector2i(rng.randi_range(4, MAP_SIZE - 5), rng.randi_range(4, MAP_SIZE - 5))
		if walkable.get(tile, false) and not occupied.has(tile):
			spawn_pickup(loot[rng.randi() % loot.size()], 1, tilemap.map_to_local(tile))


func spawn_pickup(item: String, count: int, pos: Vector2) -> void:
	var p := preload("res://scripts/world/Pickup.gd").new()
	p.setup(item, count)
	p.position = pos
	entities.add_child(p)


func _spawn_player() -> void:
	var tile := _find_walkable_near(TOWN_CENTER + Vector2i(-2, 2))
	var player := preload("res://scripts/player/Player.gd").new()
	player.position = tilemap.map_to_local(tile)
	entities.add_child(player)
	Game.player = player


func _find_walkable_near(start: Vector2i) -> Vector2i:
	for radius in 20:
		for dx in range(-radius, radius + 1):
			for dy in range(-radius, radius + 1):
				var t := start + Vector2i(dx, dy)
				if walkable.get(t, false) and not occupied.has(t):
					return t
	return start


# ---------------------------------------------------------------- town ------
func _clear_tile(t: Vector2i) -> void:
	var node: Node = occupied.get(t)
	if node:
		occupied.erase(t)
		node.queue_free()


func _pave(t: Vector2i, idx: int) -> void:
	tilemap.set_cell(t, 0, _atlas(idx))
	terrain_mat[t] = "stone" if idx in T_STONE else "dirt"
	walkable[t] = true
	_clear_tile(t)


func _build_town() -> void:
	# terraform: make sure the whole town footprint is dry land
	for x in range(TOWN_RECT_MIN.x, TOWN_RECT_MAX.x + 1):
		for y in range(TOWN_RECT_MIN.y, TOWN_RECT_MAX.y + 1):
			var t := Vector2i(x, y)
			_clear_tile(t)
			if not walkable.get(t, false):
				tilemap.set_cell(t, 0, _atlas(T_GRASS[absi(x * 11 + y * 17) % 3]))
				terrain_mat[t] = "grass"
				walkable[t] = true
	# cobbled plaza
	for x in range(44, 52):
		for y in range(44, 52):
			_pave(Vector2i(x, y), T_STONE[absi(x + y) % 2])
	# dirt roads leading out of the square
	for i in range(TOWN_RECT_MIN.x, TOWN_RECT_MAX.x + 1):
		for w in 2:
			var rx := Vector2i(i, 48 + w)
			var ry := Vector2i(48 + w, i)
			if rx.x < 44 or rx.x > 51:
				_pave(rx, T_DIRT[absi(rx.x) % 2])
			if ry.y < 44 or ry.y > 51:
				_pave(ry, T_DIRT[absi(ry.y) % 2])
	# buildings
	_place_building("cottage_a", Vector2i(41, 41))
	_place_building("forge", Vector2i(52, 43))
	_place_building("cottage_b", Vector2i(52, 52))
	_place_building("tavern", Vector2i(40, 52))
	_place_small("well", Vector2i(45, 45))
	for lamp_tile in [Vector2i(44, 44), Vector2i(51, 44), Vector2i(44, 51), Vector2i(51, 51)]:
		_place_small("lamp_post", lamp_tile)
	# market stalls and loose loot props
	for stall in [["stall_red", Vector2i(46, 50)], ["stall_yellow", Vector2i(50, 46)]]:
		_clear_tile(stall[1])
		_spawn_resource(stall[0], stall[1])
		walkable[stall[1]] = false
	for prop in [["barrel", Vector2i(44, 42)], ["barrel", Vector2i(51, 46)],
			["crate", Vector2i(45, 53)], ["crate", Vector2i(55, 46)],
			["barrel", Vector2i(50, 42)], ["crate", Vector2i(43, 51)]]:
		_clear_tile(prop[1])
		_spawn_resource(prop[0], prop[1])
	# street dressing: fences around the cottage gardens, a cart, firewood
	for fx in range(40, 44):
		_dress("fence", Vector2i(fx, 45))
	for fy in range(52, 55):
		_dress("fence_f", Vector2i(46, fy))
	_dress("cart", Vector2i(52, 47))
	_dress("woodpile", Vector2i(51, 42))
	_dress("sacks", Vector2i(45, 43))
	_dress("woodpile", Vector2i(44, 53))
	# a stocked chest by the forge
	var ct := Vector2i(55, 47)
	_clear_tile(ct)
	var chest := preload("res://scripts/world/Chest.gd").new()
	chest.position = tilemap.map_to_local(ct)
	entities.add_child(chest)
	occupied[ct] = chest


func _place_building(kind: String, top_left: Vector2i) -> void:
	var building_script := preload("res://scripts/world/Building.gd")
	var cfg: Dictionary = building_script.CONFIG[kind]
	var w := int(cfg["w"])
	var h := int(cfg["h"])
	var b := building_script.new()
	b.setup(kind)
	var south := top_left + Vector2i(w - 1, h - 1)
	b.position = tilemap.map_to_local(south) + Vector2(0, 16)
	entities.add_child(b)
	for dx in w:
		for dy in h:
			var t := top_left + Vector2i(dx, dy)
			_clear_tile(t)
			occupied[t] = b
			walkable[t] = false


func _place_small(kind: String, tile: Vector2i) -> void:
	var building_script := preload("res://scripts/world/Building.gd")
	var b := building_script.new()
	b.setup(kind)
	b.position = tilemap.map_to_local(tile)
	entities.add_child(b)
	_clear_tile(tile)
	occupied[tile] = b
	walkable[tile] = false


func _build_city() -> void:
	# terraform the whole walled city to dry land
	for x in range(CITY_MIN.x, CITY_MAX.x + 1):
		for y in range(CITY_MIN.y, CITY_MAX.y + 1):
			var t := Vector2i(x, y)
			_clear_tile(t)
			tilemap.set_cell(t, 0, _atlas(T_GRASS[absi(x * 11 + y * 17) % 3]))
			terrain_mat[t] = "grass"
			walkable[t] = true
	# perimeter walls with a south gate at x 69-71
	var gate_xs := [69, 70, 71]
	for x in range(CITY_MIN.x, CITY_MAX.x + 1):
		_city_wall(Vector2i(x, CITY_MIN.y))
		if not gate_xs.has(x):
			_city_wall(Vector2i(x, CITY_MAX.y))
	for y in range(CITY_MIN.y + 1, CITY_MAX.y):
		_city_wall(Vector2i(CITY_MIN.x, y))
		_city_wall(Vector2i(CITY_MAX.x, y))
	# watchtowers: corners, gate flanks, keep flanks
	for tt in [Vector2i(57, 11), Vector2i(85, 11), Vector2i(57, 37), Vector2i(85, 37),
			Vector2i(68, 37), Vector2i(72, 37), Vector2i(64, 14), Vector2i(73, 14)]:
		_clear_tile(tt)
		_place_small("round_tower", tt)
	# cobbled plaza + main street up from the gate
	for x in range(62, 79):
		for y in range(22, 33):
			_pave(Vector2i(x, y), T_STONE[absi(x + y) % 2])
	for y in range(33, 38):
		for w in 2:
			_pave(Vector2i(70 + w, y), T_DIRT[absi(y) % 2])
	# castle and buildings
	_place_building("castle_keep", Vector2i(66, 13))
	_place_building("manor", Vector2i(58, 24))
	_place_building("tavern", Vector2i(72, 33))
	_place_building("cottage_a", Vector2i(60, 33))
	_place_building("cottage_b", Vector2i(76, 18))
	_place_building("forge", Vector2i(80, 24))
	_place_small("well", Vector2i(70, 27))
	for lamp_tile in [Vector2i(63, 22), Vector2i(77, 22), Vector2i(63, 31), Vector2i(77, 31), Vector2i(69, 35)]:
		_clear_tile(lamp_tile)
		_place_small("lamp_post", lamp_tile)
	for stall in [["stall_red", Vector2i(67, 29)], ["stall_yellow", Vector2i(73, 29)],
			["stall_red", Vector2i(70, 23)]]:
		_clear_tile(stall[1])
		_spawn_resource(stall[0], stall[1])
		walkable[stall[1]] = false
	for prop in [["barrel", Vector2i(65, 24)], ["barrel", Vector2i(75, 25)], ["crate", Vector2i(64, 30)],
			["crate", Vector2i(76, 28)], ["barrel", Vector2i(71, 19)], ["crate", Vector2i(60, 27)],
			["barrel", Vector2i(81, 28)], ["crate", Vector2i(83, 22)]]:
		_clear_tile(prop[1])
		_spawn_resource(prop[0], prop[1])
	for ct in [Vector2i(68, 18), Vector2i(59, 28), Vector2i(82, 30)]:
		_clear_tile(ct)
		var chest := preload("res://scripts/world/Chest.gd").new()
		chest.position = tilemap.map_to_local(ct)
		entities.add_child(chest)
		occupied[ct] = chest
	# street dressing
	for fx in range(58, 62):
		_dress("fence", Vector2i(fx, 29))
	for fy in range(19, 22):
		_dress("fence_f", Vector2i(75, fy))
	_dress("cart", Vector2i(66, 34))
	_dress("cart", Vector2i(74, 21))
	_dress("woodpile", Vector2i(79, 21))
	_dress("woodpile", Vector2i(61, 19))
	_dress("sacks", Vector2i(65, 26))
	_dress("sacks", Vector2i(76, 30))
	_dress("sacks", Vector2i(72, 19))
	# the road from town to the city gate
	for x in range(58, 72):
		for w in 2:
			_pave(Vector2i(x, 48 + w), T_DIRT[absi(x) % 2])
	for y in range(39, 50):
		for w in 2:
			_pave(Vector2i(70 + w, y), T_DIRT[absi(y) % 2])
	# the city is overrun: it guards its loot
	for i in 12:
		var zx := 58 + (i * 7) % 26
		var zy := 13 + (i * 11) % 23
		var zt := Vector2i(zx, zy)
		if walkable.get(zt, false) and not occupied.has(zt):
			var z := preload("res://scripts/enemies/Zombie.gd").new()
			z.setup("brute" if i % 6 == 0 else "walker")
			z.position = tilemap.map_to_local(zt)
			entities.add_child(z)


func _city_wall(t: Vector2i) -> void:
	_clear_tile(t)
	_spawn_resource("city_wall", t)
	walkable[t] = false


var _clutter_cache: Dictionary = {}


## Sprinkle tiny ground decals: flowers, pebbles, tufts, leaves, road wear.
func _scatter_clutter() -> void:
	var grass_kinds := ["flower_a", "flower_b", "pebbles", "tuft", "tuft", "leaves"]
	for tile in terrain_mat:
		var m: String = terrain_mat[tile]
		var roll := rng.randf()
		if m == "grass":
			var node: Node = occupied.get(tile)
			if node == null and roll < 0.24:
				_add_clutter(grass_kinds[rng.randi() % grass_kinds.size()], tile)
			elif node != null and roll < 0.3:
				_add_clutter("leaves", tile)
		elif (m == "stone" or m == "dirt") and roll < 0.14:
			_add_clutter("stain", tile)


func _add_clutter(kind: String, tile: Vector2i) -> void:
	if not _clutter_cache.has(kind):
		_clutter_cache[kind] = load("res://assets/clutter/%s.png" % kind)
	var s := Sprite2D.new()
	s.texture = _clutter_cache[kind]
	s.position = tilemap.map_to_local(tile) + Vector2(rng.randf_range(-18, 18), rng.randf_range(-7, 7))
	s.flip_h = rng.randf() < 0.5
	decals.add_child(s)


## Place a dressing prop only on a free, walkable tile.
func _dress(kind: String, tile: Vector2i) -> void:
	if occupied.has(tile) or not walkable.get(tile, false):
		return
	_spawn_resource(kind, tile)


## Lay fringe tiles so higher-priority terrain bleeds over its neighbors.
func _apply_blending() -> void:
	for n in terrain_mat:
		var n_pri: int = MAT_PRIORITY.get(terrain_mat[n], 0)
		for off in FRINGE_DIRS:
			var t: Vector2i = n + off
			if not terrain_mat.has(t):
				continue
			var t_mat: String = terrain_mat[t]
			if MAT_PRIORITY.get(t_mat, 0) <= n_pri:
				continue
			var mi := FRINGE_MATS.find(t_mat)
			if mi < 0:
				continue
			var d: int = FRINGE_DIRS[off]
			overlays[d].set_cell(n, 0, _atlas(FRINGE_BASE + mi * 4 + d))


# ------------------------------------------------------------- zombies ------
func _try_spawn_zombie() -> void:
	if Game.player == null or not is_instance_valid(Game.player):
		return
	var count := get_tree().get_nodes_in_group("zombies").size()
	var desired: int
	if Game.is_night():
		desired = mini(10 + (Game.day - 1) * 4, ZOMBIE_CAP)
	else:
		desired = mini(4 + (Game.day - 1) * 2, ZOMBIE_CAP)
	if count >= desired:
		return
	for attempt in 12:
		var ang := rng.randf() * TAU
		var dist := rng.randf_range(650.0, 950.0)
		var pos: Vector2 = Game.player.position + Vector2(cos(ang), sin(ang) * 0.5) * dist
		var tile := tilemap.local_to_map(pos)
		if walkable.get(tile, false) and not occupied.has(tile):
			var z := preload("res://scripts/enemies/Zombie.gd").new()
			z.setup(_pick_zombie_type())
			z.position = tilemap.map_to_local(tile)
			entities.add_child(z)
			return


func _pick_zombie_type() -> String:
	var roll := rng.randf()
	var brute_chance := minf(0.05 + Game.day * 0.03, 0.3)
	var runner_chance := 0.25 if Game.is_night() else 0.08
	if roll < brute_chance:
		return "brute"
	if roll < brute_chance + runner_chance:
		return "runner"
	return "walker"


# ------------------------------------------------------------ building ------
func can_place(tile: Vector2i) -> bool:
	if not walkable.get(tile, false) or occupied.has(tile):
		return false
	var pos := tilemap.map_to_local(tile)
	if Game.player and is_instance_valid(Game.player) and Game.player.position.distance_to(pos) < 30.0:
		return false
	for z in get_tree().get_nodes_in_group("zombies"):
		if z.position.distance_to(pos) < 30.0:
			return false
	return true


func place_structure(item_id: String, tile: Vector2i) -> bool:
	if not can_place(tile):
		return false
	var s := preload("res://scripts/world/Structure.gd").new()
	s.setup(item_id, tile)
	s.position = tilemap.map_to_local(tile)
	entities.add_child(s)
	occupied[tile] = s
	Game.play_sfx("build")
	alert_zombies(s.position, 150.0)  # hammering carries
	return true


func free_tile(tile: Vector2i) -> void:
	occupied.erase(tile)


## Broadcast a noise: zombies in range shamble over to investigate.
func alert_zombies(pos: Vector2, radius: float) -> void:
	for z in get_tree().get_nodes_in_group("zombies"):
		if z.position.distance_to(pos) < radius:
			z.hear_noise(pos)


func station_nearby(tag: String) -> bool:
	if tag == "":
		return true
	if Game.player == null or not is_instance_valid(Game.player):
		return false
	for s in get_tree().get_nodes_in_group("station_" + tag):
		if s.position.distance_to(Game.player.position) < 120.0:
			return true
	return false


# ------------------------------------------------------------- ambient ------
func _update_ambient() -> void:
	var dark := Game.darkness()
	var day_col := Color(0.97, 0.95, 0.9)
	var night_col := Color(0.21, 0.24, 0.38)
	var c := day_col.lerp(night_col, dark)
	# muted dusk/dawn tint
	var warm := clampf(1.0 - absf(dark - 0.4) / 0.4, 0.0, 1.0) * 0.3
	c = c.lerp(Color(0.92, 0.7, 0.5), warm)
	canvas_mod.color = c


func game_over() -> void:
	hud.show_game_over()
