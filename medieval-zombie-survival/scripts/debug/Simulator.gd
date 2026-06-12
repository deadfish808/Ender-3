extends Node
## Headless balance-testing bot. Enabled via MZS_SIM=<mode> env var.
## Drives the real player through Input actions at accelerated time and
## prints CSV telemetry for balance analysis.
##
## Modes:
##   idle    - stays around the town square, fights only in self-defense
##   gather  - works the survival loop: chop, forage, eat, warm up at night
##   hunt    - actively seeks and fights zombies
## Env: MZS_SIM_SPEED (default 8), MZS_SIM_DAYS (default 3)

var mode := "gather"
var sim_days := 3
var _think := 0.0
var _log_t := 0.0
var _target: Node2D = null
var _target_pos := Vector2.ZERO
var _deaths := 0
var _trees_felled := 0
var _fish := 0
var _breaks := 0
var _home := Vector2.ZERO


func _ready() -> void:
	mode = OS.get_environment("MZS_SIM")
	sim_days = int(OS.get_environment("MZS_SIM_DAYS")) if OS.get_environment("MZS_SIM_DAYS") != "" else 3
	var speed := 8.0
	if OS.get_environment("MZS_SIM_SPEED") != "":
		speed = float(OS.get_environment("MZS_SIM_SPEED"))
	Engine.time_scale = speed
	_home = Game.player.position
	Game.player.died.connect(func(): _deaths += 1)
	print("SIMSTART,mode=%s,days=%d,speed=%.0f" % [mode, sim_days, speed])
	print("SIMHDR,day,clock,hp,hunger,stamina,level,kills,zombies,wood,food,bleeding,cold,weapon,cond")


func _process(delta: float) -> void:
	var player = Game.player
	if player == null or not is_instance_valid(player):
		return
	if Game.day > sim_days:
		_finish()
		return
	if player.dead:
		_finish()
		return
	_log_t -= delta
	if _log_t <= 0.0:
		_log_t = Game.setting("day_length") / 12.0 / Engine.time_scale * Engine.time_scale
		_log_t = Game.setting("day_length") / 12.0  # every 2 in-game hours
		_emit_log(player)
	_think -= delta
	if _think <= 0.0:
		_think = 0.25
		_tick(player)


func _emit_log(player) -> void:
	var food := int(player.inventory.get("berries", 0)) + int(player.inventory.get("mushroom", 0)) \
			+ int(player.inventory.get("raw_fish", 0)) * 2 + int(player.inventory.get("cooked_fish", 0)) * 3 \
			+ int(player.inventory.get("stew", 0)) * 3
	print("SIM,%d,%s,%.0f,%.0f,%.0f,%d,%d,%d,%d,%d,%d,%d,%s,%d" % [
		Game.day, Game.clock_text(), player.hp, player.hunger, player.stamina,
		Game.level, Game.kills, get_tree().get_nodes_in_group("zombies").size(),
		int(player.inventory.get("wood", 0)), food,
		1 if player.bleeding else 0, 1 if player.cold else 0,
		player.equipped if player.equipped != "" else "fists",
		player.weapon_condition(player.equipped) if player.equipped != "" else 100,
	])


func _finish() -> void:
	var player = Game.player
	print("SIMEND,days_survived=%d,deaths=%d,level=%d,kills=%d,hp=%.0f,trees=%d,breaks=%d" % [
		Game.day, _deaths, Game.level, Game.kills,
		player.hp if player and is_instance_valid(player) else 0.0, _trees_felled, _breaks])
	get_tree().quit()


