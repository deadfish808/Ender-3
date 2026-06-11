extends CharacterBody2D
## The walking dead. Wanders by day, hunts by night, bashes down defenses.

const TYPES := {
	"walker": {"speed": 40.0, "hp": 40.0, "dmg": 9.0, "structure_dmg": 6.0, "xp": 10,
			"tint": Color(1, 1, 1), "scale": 1.0},
	"runner": {"speed": 88.0, "hp": 28.0, "dmg": 7.0, "structure_dmg": 4.0, "xp": 14,
			"tint": Color(1.05, 0.95, 0.8), "scale": 0.95},
	"brute": {"speed": 32.0, "hp": 150.0, "dmg": 20.0, "structure_dmg": 18.0, "xp": 30,
			"tint": Color(0.8, 0.85, 0.8), "scale": 1.3},
}

const DROPS := [["essence", 0.22], ["cloth", 0.18], ["iron_scrap", 0.10], ["berries", 0.06]]

var type := "walker"
var speed := 40.0
var hp := 40.0
var max_hp := 40.0
var dmg := 9.0
var structure_dmg := 6.0
var xp_value := 10

var _aggro := false
var _aggro_memory := 0.0
var _think := 0.0
var _wander_dir := Vector2.ZERO
var _move_dir := Vector2.ZERO
var _separation := Vector2.ZERO
var _anim_lock := 0.0
var _base_scale := 1.0
var _attack_cd := 0.0
var _bash_cd := 0.0
var _slow_mult := 1.0
var _slow_time := 0.0
var _lurch := 0.0
var _t := 0.0
var _avoid_dir := Vector2.ZERO
var _avoid_time := 0.0

var _sprite: AnimatedSprite2D
var _bar: Node2D
var facing := "s"


func setup(p_type: String) -> void:
	type = p_type
	var cfg: Dictionary = TYPES[type]
	speed = cfg["speed"] * randf_range(0.85, 1.15)
	hp = cfg["hp"]
	max_hp = hp
	dmg = cfg["dmg"]
	structure_dmg = cfg["structure_dmg"]
	xp_value = cfg["xp"]


func _ready() -> void:
	add_to_group("zombies")
	collision_layer = 4
	collision_mask = 1 | 2 | 4
	var shape := CollisionShape2D.new()
	var circle := CircleShape2D.new()
	circle.radius = 6.0
	shape.shape = circle
	shape.position = Vector2(0, -4)
	add_child(shape)
	var cfg: Dictionary = TYPES[type]
	var tex: Texture2D = load("res://assets/chars/zombie_sheet.png")
	var player_script := preload("res://scripts/player/Player.gd")
	_sprite = AnimatedSprite2D.new()
	_sprite.sprite_frames = player_script.build_char_frames(tex)
	_sprite.offset = Vector2(0, -22)
	_sprite.modulate = cfg["tint"]
	_base_scale = cfg["scale"]
	_sprite.scale = Vector2.ONE * _base_scale
	_sprite.animation = "walk_s"
	add_child(_sprite)
	_sprite.play("walk_s")
	_sprite.speed_scale = randf_range(0.8, 1.2)
	_bar = preload("res://scripts/ui/HealthBar.gd").new()
	_bar.position = Vector2(0, -34)
	add_child(_bar)
	_think = randf() * 0.3
	_lurch = randf() * TAU


func _physics_process(delta: float) -> void:
	_attack_cd = maxf(0.0, _attack_cd - delta)
	_bash_cd = maxf(0.0, _bash_cd - delta)
	_anim_lock = maxf(0.0, _anim_lock - delta)
	if _slow_time > 0.0:
		_slow_time -= delta
		if _slow_time <= 0.0:
			_slow_mult = 1.0
			_sprite.modulate = TYPES[type]["tint"]
	_think -= delta
	if _think <= 0.0:
		_think = 0.25
		_think_tick()

	var player = Game.player
	var desired := Vector2.ZERO
	if _aggro and player and is_instance_valid(player) and not player.dead:
		desired = (player.position - position).normalized()
	else:
		desired = _wander_dir
	desired += _separation
	if _avoid_time > 0.0:
		_avoid_time -= delta
		desired += _avoid_dir * 1.3
	# smooth steering: zombies turn rather than snap
	_move_dir = _move_dir.lerp(desired, 1.0 - exp(-7.0 * delta))
	var move := _move_dir
	move.y *= 0.6
	# shambling lurch: walkers surge and stall instead of gliding
	_t += delta
	var lurch_mult := 1.0
	if type != "runner":
		lurch_mult = 0.55 + 0.55 * maxf(0.0, sin(_t * 2.4 + _lurch))
	if Game.is_night():
		lurch_mult *= 1.15
	velocity = move * speed * _slow_mult * lurch_mult
	move_and_slide()
	_steer_around_obstacles()
	_update_anim(move)

	if _aggro and player and is_instance_valid(player) and not player.dead:
		if position.distance_to(player.position) < 26.0 and _attack_cd <= 0.0:
			_attack_cd = 1.1
			_play_lunge((player.position - position).normalized())
			player.take_damage(dmg, position)
		elif _bash_cd <= 0.0:
			_bash_structures()


