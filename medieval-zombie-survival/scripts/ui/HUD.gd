extends CanvasLayer
## On-screen HUD: stat bars, clock, weapon slot, XP, panels, messages.

var hp_bar: ProgressBar
var stamina_bar: ProgressBar
var mana_bar: ProgressBar
var hunger_bar: ProgressBar
var time_label: Label
var weapon_icon: TextureRect
var weapon_label: Label
var xp_bar: ProgressBar
var level_label: Label
var skill_hint: Label
var message_box: VBoxContainer

var inventory_panel: Control
var crafting_panel: Control
var build_panel: Control
var skills_panel: Control
var _root: Control
var _game_over: Control


func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	layer = 10
	_root = Control.new()
	_root.set_anchors_preset(Control.PRESET_FULL_RECT)
	_root.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(_root)
	var vignette := TextureRect.new()
	vignette.texture = load("res://assets/fx/vignette.png")
	vignette.set_anchors_preset(Control.PRESET_FULL_RECT)
	vignette.stretch_mode = TextureRect.STRETCH_SCALE
	vignette.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	vignette.texture_filter = CanvasItem.TEXTURE_FILTER_LINEAR
	vignette.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_root.add_child(vignette)
	_build_stats()
	_build_clock()
	_build_weapon_slot()
	_build_xp()
	_build_hints()
	_build_messages()
	inventory_panel = preload("res://scripts/ui/InventoryUI.gd").new()
	crafting_panel = preload("res://scripts/ui/CraftingUI.gd").new()
	build_panel = preload("res://scripts/ui/BuildMenuUI.gd").new()
	skills_panel = preload("res://scripts/ui/SkillTreeUI.gd").new()
	for p in [inventory_panel, crafting_panel, build_panel, skills_panel]:
		p.visible = false
		p.set_anchors_preset(Control.PRESET_CENTER)
		p.grow_horizontal = Control.GROW_DIRECTION_BOTH
		p.grow_vertical = Control.GROW_DIRECTION_BOTH
		_root.add_child(p)


func _build_stats() -> void:
	var box := VBoxContainer.new()
	box.position = Vector2(14, 12)
	box.add_theme_constant_override("separation", 4)
	_root.add_child(box)
	hp_bar = UIKit.stat_bar(Color(0.78, 0.22, 0.2))
	stamina_bar = UIKit.stat_bar(Color(0.82, 0.72, 0.25))
	mana_bar = UIKit.stat_bar(Color(0.3, 0.5, 0.85))
	hunger_bar = UIKit.stat_bar(Color(0.85, 0.5, 0.2))
	for pair in [["HP", hp_bar], ["STA", stamina_bar], ["MANA", mana_bar], ["FOOD", hunger_bar]]:
		var row := HBoxContainer.new()
		row.add_theme_constant_override("separation", 6)
		var lbl: Label = UIKit.label(pair[0], 10, UIKit.TEXT_DIM)
		lbl.custom_minimum_size = Vector2(34, 0)
		row.add_child(lbl)
		row.add_child(pair[1])
		box.add_child(row)


func _build_clock() -> void:
	var p := UIKit.panel()
	p.set_anchors_preset(Control.PRESET_TOP_RIGHT)
	p.position = Vector2(-150, 12)
	p.grow_horizontal = Control.GROW_DIRECTION_BEGIN
	_root.add_child(p)
	time_label = UIKit.label("Day 1  07:00", 15)
	p.add_child(time_label)


func _build_weapon_slot() -> void:
	var p := UIKit.panel()
	p.set_anchors_preset(Control.PRESET_BOTTOM_LEFT)
	p.position = Vector2(14, -86)
	p.grow_vertical = Control.GROW_DIRECTION_BEGIN
	_root.add_child(p)
	var row := HBoxContainer.new()
	row.add_theme_constant_override("separation", 8)
	p.add_child(row)
	weapon_icon = UIKit.icon_rect(null, 38)
	row.add_child(weapon_icon)
	weapon_label = UIKit.label("Fists", 12)
	row.add_child(weapon_label)


func _build_xp() -> void:
	xp_bar = UIKit.stat_bar(Color(0.5, 0.8, 0.4))
	xp_bar.custom_minimum_size = Vector2(280, 8)
	xp_bar.set_anchors_preset(Control.PRESET_CENTER_BOTTOM)
	xp_bar.position = Vector2(-140, -20)
	xp_bar.grow_vertical = Control.GROW_DIRECTION_BEGIN
	_root.add_child(xp_bar)
	level_label = UIKit.label("Lv 1", 12)
	level_label.set_anchors_preset(Control.PRESET_CENTER_BOTTOM)
	level_label.position = Vector2(150, -26)
	level_label.grow_vertical = Control.GROW_DIRECTION_BEGIN
	_root.add_child(level_label)
	skill_hint = UIKit.label("", 12, Color(0.6, 1.0, 0.6))
	skill_hint.set_anchors_preset(Control.PRESET_CENTER_BOTTOM)
	skill_hint.position = Vector2(-140, -44)
	skill_hint.grow_vertical = Control.GROW_DIRECTION_BEGIN
	_root.add_child(skill_hint)


