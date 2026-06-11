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

var tilemap: TileMapLayer
var entities: Node2D
var build_manager: Node2D
var hud: CanvasLayer
var canvas_mod: CanvasModulate

var walkable: Dictionary = {}   # Vector2i -> bool (terrain passable)
var occupied: Dictionary = {}   # Vector2i -> Node (structure / resource)

var rng := RandomNumberGenerator.new()
var _spawn_timer := 0.0
var _groan_timer := 0.0


func _ready() -> void:
	Game.world = self
	rng.randomize()
	_build_tilemap()
	entities = Node2D.new()
	entities.name = "Entities"
	entities.y_sort_enabled = true
	add_child(entities)
	_generate_terrain()
	_scatter_resources()
	_build_ruins()
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
	for i in [0, 1, 2, 3, 4, 5, 6, 9, 10]:  # 7, 8 are water animation frames
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


func _atlas(i: int) -> Vector2i:
	return Vector2i(i % 5, i / 5)


func _generate_terrain() -> void:
	var height := FastNoiseLite.new()
	height.seed = rng.randi()
	height.frequency = 0.035
	var detail := FastNoiseLite.new()
	detail.seed = rng.randi()
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
			elif e < -0.30:
				idx = T_SAND
				walkable[tile] = true
			elif detail.get_noise_2d(x, y) > 0.42:
				idx = T_DIRT[absi(x * 3 + y * 5) % 2]
				walkable[tile] = true
			else:
				idx = T_GRASS[absi(x * 11 + y * 17) % 3]
				walkable[tile] = true
			tilemap.set_cell(tile, 0, _atlas(idx))


func _scatter_resources() -> void:
	var forest := FastNoiseLite.new()
	forest.seed = rng.randi()
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
	var center := Vector2i(MAP_SIZE / 2, MAP_SIZE / 2)
	var tile := _find_walkable_near(center)
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
	return true


func free_tile(tile: Vector2i) -> void:
	occupied.erase(tile)


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
