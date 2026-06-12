extends Node
## Item, recipe and buildable definitions.

const ITEMS := {
	# materials
	"wood": {"name": "Wood", "desc": "Rough timber chopped from trees.", "type": "material"},
	"stone": {"name": "Stone", "desc": "A chunk of fieldstone.", "type": "material"},
	"fiber": {"name": "Plant Fiber", "desc": "Tough strands torn from bushes.", "type": "material"},
	"flint": {"name": "Flint", "desc": "Sharp-edged stone, good for arrowheads.", "type": "material"},
	"iron_scrap": {"name": "Iron Scrap", "desc": "Salvaged metal from the fallen.", "type": "material"},
	"cloth": {"name": "Old Cloth", "desc": "Tattered but usable fabric.", "type": "material"},
	"essence": {"name": "Dark Essence", "desc": "The cursed spark that animates the dead. Fuel for magic.", "type": "material"},
	"plank": {"name": "Plank", "desc": "Worked timber for sturdy construction.", "type": "material"},
	"rope": {"name": "Rope", "desc": "Braided fiber cord.", "type": "material"},
	"arrow": {"name": "Arrow", "desc": "Flint-tipped arrow. Ammunition for bows.", "type": "material"},
	# food / consumables
	"berries": {"name": "Berries", "desc": "Wild berries. Eat to restore hunger.", "type": "food", "food": 20, "heal": 2},
	"mushroom": {"name": "Mushroom", "desc": "A forest mushroom. Edible... probably.", "type": "food", "food": 12, "heal": 0},
	"stew": {"name": "Mushroom Stew", "desc": "Hearty hot stew. Restores hunger and some health.", "type": "food", "food": 55, "heal": 12},
	"salve": {"name": "Healing Salve", "desc": "Herbal salve. Restores 40 health and stops bleeding.", "type": "food", "food": 0, "heal": 40, "cures": true},
	"bandage": {"name": "Bandage", "desc": "Stops bleeding and patches small wounds.", "type": "food", "food": 0, "heal": 6, "cures": true},
	"remedy": {"name": "Plague Remedy", "desc": "A bitter draught that burns out wound-rot. The only cure for infection.", "type": "food", "food": 0, "heal": 10, "cures": true, "cures_infection": true},
	"raw_fish": {"name": "Raw Fish", "desc": "Fresh from the lake. Better cooked.", "type": "food", "food": 12, "heal": 0},
	"cooked_fish": {"name": "Cooked Fish", "desc": "Flaky and hot. A proper meal.", "type": "food", "food": 45, "heal": 8},
	"fishing_rod": {"name": "Fishing Rod", "desc": "Equip it, then cast at open water (LMB). Patience feeds you quietly.", "type": "tool"},
	# weapons
	"wooden_sword": {"name": "Wooden Sword", "desc": "A practice blade. Better than fists.", "type": "melee", "dmg": 14, "cooldown": 0.55, "knockback": 90},
	"iron_sword": {"name": "Iron Sword", "desc": "A proper soldier's blade.", "type": "melee", "dmg": 28, "cooldown": 0.5, "knockback": 110},
	"wooden_bow": {"name": "Wooden Bow", "desc": "A simple hunting bow. Uses arrows.", "type": "bow", "dmg": 16, "cooldown": 0.9},
	"longbow": {"name": "Longbow", "desc": "A war bow with serious draw weight. Uses arrows.", "type": "bow", "dmg": 30, "cooldown": 0.8},
	"apprentice_staff": {"name": "Apprentice Staff", "desc": "Channels dark essence into firebolts. Uses mana.", "type": "staff", "dmg": 18, "cooldown": 0.6, "mana": 7},
	"arcane_staff": {"name": "Arcane Staff", "desc": "A master's conduit for destructive magic. Uses mana.", "type": "staff", "dmg": 34, "cooldown": 0.55, "mana": 9},
	# buildables
	"wooden_wall": {"name": "Wooden Wall", "desc": "A solid timber wall. Zombies will claw at it.", "type": "buildable"},
	"stone_wall": {"name": "Stone Wall", "desc": "Heavy masonry. Holds the line for a long time.", "type": "buildable"},
	"wooden_door": {"name": "Wooden Door", "desc": "A wall with a door. Press E to open and close.", "type": "buildable"},
	"barricade": {"name": "Barricade", "desc": "Cheap crossed planks. Slows the horde down.", "type": "buildable"},
	"spike_trap": {"name": "Spike Trap", "desc": "Iron spikes that shred zombies who walk over them.", "type": "buildable"},
	"campfire": {"name": "Campfire", "desc": "Light, warmth, and a place to cook.", "type": "buildable"},
	"workbench": {"name": "Workbench", "desc": "Needed to craft advanced gear and stone walls.", "type": "buildable"},
	"garden_plot": {"name": "Garden Plot", "desc": "Tilled earth. Plant 2 berries (E), wait a day, harvest a crop.", "type": "buildable"},
}

