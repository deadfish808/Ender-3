extends Control
## Pre-game menu: title, sandbox difficulty setup, and Begin. The game
## itself never pauses — difficulty is decided here, before you step in.

var _rows: VBoxContainer
var _shot_frame := 0


func _ready() -> void:
	get_tree().paused = false
	set_anchors_preset(Control.PRESET_FULL_RECT)
	var bg := ColorRect.new()
	bg.color = Color(0.06, 0.055, 0.09)
	add_child(bg)
	bg.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	var vignette := TextureRect.new()
	vignette.texture = load("res://assets/fx/vignette.png")
	vignette.stretch_mode = TextureRect.STRETCH_SCALE
	vignette.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	vignette.texture_filter = CanvasItem.TEXTURE_FILTER_LINEAR
	add_child(vignette)
	vignette.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	var center := CenterContainer.new()
	add_child(center)
	center.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	var box := VBoxContainer.new()
	box.add_theme_constant_override("separation", 10)
	center.add_child(box)

	var icon := TextureRect.new()
	icon.texture = load("res://icon.png")
	icon.custom_minimum_size = Vector2(96, 96)
	icon.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	icon.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
	icon.size_flags_horizontal = Control.SIZE_SHRINK_CENTER
	box.add_child(icon)
	var title := UIKit.label("MEDIEVAL ZOMBIE SURVIVAL", 32, Color(0.95, 0.88, 0.66))
	title.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	box.add_child(title)
	var sub := UIKit.label("The dead walk the old kingdom. Decide how cruel it will be — then survive it.", 13, UIKit.TEXT_DIM)
	sub.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	box.add_child(sub)

	var panel := UIKit.panel(Vector2(560, 0))
	box.add_child(panel)
	var pbox := VBoxContainer.new()
	pbox.add_theme_constant_override("separation", 6)
	panel.add_child(pbox)
	var header := UIKit.label("SANDBOX DIFFICULTY", 14, Color(0.9, 0.55, 0.4))
	header.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	pbox.add_child(header)
	_rows = VBoxContainer.new()
	_rows.add_theme_constant_override("separation", 4)
	pbox.add_child(_rows)
	_refresh()

	var begin := UIKit.button("Begin Survival", 18)
	begin.size_flags_horizontal = Control.SIZE_SHRINK_CENTER
	begin.pressed.connect(_start)
	box.add_child(begin)
	var hint := UIKit.label("Settings are saved for next time. There is no pause out there.", 11, UIKit.TEXT_DIM)
	hint.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	box.add_child(hint)


func _refresh() -> void:
	for c in _rows.get_children():
		c.queue_free()
	for def in Game.OPTION_DEFS:
		_rows.add_child(_option_row(def))


func _option_row(def: Dictionary) -> Control:
	var row := HBoxContainer.new()
	row.add_theme_constant_override("separation", 10)
	var name_lbl := UIKit.label(def["name"], 13)
	name_lbl.custom_minimum_size = Vector2(230, 0)
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
		_refresh())
	row.add_child(btn)
	return row


func _start() -> void:
	Game.reset_run()
	get_tree().change_scene_to_file("res://scenes/Main.tscn")


func _process(_delta: float) -> void:
	if OS.get_environment("MZS_SHOT_DIR") == "":
		return
	_shot_frame += 1
	if _shot_frame == 8:
		var img := get_viewport().get_texture().get_image()
		img.save_png(OS.get_environment("MZS_SHOT_DIR").path_join("00_main_menu.png"))
		print("saved 00_main_menu")
		_start()
