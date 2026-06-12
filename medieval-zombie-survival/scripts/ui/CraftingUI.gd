extends PanelContainer
## Crafting list. Some recipes need a workbench or campfire nearby.

var _list: VBoxContainer


func _ready() -> void:
	add_theme_stylebox_override("panel", UIKit.panel_style())
	custom_minimum_size = Vector2(520, 420)
	var box := VBoxContainer.new()
	box.add_theme_constant_override("separation", 8)
	add_child(box)
	box.add_child(UIKit.title("Crafting"))
	var scroll := ScrollContainer.new()
	scroll.size_flags_vertical = Control.SIZE_EXPAND_FILL
	box.add_child(scroll)
	_list = VBoxContainer.new()
	_list.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	_list.add_theme_constant_override("separation", 4)
	scroll.add_child(_list)
	if Game.player:
		Game.player.inventory_changed.connect(refresh)


func refresh() -> void:
	if not visible:
		return
	for c in _list.get_children():
		c.queue_free()
	var player = Game.player
	if player == null or not is_instance_valid(player):
		return
	for recipe in ItemDB.RECIPES:
		_list.add_child(_recipe_row(recipe, player))


func _recipe_row(recipe: Dictionary, player) -> Control:
	var row := HBoxContainer.new()
	row.add_theme_constant_override("separation", 8)
	var out_id: String = recipe["out"]
	var count := int(recipe["count"])
	if out_id == "arrow":
		count *= SkillTree.arrow_craft_mult()
	var icon := UIKit.icon_rect(ItemDB.icon(out_id), 30)
	row.add_child(icon)
	var name_box := VBoxContainer.new()
	name_box.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	row.add_child(name_box)
	var title := ItemDB.display_name(out_id)
	if count > 1:
		title += " x%d" % count
	var has_station: bool = Game.world.station_nearby(recipe["station"])
	var has_mats: bool = player.has_all(recipe["cost"])
	name_box.add_child(UIKit.label(title, 13, UIKit.TEXT if has_mats and has_station else UIKit.TEXT_DIM))
	var cost_line := ItemDB.cost_text(recipe)
	if recipe["station"] != "":
		cost_line += "   — needs %s nearby" % ItemDB.display_name(recipe["station"])
	name_box.add_child(UIKit.label(cost_line, 10,
			Color(0.55, 0.75, 0.5) if has_mats and has_station else Color(0.6, 0.45, 0.4)))
	var btn := UIKit.button("Craft", 12)
	btn.disabled = not (has_mats and has_station)
	btn.pressed.connect(_craft.bind(recipe))
	row.add_child(btn)
	return row


func _craft(recipe: Dictionary) -> void:
	var player = Game.player
	if player == null or not player.has_all(recipe["cost"]):
		return
	if not Game.world.station_nearby(recipe["station"]):
		return
	for mat in recipe["cost"]:
		player.remove_item(mat, recipe["cost"][mat])
	var count := int(recipe["count"])
	if recipe["out"] == "arrow":
		count *= SkillTree.arrow_craft_mult()
	player.add_item(recipe["out"], count)
	Game.play_sfx("craft")
	Game.add_xp(3)
	refresh()
