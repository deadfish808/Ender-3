extends StaticBody2D
## A lootable chest found in ruins.

const LOOT := [
	["cloth", 1, 3], ["iron_scrap", 1, 3], ["essence", 1, 2], ["arrow", 3, 8],
	["rope", 1, 2], ["salve", 1, 1], ["plank", 1, 3], ["bandage", 1, 3],
]

var opened := false
var _sprite: Sprite2D


func _ready() -> void:
	add_to_group("interactable")
	collision_layer = 1
	collision_mask = 0
	_sprite = Sprite2D.new()
	_sprite.texture = load("res://assets/props/chest_closed.png")
	_sprite.scale = Vector2(0.5, 0.5)
	_sprite.offset = Vector2(0, -26)
	add_child(_sprite)
	var shape := CollisionShape2D.new()
	var circle := CircleShape2D.new()
	circle.radius = 8.0
	shape.shape = circle
	add_child(shape)


func interact(_player: Node) -> void:
	if opened:
		return
	opened = true
	_sprite.texture = load("res://assets/props/chest_open.png")
	Game.play_sfx("craft")
	Game.add_xp(8)
	var drops := maxi(1, roundi(randi_range(2, 3) * Game.setting("loot")))
	for i in drops:
		var entry: Array = LOOT[randi() % LOOT.size()]
		var count := randi_range(int(entry[1]), int(entry[2]))
		var offset := Vector2(randf_range(-20, 20), randf_range(12, 24))
		Game.world.spawn_pickup(entry[0], count, position + offset)


func interact_hint() -> String:
	return "" if opened else "open chest"
