extends Node
## One-shot visual effects and spritesheet helpers.

var _frames_cache: Dictionary = {}


## Build (and cache) SpriteFrames from a horizontal strip spritesheet.
func strip_frames(path: String, fw: int, fh: int, count: int, fps: float, loop := false) -> SpriteFrames:
	var key := "%s:%d" % [path, fps]
	if _frames_cache.has(key):
		return _frames_cache[key]
	var tex: Texture2D = load(path)
	var frames := SpriteFrames.new()
	frames.remove_animation("default")
	frames.add_animation("play")
	frames.set_animation_speed("play", fps)
	frames.set_animation_loop("play", loop)
	for i in count:
		var at := AtlasTexture.new()
		at.atlas = tex
		at.region = Rect2(i * fw, 0, fw, fh)
		frames.add_frame("play", at)
	_frames_cache[key] = frames
	return frames


func _one_shot(parent: Node, pos: Vector2, frames: SpriteFrames, rot := 0.0, z := 50) -> AnimatedSprite2D:
	var s := AnimatedSprite2D.new()
	s.sprite_frames = frames
	s.position = pos
	s.rotation = rot
	s.z_index = z
	s.animation = "play"
	parent.add_child(s)
	s.play("play")
	s.animation_finished.connect(s.queue_free)
	return s


func slash(parent: Node, pos: Vector2, angle: float) -> void:
	var frames := strip_frames("res://assets/fx/slash.png", 36, 36, 3, 18.0)
	_one_shot(parent, pos, frames, angle)


func blood(parent: Node, pos: Vector2) -> void:
	var frames := strip_frames("res://assets/fx/blood.png", 24, 24, 3, 12.0)
	_one_shot(parent, pos, frames, randf() * TAU, 1)


func explosion(parent: Node, pos: Vector2) -> void:
	var frames := strip_frames("res://assets/fx/explosion.png", 40, 40, 4, 14.0)
	_one_shot(parent, pos, frames, 0.0, 60)


func float_text(parent: Node, pos: Vector2, text: String, color := Color.WHITE) -> void:
	var label := Label.new()
	label.text = text
	label.z_index = 100
	label.position = pos + Vector2(-20, -44)
	label.add_theme_font_size_override("font_size", 11)
	label.add_theme_color_override("font_color", color)
	label.add_theme_color_override("font_outline_color", Color(0.08, 0.06, 0.1))
	label.add_theme_constant_override("outline_size", 3)
	parent.add_child(label)
	var tw := label.create_tween()
	tw.set_parallel(true)
	tw.tween_property(label, "position:y", label.position.y - 26.0, 0.7)
	tw.tween_property(label, "modulate:a", 0.0, 0.7).set_delay(0.25)
	tw.chain().tween_callback(label.queue_free)


## Small footstep dust puff (sprinting).
func dust(parent: Node, pos: Vector2) -> void:
	var p := CPUParticles2D.new()
	p.position = pos
	p.amount = 4
	p.lifetime = 0.4
	p.one_shot = true
	p.emitting = true
	p.direction = Vector2(0, -1)
	p.spread = 70.0
	p.initial_velocity_min = 6.0
	p.initial_velocity_max = 16.0
	p.gravity = Vector2(0, -8)
	p.scale_amount_min = 1.0
	p.scale_amount_max = 2.0
	p.color = Color(0.76, 0.71, 0.6, 0.5)
	parent.add_child(p)
	get_tree().create_timer(0.7).timeout.connect(p.queue_free)


## Expanding ring used by Frost Nova.
func ring(parent: Node, pos: Vector2, radius: float, color: Color) -> void:
	var ring_node := FXRing.new()
	ring_node.position = pos
	ring_node.max_radius = radius
	ring_node.color = color
	ring_node.z_index = 60
	parent.add_child(ring_node)


class FXRing extends Node2D:
	var max_radius := 100.0
	var color := Color(0.6, 0.8, 1.0)
	var _t := 0.0

	func _process(delta: float) -> void:
		_t += delta * 3.0
		if _t >= 1.0:
			queue_free()
			return
		queue_redraw()

	func _draw() -> void:
		var r := max_radius * _t
		var c := color
		c.a = 1.0 - _t
		draw_arc(Vector2.ZERO, r, 0, TAU, 40, c, 3.0)
		c.a *= 0.4
		draw_arc(Vector2.ZERO, r * 0.8, 0, TAU, 40, c, 2.0)