func _build_hints() -> void:
	var hints := UIKit.label(
		"[WASD] move   [Shift] sprint   [Space] dodge   [LMB] attack/harvest   [RMB] frost nova   [E] interact   [1/2/3] weapons   [Tab] inventory   [C] craft   [B] build   [K] skills",
		11, UIKit.TEXT_DIM)
	hints.set_anchors_preset(Control.PRESET_CENTER_BOTTOM)
	hints.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	hints.position = Vector2(-490, -6)
	hints.custom_minimum_size = Vector2(980, 0)
	hints.grow_vertical = Control.GROW_DIRECTION_BEGIN
	_root.add_child(hints)


func _build_messages() -> void:
	message_box = VBoxContainer.new()
	message_box.set_anchors_preset(Control.PRESET_CENTER_TOP)
	message_box.position = Vector2(-250, 60)
	message_box.custom_minimum_size = Vector2(500, 0)
	message_box.alignment = BoxContainer.ALIGNMENT_BEGIN
	_root.add_child(message_box)


func announce(text: String, color := Color.WHITE) -> void:
	var l := UIKit.label(text, 17, color)
	l.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	l.add_theme_color_override("font_outline_color", Color(0.05, 0.04, 0.08))
	l.add_theme_constant_override("outline_size", 4)
	message_box.add_child(l)
	var tw := l.create_tween()
	tw.tween_interval(2.6)
	tw.tween_property(l, "modulate:a", 0.0, 0.8)
	tw.tween_callback(l.queue_free)


func _process(_delta: float) -> void:
	var player = Game.player
	if player == null or not is_instance_valid(player):
		return
	hp_bar.max_value = player.max_hp()
	hp_bar.value = player.hp
	stamina_bar.value = player.stamina
	mana_bar.max_value = player.max_mana()
	mana_bar.value = player.mana
	hunger_bar.value = player.hunger
	var night_marker := "  (night)" if Game.is_night() else ""
	time_label.text = "Day %d   %s%s" % [Game.day, Game.clock_text(), night_marker]
	time_label.add_theme_color_override("font_color",
			Color(0.65, 0.7, 1.0) if Game.is_night() else UIKit.TEXT)
	xp_bar.max_value = Game.xp_needed()
	xp_bar.value = Game.xp
	level_label.text = "Lv %d" % Game.level
	skill_hint.text = "%d skill point%s available — press K" % [Game.skill_points, "s" if Game.skill_points > 1 else ""] if Game.skill_points > 0 else ""
	# weapon slot
	var w: Dictionary = player.weapon_stats()
	weapon_icon.texture = ItemDB.icon(player.equipped) if player.equipped != "" else null
	var extra := ""
	match w.get("type", ""):
		"bow":
			extra = "\narrows: %d" % player.inventory.get("arrow", 0)
		"staff":
			extra = "\nmana cost: %d" % int(w.get("mana", 0))
		_:
			pass
	weapon_label.text = str(w.get("name", "Fists")) + extra


# ------------------------------------------------------------- panels -------
func _unhandled_input(event: InputEvent) -> void:
	if _game_over != null:
		return
	if event.is_action_pressed("toggle_inventory"):
		_toggle(inventory_panel)
	elif event.is_action_pressed("toggle_craft"):
		_toggle(crafting_panel)
	elif event.is_action_pressed("toggle_build"):
		_toggle(build_panel)
	elif event.is_action_pressed("toggle_skills"):
		_toggle(skills_panel)
	elif event.is_action_pressed("ui_cancel"):
		close_all_panels()


func _toggle(panel: Control) -> void:
	var was := panel.visible
	close_all_panels()
	panel.visible = not was
	if panel.visible and panel.has_method("refresh"):
		panel.refresh()
	get_viewport().set_input_as_handled()


func close_all_panels() -> void:
	for p in [inventory_panel, crafting_panel, build_panel, skills_panel]:
		p.visible = false


func ui_blocking() -> bool:
	for p in [inventory_panel, crafting_panel, build_panel, skills_panel]:
		if p.visible:
			return true
	return _game_over != null


func show_game_over() -> void:
	if _game_over:
		return
	close_all_panels()
	get_tree().paused = true
	_game_over = Control.new()
	_game_over.set_anchors_preset(Control.PRESET_FULL_RECT)
	_root.add_child(_game_over)
	var dim := ColorRect.new()
	dim.color = Color(0.05, 0.02, 0.03, 0.75)
	dim.set_anchors_preset(Control.PRESET_FULL_RECT)
	_game_over.add_child(dim)
	var panel := UIKit.panel(Vector2(360, 0))
	panel.set_anchors_preset(Control.PRESET_CENTER)
	panel.grow_horizontal = Control.GROW_DIRECTION_BOTH
	panel.grow_vertical = Control.GROW_DIRECTION_BOTH
	_game_over.add_child(panel)
	var box := VBoxContainer.new()
	box.add_theme_constant_override("separation", 10)
	panel.add_child(box)
	var title := UIKit.label("YOU DIED", 30, Color(0.85, 0.25, 0.2))
	title.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	box.add_child(title)
	var stats := UIKit.label(
		"Survived %d day%s\nZombies slain: %d\nLevel reached: %d" %
		[Game.day, "s" if Game.day > 1 else "", Game.kills, Game.level], 15)
	stats.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	box.add_child(stats)
	var btn := UIKit.button("Rise Again", 16)
	btn.pressed.connect(_restart)
	box.add_child(btn)


func _restart() -> void:
	get_tree().paused = false
	Game.reset_run()
	get_tree().reload_current_scene()
