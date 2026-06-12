extends Node2D
## Ambient crow: pecks at the ground, flushes when anything comes close.
## A startled crow is information — something is moving over there.

var _sprite: AnimatedSprite2D
var _state := "ground"
var _check := 0.0
var _vel := Vector2.ZERO


func _ready() -> void:
	add_to_group("crows")
	_sprite = AnimatedSprite2D.new()
	var tex: Texture2D = load("res://assets/props/crow.png")
	var frames := SpriteFrames.new()
	frames.remove_animation("default")
	for anim in [["ground", 0, 2, 2.2], ["fly", 2, 2, 11.0]]:
		frames.add_animation(anim[0])
		frames.set_animation_speed(anim[0], anim[3])
		frames.set_animation_loop(anim[0], true)
		for f in anim[2]:
			var at := AtlasTexture.new()
			at.atlas = tex
			at.region = Rect2((anim[1] + f) * 24, 0, 24, 24)
			frames.add_frame(anim[0], at)
	_sprite.sprite_frames = frames
	_sprite.scale = Vector2(0.5, 0.5)
	_sprite.offset = Vector2(0, -10)
	add_child(_sprite)
	_sprite.play("ground")
	_check = randf() * 0.3


func _process(delta: float) -> void:
	if _state == "ground":
		_check -= delta
		if _check > 0.0:
			return
		_check = 0.3
		var threat: Node2D = null
		if Game.player and is_instance_valid(Game.player) and position.distance_to(Game.player.position) < 70.0:
			threat = Game.player
		else:
			for z in get_tree().get_nodes_in_group("zombies"):
				if position.distance_to(z.position) < 60.0:
					threat = z
					break
		if threat:
			_state = "fly"
			_vel = (position - threat.position).normalized() * 230.0
			_vel.y = -absf(_vel.y) - 120.0
			_sprite.play("fly")
			_sprite.flip_h = _vel.x < 0
			Game.play_sfx("crow", -10.0, 0.2)
	else:
		position += _vel * delta
		modulate.a -= delta * 0.9
		if modulate.a <= 0.0:
			queue_free()
