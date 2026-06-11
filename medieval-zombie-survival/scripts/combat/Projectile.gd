extends Area2D
## Arrows, firebolts and frost shards.

var kind := "arrow"
var dir := Vector2.RIGHT
var dmg := 10.0
var pierce := 0
var explode := false
var speed := 420.0
var _life := 1.4
var _hit_targets := {}


func setup(p_kind: String, p_dir: Vector2, p_dmg: float, p_pierce: int, p_explode: bool) -> void:
	kind = p_kind
	dir = p_dir.normalized()
	dmg = p_dmg
	pierce = p_pierce
	explode = p_explode
	if kind != "arrow":
		speed = 330.0


func _ready() -> void:
	collision_layer = 0
	collision_mask = 1 | 4  # world obstacles + zombies
	monitorable = false
	z_index = 30
	var shape := CollisionShape2D.new()
	var circle := CircleShape2D.new()
	circle.radius = 5.0
	shape.shape = circle
	add_child(shape)
	if kind == "arrow":
		var spr := Sprite2D.new()
		spr.texture = load("res://assets/fx/arrow.png")
		add_child(spr)
		rotation = dir.angle()
	else:
		var path := "res://assets/fx/firebolt.png" if kind == "fire" else "res://assets/fx/frostbolt.png"
		var anim := AnimatedSprite2D.new()
		anim.sprite_frames = FX.strip_frames(path, 14, 14, 3, 12.0, true)
		anim.animation = "play"
		add_child(anim)
		anim.play("play")
		var light := PointLight2D.new()
		light.texture = load("res://assets/fx/light.png")
		light.texture_scale = 0.25
		light.energy = 0.7
		light.color = Color(1.0, 0.6, 0.3) if kind == "fire" else Color(0.5, 0.7, 1.0)
		add_child(light)
	body_entered.connect(_on_body)


func _physics_process(delta: float) -> void:
	position += dir * speed * delta
	_life -= delta
	if _life <= 0.0:
		queue_free()


func _on_body(body: Node) -> void:
	if _hit_targets.has(body):
		return
	_hit_targets[body] = true
	if body.is_in_group("zombies"):
		body.hit(dmg, position - dir * 10.0, 30.0)
		if explode:
			_explode()
			return
		if pierce > 0:
			pierce -= 1
			return
		_finish()
	elif body is StaticBody2D:
		if body.is_in_group("structures") or body.is_in_group("harvestable"):
			if explode:
				_explode()
				return
			_finish()


func _finish() -> void:
	if kind == "arrow" and randf() < 0.35:
		Game.world.spawn_pickup("arrow", 1, position)
	queue_free()


func _explode() -> void:
	FX.explosion(get_parent(), position)
	Game.play_sfx("explosion", -8.0)
	Game.world.alert_zombies(position, 480.0)
	for z in get_tree().get_nodes_in_group("zombies"):
		if z.position.distance_to(position) < 46.0 and not _hit_targets.has(z):
			z.hit(dmg * 0.7, position, 60.0)
	queue_free()
