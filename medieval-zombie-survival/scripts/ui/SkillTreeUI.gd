extends PanelContainer
## Fighter / Archer / Mage skill trees.

const TREE_COLORS := {
	"Fighter": Color(0.9, 0.55, 0.4),
	"Archer": Color(0.55, 0.85, 0.5),
	"Mage": Color(0.6, 0.6, 0.95),
}

var _points_label: Label
var _columns: HBoxContainer


func _ready() -> void:
	add_theme_stylebox_override("panel", UIKit.panel_style())
	custom_minimum_size = Vector2(720, 440)
	var box := VBoxContainer.new()
	box.add_theme_constant_override("separation", 8)
	add_child(box)
	box.add_child(UIKit.title("Skills"))
	_points_label = UIKit.label("Skill points: 0", 14, Color(0.6, 1.0, 0.6))
	_points_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	box.add_child(_points_label)
	_columns = HBoxContainer.new()
	_columns.add_theme_constant_override("separation", 14)
	_columns.size_flags_vertical = Control.SIZE_EXPAND_FILL
	box.add_child(_columns)
	SkillTree.skills_changed.connect(refresh)
	Game.skill_points_changed.connect(func(_p): refresh())


func refresh() -> void:
	if not visible:
		return
	_points_label.text = "Skill points: %d  (earn more by leveling up)" % Game.skill_points
	for c in _columns.get_children():
		c.queue_free()
	for tree_name in SkillTree.TREES:
		_columns.add_child(_tree_column(tree_name))


func _tree_column(tree_name: String) -> Control:
	var col := VBoxContainer.new()
	col.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	col.add_theme_constant_override("separation", 6)
	var header := UIKit.label(tree_name.to_upper(), 15, TREE_COLORS[tree_name])
	header.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	col.add_child(header)
	var pts := UIKit.label("%d points spent" % SkillTree.points_in_tree(tree_name), 10, UIKit.TEXT_DIM)
	pts.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	col.add_child(pts)
	for skill in SkillTree.TREES[tree_name]:
		col.add_child(_skill_button(skill, tree_name))
	return col


func _skill_button(skill: Dictionary, tree_name: String) -> Control:
	var id: String = skill["id"]
	var learned: bool = SkillTree.has_skill(id)
	var can: bool = SkillTree.can_learn(id)
	var btn := UIKit.button("", 12)
	btn.custom_minimum_size = Vector2(0, 52)
	var inner := VBoxContainer.new()
	inner.mouse_filter = Control.MOUSE_FILTER_IGNORE
	inner.set_anchors_preset(Control.PRESET_FULL_RECT)
	inner.alignment = BoxContainer.ALIGNMENT_CENTER
	btn.add_child(inner)
	var name_color: Color = TREE_COLORS[tree_name] if learned else (UIKit.TEXT if can else UIKit.TEXT_DIM)
	var name_text: String = skill["name"] + ("  ✓" if learned else "")
	var name_lbl := UIKit.label(name_text, 13, name_color)
	name_lbl.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	name_lbl.mouse_filter = Control.MOUSE_FILTER_IGNORE
	inner.add_child(name_lbl)
	var desc := UIKit.label(skill["desc"], 10, UIKit.TEXT_DIM)
	desc.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	desc.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	desc.mouse_filter = Control.MOUSE_FILTER_IGNORE
	inner.add_child(desc)
	if learned:
		btn.disabled = true
	elif not can:
		btn.disabled = true
		var reason := SkillTree.locked_reason(id)
		if Game.skill_points <= 0:
			reason = ("No skill points. " + reason).strip_edges()
		btn.tooltip_text = reason
	else:
		btn.tooltip_text = "Click to learn"
		btn.pressed.connect(func():
			if SkillTree.learn(id):
				Game.play_sfx("levelup", -8.0))
	return btn
