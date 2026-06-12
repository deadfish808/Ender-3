extends PanelContainer
## Lists buildable structures in the player's pack; click to start placing.

var _list: VBoxContainer


func _ready() -> void:
	add_theme_stylebox_override("panel", UIKit.panel_style())
	custom_minimum_size = Vector2(420, 320)
	var box := VBoxContainer.new()
	box.add_theme_constant_override("separation", 8)
	add_child(box)
	box.add_child(UIKit.title("Build"))
	box.add_child(UIKit.label("Craft structures first [C], then place them here.\nLMB places, RMB/Esc cancels.", 11, UIKit.TEXT_DIM))
	var scroll := ScrollContainer.new()
	scroll.size_flags_vertical = Control.SIZE_EXPAND_FILL
	box.add_child(scroll)
	_list = VBoxContainer.new()
	_list.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	_list.add_theme_constant_override("separation", 4)
	scroll.add_child(_list)


func refresh() -> void:
	for c in _list.get_children():
		c.queue_free()
	var player = Game.player
	if player == null or not is_instance_valid(player):
		return
	var any := false
	for id in ItemDB.BUILDABLES:
		var count: int = player.inventory.get(id, 0)
		if count <= 0:
			continue
		any = true
		var row := HBoxContainer.new()
		row.add_theme_constant_override("separation", 8)
		row.add_child(UIKit.icon_rect(ItemDB.icon(id), 30))
		var lbl := UIKit.label("%s  x%d" % [ItemDB.display_name(id), count], 13)
		lbl.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		row.add_child(lbl)
		var btn := UIKit.button("Place", 12)
		btn.pressed.connect(func():
			Game.world.hud.close_all_panels()
			Game.world.build_manager.enter_build(id))
		row.add_child(btn)
		_list.add_child(row)
	if not any:
		_list.add_child(UIKit.label("No structures in your pack.\nCraft walls, traps and stations from the crafting menu.", 12, UIKit.TEXT_DIM))
