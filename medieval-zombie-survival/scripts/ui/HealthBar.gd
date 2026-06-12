extends Node2D
## Tiny world-space health bar shown above damaged zombies/structures.

var _ratio := 1.0
var _visible_time := 0.0


func update_bar(hp: float, max_hp: float) -> void:
	_ratio = clampf(hp / maxf(max_hp, 1.0), 0.0, 1.0)
	_visible_time = 3.0
	queue_redraw()


func _process(delta: float) -> void:
	if _visible_time > 0.0:
		_visible_time -= delta
		if _visible_time <= 0.0:
			queue_redraw()


func _draw() -> void:
	if _visible_time <= 0.0 or _ratio >= 1.0:
		return
	var w := 26.0
	draw_rect(Rect2(-w / 2 - 1, -3, w + 2, 5), Color(0.08, 0.06, 0.1, 0.85))
	draw_rect(Rect2(-w / 2, -2, w * _ratio, 3), Color(0.85, 0.25, 0.2))
