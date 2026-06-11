extends Node
## The three skill trees and the player's learned skills.

signal skills_changed

const TREES := {
	"Fighter": [
		{"id": "toughness", "name": "Toughness", "desc": "+30 maximum health.", "req": [], "min_pts": 0},
		{"id": "sword_mastery", "name": "Sword Mastery", "desc": "+25% melee damage.", "req": [], "min_pts": 0},
		{"id": "heavy_swing", "name": "Heavy Swing", "desc": "+10% melee damage, double knockback.", "req": ["sword_mastery"], "min_pts": 1},
		{"id": "second_wind", "name": "Second Wind", "desc": "Regenerate 2 HP/s while below 30% health.", "req": ["toughness"], "min_pts": 1},
		{"id": "cleave", "name": "Cleave", "desc": "Melee swings strike every enemy in the arc.", "req": ["heavy_swing"], "min_pts": 3},
		{"id": "juggernaut", "name": "Juggernaut", "desc": "Take 25% less damage from all sources.", "req": ["toughness"], "min_pts": 3},
	],
	"Archer": [
		{"id": "steady_hands", "name": "Steady Hands", "desc": "+25% bow damage.", "req": [], "min_pts": 0},
		{"id": "fletcher", "name": "Fletcher", "desc": "Crafting arrows yields twice as many.", "req": [], "min_pts": 0},
		{"id": "quick_draw", "name": "Quick Draw", "desc": "Bows fire 30% faster.", "req": ["steady_hands"], "min_pts": 1},
		{"id": "power_shot", "name": "Power Shot", "desc": "+35% bow damage.", "req": ["steady_hands"], "min_pts": 1},
		{"id": "piercing", "name": "Piercing Shots", "desc": "Arrows punch through up to 2 extra zombies.", "req": ["power_shot"], "min_pts": 3},
		{"id": "multishot", "name": "Multishot", "desc": "Fire a fan of 3 arrows per shot.", "req": ["quick_draw"], "min_pts": 3},
	],
	"Mage": [
		{"id": "mana_pool", "name": "Mana Pool", "desc": "+30 maximum mana.", "req": [], "min_pts": 0},
		{"id": "focus", "name": "Focus", "desc": "+25% spell damage.", "req": [], "min_pts": 0},
		{"id": "mana_flow", "name": "Mana Flow", "desc": "+1.5 mana regenerated per second.", "req": ["mana_pool"], "min_pts": 1},
		{"id": "arcane_power", "name": "Arcane Power", "desc": "+35% spell damage.", "req": ["focus"], "min_pts": 1},
		{"id": "fireball", "name": "Fireball", "desc": "Staff bolts explode, damaging nearby zombies.", "req": ["arcane_power"], "min_pts": 3},
		{"id": "frost_nova", "name": "Frost Nova", "desc": "Right-click: freeze-blast that slows all nearby zombies. Costs 20 mana.", "req": ["mana_pool"], "min_pts": 3},
	],
}

var learned: Dictionary = {}


func reset() -> void:
	learned.clear()
	emit_signal("skills_changed")


func has_skill(id: String) -> bool:
	return learned.has(id)


func tree_of(id: String) -> String:
	for tree_name in TREES:
		for s in TREES[tree_name]:
			if s["id"] == id:
				return tree_name
	return ""


func get_skill(id: String) -> Dictionary:
	for tree_name in TREES:
		for s in TREES[tree_name]:
			if s["id"] == id:
				return s
	return {}


func points_in_tree(tree_name: String) -> int:
	var n := 0
	for s in TREES.get(tree_name, []):
		if learned.has(s["id"]):
			n += 1
	return n


func can_learn(id: String) -> bool:
	if learned.has(id) or Game.skill_points <= 0:
		return false
	var s := get_skill(id)
	if s.is_empty():
		return false
	for r in s["req"]:
		if not learned.has(r):
			return false
	return points_in_tree(tree_of(id)) >= int(s["min_pts"])


func locked_reason(id: String) -> String:
	var s := get_skill(id)
	if s.is_empty():
		return ""
	var reasons := []
	for r in s["req"]:
		if not learned.has(r):
			reasons.append("Requires %s" % get_skill(r).get("name", r))
	var tree_name := tree_of(id)
	if points_in_tree(tree_name) < int(s["min_pts"]):
		reasons.append("Requires %d points in %s" % [int(s["min_pts"]), tree_name])
	return ". ".join(reasons)


func learn(id: String) -> bool:
	if not can_learn(id):
		return false
	if not Game.spend_skill_point():
		return false
	learned[id] = true
	emit_signal("skills_changed")
	if Game.player and Game.player.has_method("on_skills_changed"):
		Game.player.on_skills_changed()
	return true


# ----------------------------------------------------------- modifiers ------
func melee_mult() -> float:
	var m := 1.0
	if has_skill("sword_mastery"):
		m += 0.25
	if has_skill("heavy_swing"):
		m += 0.10
	return m


func bow_mult() -> float:
	var m := 1.0
	if has_skill("steady_hands"):
		m += 0.25
	if has_skill("power_shot"):
		m += 0.35
	return m


func spell_mult() -> float:
	var m := 1.0
	if has_skill("focus"):
		m += 0.25
	if has_skill("arcane_power"):
		m += 0.35
	return m


func bow_cooldown_mult() -> float:
	return 0.7 if has_skill("quick_draw") else 1.0


func knockback_mult() -> float:
	return 2.0 if has_skill("heavy_swing") else 1.0


func damage_taken_mult() -> float:
	return 0.75 if has_skill("juggernaut") else 1.0


func bonus_hp() -> int:
	return 30 if has_skill("toughness") else 0


func bonus_mana() -> int:
	return 30 if has_skill("mana_pool") else 0


func mana_regen() -> float:
	return 2.5 if has_skill("mana_flow") else 1.0


func arrow_pierce() -> int:
	return 2 if has_skill("piercing") else 0


func arrow_craft_mult() -> int:
	return 2 if has_skill("fletcher") else 1