func _think_tick() -> void:
	var player = Game.player
	if player == null or not is_instance_valid(player) or player.dead:
		_aggro = false
		if randf() < 0.15:
			_wander_dir = Vector2.from_angle(randf() * TAU) if randf() < 0.7 else Vector2.ZERO
		return
	_separation = _compute_separation()
	var dist := position.distance_to(player.position)
	var aggro_range := 150.0
	if Game.is_night():
		aggro_range = 300.0
	if type == "runner":
		aggro_range += 60.0
	if dist < aggro_range:
		_aggro = true
		_aggro_memory = 10.0
	else:
		_aggro_memory -= 0.25
		if _aggro_memory <= 0.0:
			_aggro = false
	if not _aggro and randf() < 0.12:
		_wander_dir = Vector2.from_angle(randf() * TAU) if randf() < 0.7 else Vector2.ZERO


func _steer_around_obstacles() -> void:
	if not _aggro or _avoid_time > 0.0:
		return
	for i in get_slide_collision_count():
		var col := get_slide_collision(i)
		var node := col.get_collider()
		if node == null or node.is_in_group("structures") or node == Game.player:
			continue  # structures get bashed, not avoided
		var normal := col.get_normal()
		var side := signf(normal.cross(_move_dir))
		if side == 0.0:
			side = 1.0
		_avoid_dir = normal.rotated(side * PI / 2.0)
		_avoid_time = 0.6
		return


func _compute_separation() -> Vector2:
	var push := Vector2.ZERO
	for z in get_tree().get_nodes_in_group("zombies"):
		if z == self:
			continue
		var d: float = position.distance_to(z.position)
		if d < 18.0 and d > 0.01:
			push += (position - z.position) / d * (1.0 - d / 18.0)
	return push * 0.8


func _play_lunge(dir: Vector2) -> void:
	facing = "s"
	if absf(dir.x) > absf(dir.y) * 1.2:
		facing = "e" if dir.x > 0 else "w"
	elif dir.y < 0:
		facing = "n"
	_sprite.flip_h = facing == "w"
	_sprite.play("attack_melee_" + ("e" if facing == "w" else facing))
	_anim_lock = 0.25


func _bash_structures() -> void:
	for i in get_slide_collision_count():
		var col := get_slide_collision(i)
		var node := col.get_collider()
		if node and node.is_in_group("structures"):
			_bash_cd = 1.0
			_play_lunge((node.position - position).normalized())
			node.damage(structure_dmg)
			return


func _update_anim(move: Vector2) -> void:
	if _anim_lock > 0.0:
		return
	if move.length() < 4.0:
		if String(_sprite.animation).begins_with("walk_"):
			_sprite.play("idle_" + ("e" if facing == "w" else facing))
		return
	facing = "s"
	if absf(move.x) > absf(move.y) * 1.2:
		facing = "e" if move.x > 0 else "w"
	elif move.y < 0:
		facing = "n"
	_sprite.flip_h = facing == "w"
	var anim := "walk_" + ("e" if facing == "w" else facing)
	if _sprite.animation != anim:
		_sprite.play(anim)


func hit(amount: float, from_pos: Vector2, knockback: float) -> void:
	if hp <= 0.0:
		return
	hp -= amount
	_aggro = true
	_aggro_memory = 12.0
	_bar.update_bar(hp, max_hp)
	Game.play_sfx("zombie_hit", -6.0)
	FX.float_text(get_parent(), position, str(int(amount)), Color(1, 0.85, 0.4))
	if knockback > 0.0:
		position += (position - from_pos).normalized() * knockback * 0.12
	_sprite.modulate = Color(1.6, 1.2, 1.2)
	_sprite.scale = Vector2.ONE * _base_scale * 1.12
	var tw := create_tween()
	tw.set_parallel(true)
	tw.tween_property(_sprite, "modulate", TYPES[type]["tint"] if _slow_time <= 0.0 else Color(0.6, 0.8, 1.4), 0.18)
	tw.tween_property(_sprite, "scale", Vector2.ONE * _base_scale, 0.15)
	if hp <= 0.0:
		_die()


func apply_slow(mult: float, duration: float) -> void:
	_slow_mult = mult
	_slow_time = duration
	_sprite.modulate = Color(0.6, 0.8, 1.4)


func _die() -> void:
	FX.blood(get_parent(), position)
	FX.blood_decal(position)
	var corpse_tex: Texture2D = _sprite.sprite_frames.get_frame_texture("idle_" + ("e" if facing == "w" else facing), 0)
	FX.corpse(get_parent(), position, corpse_tex, _sprite.flip_h, TYPES[type]["tint"])
	Game.play_sfx("zombie", -8.0, 0.25)
	Game.add_xp(xp_value)
	Game.kills += 1
	var night_bonus := 0.10 if Game.is_night() else 0.0
	for drop in DROPS:
		var chance: float = drop[1] + (night_bonus if drop[0] == "essence" else 0.0)
		if randf() < chance:
			Game.world.spawn_pickup(drop[0], 1, position + Vector2(randf_range(-10, 10), randf_range(-6, 6)))
	queue_free()