## station: "" = anywhere, "workbench"/"campfire" = must stand near one.
const RECIPES := [
	{"out": "plank", "count": 1, "cost": {"wood": 2}, "station": ""},
	{"out": "rope", "count": 1, "cost": {"fiber": 3}, "station": ""},
	{"out": "arrow", "count": 4, "cost": {"wood": 1, "flint": 1}, "station": ""},
	{"out": "bandage", "count": 2, "cost": {"cloth": 1}, "station": ""},
	{"out": "wooden_sword", "count": 1, "cost": {"wood": 3, "rope": 1}, "station": ""},
	{"out": "wooden_bow", "count": 1, "cost": {"wood": 3, "rope": 2}, "station": ""},
	{"out": "apprentice_staff", "count": 1, "cost": {"wood": 3, "essence": 2}, "station": ""},
	{"out": "campfire", "count": 1, "cost": {"stone": 3, "wood": 2}, "station": ""},
	{"out": "workbench", "count": 1, "cost": {"wood": 5, "stone": 2}, "station": ""},
	{"out": "wooden_wall", "count": 1, "cost": {"wood": 4}, "station": ""},
	{"out": "barricade", "count": 1, "cost": {"wood": 2}, "station": ""},
	{"out": "wooden_door", "count": 1, "cost": {"wood": 4, "rope": 1}, "station": ""},
	{"out": "spike_trap", "count": 1, "cost": {"wood": 3, "flint": 2}, "station": ""},
	{"out": "garden_plot", "count": 1, "cost": {"wood": 3, "fiber": 2}, "station": ""},
	{"out": "fishing_rod", "count": 1, "cost": {"wood": 2, "rope": 2}, "station": ""},
	{"out": "cooked_fish", "count": 1, "cost": {"raw_fish": 1}, "station": "campfire"},
	{"out": "stew", "count": 1, "cost": {"mushroom": 2, "berries": 1}, "station": "campfire"},
	{"out": "salve", "count": 1, "cost": {"berries": 3, "cloth": 1}, "station": "campfire"},
	{"out": "remedy", "count": 1, "cost": {"essence": 2, "berries": 2, "cloth": 1}, "station": "campfire"},
	{"out": "iron_sword", "count": 1, "cost": {"plank": 2, "iron_scrap": 3}, "station": "workbench"},
	{"out": "longbow", "count": 1, "cost": {"plank": 4, "rope": 2}, "station": "workbench"},
	{"out": "arcane_staff", "count": 1, "cost": {"plank": 2, "essence": 5}, "station": "workbench"},
	{"out": "stone_wall", "count": 1, "cost": {"stone": 6}, "station": "workbench"},
]

const BUILDABLES := {
	"wooden_wall": {"hp": 220, "texture": "res://assets/buildables/wooden_wall.png", "blocks": true},
	"stone_wall": {"hp": 520, "texture": "res://assets/buildables/stone_wall.png", "blocks": true},
	"wooden_door": {"hp": 180, "texture": "res://assets/buildables/door_closed.png",
			"texture_open": "res://assets/buildables/door_open.png", "blocks": true, "door": true},
	"barricade": {"hp": 120, "texture": "res://assets/buildables/barricade.png", "blocks": true},
	"spike_trap": {"hp": 90, "texture": "res://assets/buildables/spike_trap.png", "blocks": false, "spikes": true},
	"campfire": {"hp": 80, "texture": "res://assets/buildables/campfire.png", "blocks": false,
			"frames": 4, "frame_size": Vector2i(80, 88), "light": true, "station": "campfire"},
	"workbench": {"hp": 140, "texture": "res://assets/buildables/workbench.png", "blocks": true, "station": "workbench"},
	"garden_plot": {"hp": 60, "texture": "res://assets/buildables/garden_plot.png", "blocks": false, "garden": true,
			"texture_sprout": "res://assets/buildables/garden_sprout.png",
			"texture_ready": "res://assets/buildables/garden_ready.png"},
}

var _icon_cache: Dictionary = {}


func get_item(id: String) -> Dictionary:
	return ITEMS.get(id, {})


func display_name(id: String) -> String:
	return ITEMS.get(id, {}).get("name", id)


func icon(id: String) -> Texture2D:
	if _icon_cache.has(id):
		return _icon_cache[id]
	var path := "res://assets/items/%s.png" % id
	var tex: Texture2D = load(path) if ResourceLoader.exists(path) else null
	_icon_cache[id] = tex
	return tex


func is_weapon(id: String) -> bool:
	var t: String = ITEMS.get(id, {}).get("type", "")
	return t == "melee" or t == "bow" or t == "staff"


func cost_text(recipe: Dictionary) -> String:
	var parts := []
	for mat in recipe["cost"]:
		parts.append("%d %s" % [recipe["cost"][mat], display_name(mat)])
	return ", ".join(parts)
