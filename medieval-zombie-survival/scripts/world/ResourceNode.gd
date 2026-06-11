extends StaticBody2D
## Harvestable world prop: trees, rocks, bushes, mushrooms, ruin walls.
## Hit it with any attack to gather materials.

const CONFIG := {
	"tree_oak": {"texture": "res://assets/props/tree_oak.png", "hits": 5, "offset": -88.0,
			"yield": [["wood", 1.0]], "radius": 7.0, "blocks": true},
	"tree_pine": {"texture": "res://assets/props/tree_pine.png", "hits": 5, "offset": -88.0,
			"yield": [["wood", 1.0]], "radius": 7.0, "blocks": true},
	"rock_big": {"texture": "res://assets/props/rock_big.png", "hits": 5, "offset": -28.0,
			"yield": [["stone", 1.0], ["flint", 0.25], ["iron_scrap", 0.12]], "radius": 10.0, "blocks": true},
	"rock_small": {"texture": "res://assets/props/rock_small.png", "hits": 3, "offset": -18.0,
			"yield": [["stone", 1.0], ["flint", 0.3]], "radius": 8.0, "blocks": true},
	"bush": {"texture": "res://assets/props/bush_berry.png", "hits": 3, "offset": -24.0,
			"yield": [["berries", 1.0], ["fiber", 0.55]], "radius": 0.0, "blocks": false, "regrow": 75.0,
			"empty_texture": "res://assets/props/bush_empty.png"},
	"mushrooms": {"texture": "res://assets/props/mushrooms.png", "hits": 1, "offset": -14.0,
			"yield": [["mushroom", 1.0], ["mushroom", 0.4]], "radius": 0.0, "blocks": false, "regrow": 90.0},
	"ruin_wall": {"texture": "res://assets/props/ruin_wall.png", "hits": 8, "offset": -32.0,
			"yield": [["stone", 1.0]], "radius": 16.0, "blocks": true},
	"ruin_wall2": {"texture": "res://assets/props/ruin_wall2.png", "hits": 8, "offset": -32.0,
			"yield": [["stone", 1.0]], "radius": 16.0, "blocks": true},
	"city_wall": {"texture": "res://assets/buildables/stone_wall.png", "hits": 25, "offset": -32.0,
			"yield": [["stone", 1.0]], "radius": 16.0, "blocks": true},
	"barrel": {"texture": "res://assets/props/barrel.png", "hits": 2, "offset": -26.0,
			"yield": [["wood", 0.8], ["cloth", 0.4], ["berries", 0.35]], "radius": 7.0, "blocks": true},
	"crate": {"texture": "res://assets/props/crate.png", "hits": 2, "offset": -22.0,
			"yield": [["wood", 0.8], ["flint", 0.35], ["arrow", 0.3]], "radius": 7.0, "blocks": true},
	"stall_red": {"texture": "res://assets/props/stall_red.png", "hits": 3, "offset": -42.0,
			"yield": [["berries", 0.7], ["cloth", 0.4], ["rope", 0.25]], "radius": 10.0, "blocks": true},
	"stall_yellow": {"texture": "res://assets/props/stall_yellow.png", "hits": 3, "offset": -42.0,
			"yield": [["mushroom", 0.6], ["fiber", 0.5], ["rope", 0.25]], "radius": 10.0, "blocks": true},
	"fence": {"texture": "res://assets/props/fence.png", "hits": 3, "offset": -28.0,
			"yield": [["wood", 0.9]], "radius": 9.0, "blocks": true},
	"fence_f": {"texture": "res://assets/props/fence.png", "hits": 3, "offset": -28.0,
			"yield": [["wood", 0.9]], "radius": 9.0, "blocks": true, "flip": true},
	"cart": {"texture": "res://assets/props/cart.png", "hits": 4, "offset": -38.0,
			"yield": [["wood", 0.8], ["rope", 0.3], ["fiber", 0.5]], "radius": 11.0, "blocks": true},
	"woodpile": {"texture": "res://assets/props/woodpile.png", "hits": 3, "offset": -24.0,
			"yield": [["wood", 1.0], ["wood", 0.6]], "radius": 9.0, "blocks": true},
	"sacks": {"texture": "res://assets/props/sacks.png", "hits": 2, "offset": -20.0,
			"yield": [["berries", 0.6], ["mushroom", 0.4], ["fiber", 0.4]], "radius": 7.0, "blocks": true},
}

var kind := ""
var tile := Vector2i.ZERO
var hits_left := 1
var depleted := false
var _sprite: Sprite2D
var _cfg: Dictionary


func setup(p_kind: String, p_tile: Vector2i) -> void:
	kind = p_kind
	tile = p_tile
	_cfg = CONFIG[kind]
	hits_left = _cfg["hits"]


func _ready() -> void:
	add_to_group("harvestable")
	collision_layer = 1
	collision_mask = 0
	_sprite = Sprite2D.new()
	_sprite.texture = load(_cfg["texture"])
	_sprite.scale = Vector2(0.5, 0.5)  # textures are 2x resolution, rendered at half scale for finer pixels
	_sprite.offset = Vector2(0, _cfg["offset"])
	_sprite.flip_h = _cfg.get("flip", false)
	add_child(_sprite)
	if _cfg["blocks"] and _cfg["radius"] > 0.0:
		var shape := CollisionShape2D.new()
		var circle := CircleShape2D.new()
		circle.radius = _cfg["radius"]
		shape.shape = circle
		shape.position = Vector2(0, -2)
		add_child(shape)


func hit(_dmg: float) -> void:
	if depleted:
		return
	hits_left -= 1
	Game.play_sfx("hit", -6.0)
	Game.add_xp(1)
	# drop one yield roll per hit
	for y in _cfg["yield"]:
		if randf() <= float(y[1]):
			var offset := Vector2(randf_range(-14, 14), randf_range(8, 18))
			Game.world.spawn_pickup(y[0], 1, position + offset)
	_shake()
	if hits_left <= 0:
		if _cfg.has("regrow"):
			_set_depleted(true)
			get_tree().create_timer(float(_cfg["regrow"])).timeout.connect(_regrow)
		else:
			Game.world.free_tile(tile)
			queue_free()


func _set_depleted(value: bool) -> void:
	depleted = value
	if _cfg.has("empty_texture"):
		_sprite.texture = load(_cfg["empty_texture"] if value else _cfg["texture"])
	else:
		_sprite.modulate.a = 0.0 if value else 1.0


func _regrow() -> void:
	if not is_inside_tree():
		return
	hits_left = _cfg["hits"]
	_set_depleted(false)


func _shake() -> void:
	var tw := create_tween()
	tw.tween_property(_sprite, "position:x", 2.0, 0.04)
	tw.tween_property(_sprite, "position:x", -2.0, 0.04)
	tw.tween_property(_sprite, "position:x", 0.0, 0.04)
