extends PanelContainer
## Inventory grid. Click food to eat, weapons to equip, buildables to place.

var _grid: GridContainer


func _ready() -> void:
	add_theme_stylebox_override("panel", UIKit.panel_style())
	custom_minimum_size = Vector2(440, 340)
	var box := VBoxContainer.new()
	box.add_theme_constant_override("separation", 8)
	add_child(box)
	box.add_child(UIKit.title("Inventory"))
	box.add_child(UIKit.label("Click: eat food / equip weapon / place buildable", 11, UIKit.TEXT_DIM))
	var scroll := ScrollContainer.new()
	scroll.size_flags_vertical = Control.SIZE_EXPAND_FILL
	box.add_child(scroll)
	_grid = GridContainer.new()
	_grid.columns = 6
	_grid.add_theme_constant_override("h_separation", 6)
	_grid.add_theme_constant_override("v_separation", 6)
	scroll.add_child(_grid)
	if Game.player:
		Game.player.inventory_changed.connect(refresh)


func refresh() -> void:
	if not visible:
		return
	for c in _grid.get_children():
		c.queue_free()
	var player = Game.player
	if player == null or not is_instance_valid(player):
		return
	var ids: Array = player.inventory.keys()
	ids.sort()
	for id in ids:
		var count: int = player.inventory[id]
		var item: Dictionary = ItemDB.get_item(id)
		var btn := UIKit.button("", 11)
		btn.custom_minimum_size = Vector2(62, 62)
		btn.tooltip_text = "%s\n%s" % [ItemDB.display_name(id), item.get("desc", "")]
		var inner := VBoxContainer.new()
		inner.alignment = BoxContainer.ALIGNMENT_CENTER
		inner.mouse_filter = Control.MOUSE_FILTER_IGNORE
		inner.set_anchors_preset(Control.PRESET_FULL_RECT)
		btn.add_child(inner)
		var icon := UIKit.icon_rect(ItemDB.icon(id), 30)
		icon.mouse_filter = Control.MOUSE_FILTER_IGNORE
		icon.size_flags_horizontal = Control.SIZE_SHRINK_CENTER
		inner.add_child(icon)
		var suffix := "  [E]" if id == player.equipped else ""
		var lbl := UIKit.label("x%d%s" % [count, suffix], 10,
				Color(0.6, 1.0, 0.6) if id == player.equipped else UIKit.TEXT_DIM)
		lbl.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
		lbl.mouse_filter = Control.MOUSE_FILTER_IGNORE
		inner.add_child(lbl)
		btn.pressed.connect(func():
			player.use_item(id)
			refresh())
		_grid.add_child(btn)
