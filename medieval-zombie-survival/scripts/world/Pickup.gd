extends Area2D
## A dropped item lying on the ground. Drifts to the player when close.

var item := ""
var count := 1
var _sprite: Sprite2D
var _bob := 0.0


func setup(p_item: String, p_count: int) -> void:
	item = p_item
	count = p_count


func _ready() -> void:
	collision_layer = 0
	collision_mask = 2  # player
	monitorable = false
	var shape := CollisionShape2D.new()
	var circle := CircleShape2D.new()
	circle.radius = 12.0
	shape.shape = circle
	add_child(shape)
	_sprite = Sprite2D.new()
	_sprite.texture = ItemDB.icon(item)
	_sprite.scale = Vector2(0.5, 0.5)
	_sprite.offset = Vector2(0, -16)
	add_child(_sprite)
	_bob = randf() * TAU
	body_entered.connect(_on_body)


func _process(delta: float) -> void:
	_bob += delta * 3.0
	_sprite.position.y = sin(_bob) * 2.0
	var player = Game.player
	if player and is_instance_valid(player):
		var d := position.distance_to(player.position)
		if d < 48.0 and d > 6.0:
			position = position.move_toward(player.position, delta * 140.0)


func _on_body(body: Node) -> void:
	if body != Game.player:
		return
	body.add_item(item, count)
	Game.play_sfx("pickup", -6.0)
	var text := ItemDB.display_name(item) if count == 1 else "%s x%d" % [ItemDB.display_name(item), count]
	FX.float_text(get_parent(), position, "+ " + text, Color(0.9, 0.9, 0.75))
	queue_free()
