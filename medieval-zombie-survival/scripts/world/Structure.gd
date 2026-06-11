extends StaticBody2D
## A player-built defense or station. Zombies bash these down.

var item_id := ""
var tile := Vector2i.ZERO
var max_hp := 100.0
var hp := 100.0
var is_door := false
var door_open := false
var is_garden := false
var garden_state := "empty"  # empty -> growing -> ready
var _grow_left := 0.0

var _cfg: Dictionary
var _sprite: Node2D  # Sprite2D or AnimatedSprite2D
var _shape: CollisionShape2D
var _bar: Node2D
var _light: PointLight2D


func setup(p_item: String, p_tile: Vector2i) -> void:
	item_id = p_item
	tile = p_tile
	_cfg = ItemDB.BUILDABLES[item_id]
	max_hp = float(_cfg["hp"])
	hp = max_hp
	is_door = _cfg.get("door", false)
	is_garden = _cfg.get("garden", false)


func _ready() -> void:
	add_to_group("structures")
	add_to_group("interactable")
	if _cfg.has("station"):
		add_to_group("station_" + str(_cfg["station"]))
	collision_layer = 1
	collision_mask = 0
	if _cfg.get("frames", 0) > 0:
		var fs: Vector2i = _cfg["frame_size"]
		var anim := AnimatedSprite2D.new()
		anim.sprite_frames = FX.strip_frames(_cfg["texture"], fs.x, fs.y, _cfg["frames"], 8.0, true)
		anim.scale = Vector2(0.5, 0.5)
		anim.offset = Vector2(0, 32.0 - fs.y / 2.0)
		anim.animation = "play"
		add_child(anim)
		anim.play("play")
		_sprite = anim
	else:
		var spr := Sprite2D.new()
		spr.texture = load(_cfg["texture"])
		spr.scale = Vector2(0.5, 0.5)
		spr.offset = Vector2(0, 32.0 - spr.texture.get_height() / 2.0)
		add_child(spr)
		_sprite = spr
	if _cfg.get("blocks", false):
		_shape = CollisionShape2D.new()
		var poly := ConvexPolygonShape2D.new()
		poly.points = PackedVector2Array([
			Vector2(-30, 0), Vector2(0, -15), Vector2(30, 0), Vector2(0, 15),
		])
		_shape.shape = poly
		add_child(_shape)
	if is_garden:
		set_process(true)
	if _cfg.get("light", false):
		add_child(preload("res://scripts/world/Building.gd")._make_smoke(Vector2(0, -26)))
		var light := PointLight2D.new()
		light.texture = load("res://assets/fx/light.png")
		light.color = Color(1.0, 0.75, 0.45)
		light.energy = 1.1
		light.texture_scale = 1.6
		light.position = Vector2(0, -10)
		add_child(light)
	if _cfg.get("spikes", false):
		var area := Area2D.new()
		area.collision_layer = 0
		area.collision_mask = 4  # zombies
		var ashape := CollisionShape2D.new()
		var circle := CircleShape2D.new()
		circle.radius = 22.0
		ashape.shape = circle
		area.add_child(ashape)
		add_child(area)
		var timer := Timer.new()
		timer.wait_time = 0.5
		timer.autostart = true
		timer.timeout.connect(_spike_tick.bind(area))
		add_child(timer)
	_bar = preload("res://scripts/ui/HealthBar.gd").new()
	_bar.position = Vector2(0, -36)
	add_child(_bar)


func _process(delta: float) -> void:
	if _light:
		# firelight flicker
		_light.energy = 1.1 * (0.88 + 0.12 * sin(Time.get_ticks_msec() / 90.0 + position.x))
	if is_garden and garden_state == "growing":
		_grow_left -= delta
		if _grow_left <= 0.0:
			garden_state = "ready"
			(_sprite as Sprite2D).texture = load(_cfg["texture_ready"])


func _spike_tick(area: Area2D) -> void:
	var victims := area.get_overlapping_bodies()
	for body in victims:
		if body.is_in_group("zombies"):
			body.hit(9.0, position, 0.0)
			damage(1.0, true)  # spikes wear out
			if hp <= 0.0:
				return


func damage(amount: float, silent := false) -> void:
	hp -= amount
	_bar.update_bar(hp, max_hp)
	if not silent:
		Game.play_sfx("hit", -8.0)
		var tw := create_tween()
		tw.tween_property(_sprite, "position:x", 1.5, 0.04)
		tw.tween_property(_sprite, "position:x", 0.0, 0.04)
	if hp <= 0.0:
		Game.world.free_tile(tile)
		FX.blood(get_parent(), position)  # debris puff (reuses splat shape)
		Game.play_sfx("explosion", -10.0)
		queue_free()


func interact(player: Node) -> void:
	if is_garden:
		match garden_state:
			"empty":
				if player.inventory.get("berries", 0) >= 2:
					player.remove_item("berries", 2)
					garden_state = "growing"
					_grow_left = Game.setting("day_length") * 0.8
					(_sprite as Sprite2D).texture = load(_cfg["texture_sprout"])
					Game.play_sfx("build", -6.0)
					FX.float_text(get_parent(), position, "planted", Color(0.6, 1.0, 0.6))
				else:
					FX.float_text(get_parent(), position, "needs 2 berries", Color(0.9, 0.8, 0.6))
			"growing":
				FX.float_text(get_parent(), position, "still growing...", Color(0.7, 0.9, 0.7))
			"ready":
				garden_state = "empty"
				(_sprite as Sprite2D).texture = load(_cfg["texture"])
				var crop := randi_range(6, 10)
				Game.world.spawn_pickup("berries", crop, position + Vector2(0, 10))
				Game.add_xp(4)
				Game.play_sfx("pickup")
		return
	if is_door:
		door_open = not door_open
		_shape.set_deferred("disabled", door_open)
		(_sprite as Sprite2D).texture = load(_cfg["texture_open"] if door_open else _cfg["texture"])
		Game.play_sfx("door")
		Game.world.alert_zombies(position, 90.0)
		return
	# repair: 1 wood -> 30 hp
	if hp < max_hp and player.inventory.get("wood", 0) > 0:
		player.remove_item("wood", 1)
		hp = minf(hp + 30.0, max_hp)
		_bar.update_bar(hp, max_hp)
		Game.play_sfx("build", -4.0)
		FX.float_text(get_parent(), position, "repaired", Color(0.6, 1.0, 0.6))


func interact_hint() -> String:
	if is_door:
		return "close door" if door_open else "open door"
	if hp < max_hp:
		return "repair (1 wood)"
	return ""