# ----------------------------------------------------------------- brain ----
func _tick(player) -> void:
	_release_all()
	# 1. survival reflexes
	if player.bleeding:
		if player.inventory.get("bandage", 0) == 0 and player.inventory.get("fiber", 0) >= 2:
			player.remove_item("fiber", 2)
			player.add_item("bandage", 1)
		if player.inventory.get("bandage", 0) > 0:
			player.use_item("bandage")
	if player.infected and player.inventory.get("remedy", 0) > 0:
		player.use_item("remedy")
	if player.hunger < 45.0:
		for food in ["stew", "cooked_fish", "berries", "raw_fish", "mushroom"]:
			if player.inventory.get(food, 0) > 0:
				player.use_item(food)
				break
	# 2. threats
	var hunt_range := 700.0 if not Game.is_night() else 200.0  # even hunters respect the dark
	var threat := _nearest_zombie(player.position, 150.0 if mode != "hunt" else hunt_range)
	if threat:
		_fight(player, threat)
		return
	# 3. cold at night: hug the nearest fire
	if player.cold:
		var fire := _nearest_in_group(player.position, "warmth", 4000.0)
		if fire and player.position.distance_to(fire.position) > 90.0:
			_move_toward(player, fire.position)
			return
	# 4. mode behaviors
	match mode:
		"idle":
			if player.position.distance_to(_home) > 120.0:
				_move_toward(player, _home)
		"hunt":
			# patrol toward the city gate looking for trouble
			var gate: Vector2 = Game.world.tile_to_world(Vector2i(70, 42))
			if player.position.distance_to(gate) > 80.0:
				_move_toward(player, gate)
		"gather":
			_gather(player)


func _fight(player, threat: Node2D) -> void:
	player.aim_override = threat.position
	var d: float = player.position.distance_to(threat.position)
	var packed := _zombies_within(player.position, 50.0) >= 3
	if player.hp < player.max_hp() * 0.35 or packed:
		# retreat toward home/fire and swing at whatever follows
		_move_toward(player, _home, true)
		if d < 40.0:
			Input.action_press("attack")
		if packed and player.stamina > 30.0:
			Input.action_press("dodge")
		return
	if d > 34.0:
		_move_toward(player, threat.position)
	else:
		Input.action_press("attack")


func _gather(player) -> void:
	# keep a working stock of wood, then food from bushes
	var want_wood: bool = player.inventory.get("wood", 0) < 18
	var kind_filter := ["tree_oak", "tree_pine"] if want_wood else ["bush"]
	if _target == null or not is_instance_valid(_target):
		_target = _nearest_harvestable(player.position, kind_filter)
		if _target == null:
			_target = _nearest_harvestable(player.position, ["tree_oak", "tree_pine", "bush", "rock_big", "rock_small"])
	if _target == null:
		_move_toward(player, _home)
		return
	var d: float = player.position.distance_to(_target.position)
	player.aim_override = _target.position
	if d > 36.0:
		_move_toward(player, _target.position)
	else:
		Input.action_press("attack")
		if _target.has_method("hit") and _target.hits_left <= 1:
			_trees_felled += 1
			_target = null


# --------------------------------------------------------------- helpers ----
func _move_toward(player, pos: Vector2, keep_aim := false) -> void:
	if not keep_aim:
		player.aim_override = pos
	var d: Vector2 = pos - player.position
	if absf(d.x) > 10.0:
		Input.action_press("move_right" if d.x > 0 else "move_left")
	if absf(d.y) > 8.0:
		Input.action_press("move_down" if d.y > 0 else "move_up")


func _release_all() -> void:
	for a in ["move_up", "move_down", "move_left", "move_right", "attack", "dodge", "sprint"]:
		Input.action_release(a)


func _nearest_zombie(pos: Vector2, radius: float) -> Node2D:
	var best: Node2D = null
	var best_d := radius
	for z in get_tree().get_nodes_in_group("zombies"):
		var d: float = pos.distance_to(z.position)
		if d < best_d:
			best = z
			best_d = d
	return best


func _zombies_within(pos: Vector2, radius: float) -> int:
	var n := 0
	for z in get_tree().get_nodes_in_group("zombies"):
		if pos.distance_to(z.position) < radius:
			n += 1
	return n


func _nearest_in_group(pos: Vector2, group: String, radius: float) -> Node2D:
	var best: Node2D = null
	var best_d := radius
	for n in get_tree().get_nodes_in_group(group):
		var d: float = pos.distance_to(n.position)
		if d < best_d:
			best = n
			best_d = d
	return best


func _nearest_harvestable(pos: Vector2, kinds: Array) -> Node2D:
	var best: Node2D = null
	var best_d := 2000.0
	for h in get_tree().get_nodes_in_group("harvestable"):
		if not (h.kind in kinds) or h.depleted:
			continue
		var d: float = pos.distance_to(h.position)
		if d < best_d:
			best = h
			best_d = d
	return best
