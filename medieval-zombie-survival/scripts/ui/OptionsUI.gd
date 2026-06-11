extends PanelContainer
## Sandbox difficulty options, Project Zomboid style. Opens with Esc and
## pauses the game. Changes apply immediately and persist to disk.

var _rows: VBoxContainer


func _ready() -> void:
	add_theme_stylebox_override("panel", UIKit.panel_style())
	custom_minimum_size = Vector2(560, 0)
	var box := VBoxContainer.new()
	box.add_theme_constant_override("separation", 8)
	add_child(box)
	box.add_child(UIKit.title("Options — Sandbox Difficulty"))
	box.add_child(UIKit.label("Changes apply immediately and are saved. Population and loot\ndensity fully settle in over the next in-game hours.", 11, UIKit.TEXT_DIM))
	_rows = VBoxContainer.new()
	_rows.add_theme_constant_override("separation", 4)
	box.add_child(_rows)
	var buttons := HBoxContainer.new()
	buttons.alignment = BoxContainer.ALIGNMENT_CENTER
	buttons.add_theme_constant_override("separation", 12)
	box.add_child(buttons)
	var resume := UIKit.button("Resume  [Esc]", 14)
	resume.pressed.connect(func(): Game.world.hud.close_options())
	buttons.add_child(resume)
	var restart := UIKit.button("Restart World", 14)
	restart.tooltip_text = "Start a fresh run with the current settings."
	restart.pressed.connect(_restart)
	buttons.add_child(restart)


func refresh() -> void:
	for c in _rows.get_children():
		c.queue_free()
	for def in Game.OPTION_DEFS:
		_rows.add_child(_option_row(def))


func _option_row(def: Dictionary) -> Control:
	var row := HBoxContainer.new()
	row.add_theme_constant_override("separation", 10)
	var name_lbl := UIKit.label(def["name"], 13)
	name_lbl.custom_minimum_size = Vector2(220, 0)
	name_lbl.tooltip_text = def["desc"]
	name_lbl.mouse_filter = Control.MOUSE_FILTER_STOP
	row.add_child(name_lbl)
	var current: float = Game.setting(def["key"])
	var idx := 0
	for i in def["choices"].size():
		if is_equal_approx(float(def["choices"][i][1]), current):
			idx = i
	var btn := UIKit.button("< %s >" % def["choices"][idx][0], 13)
	btn.custom_minimum_size = Vector2(190, 0)
	btn.tooltip_text = def["desc"]
	btn.pressed.connect(func():
		var next: int = (idx + 1) % int(def["choices"].size())
		Game.set_setting(def["key"], float(def["choices"][next][1]))
		refresh())
	row.add_child(btn)
	return row


func _restart() -> void:
	get_tree().paused = false
	Game.reset_run()
	get_tree().reload_current_scene()
