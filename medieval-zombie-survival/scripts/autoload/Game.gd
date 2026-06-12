extends Node
## Global game state: clock, day counter, XP/levels, input map, sound.

signal time_changed(day: int, time_of_day: float)
signal day_started(day: int)
signal night_started(day: int)
signal xp_changed(xp: int, needed: int, level: int)
signal level_gained(level: int)
signal skill_points_changed(points: int)

const NIGHT_START := 0.625  # 21:00 (time_of_day 0.0 == 06:00)
const NIGHT_END := 0.958    # 05:00

## Sandbox difficulty options (Project Zomboid style). Persisted to disk.
const OPTION_DEFS := [
	{"key": "zombie_population", "name": "Zombie Population",
		"desc": "How many zombies the world sustains.",
		"choices": [["Sparse", 0.5], ["Normal", 1.0], ["Heavy", 1.5], ["Horde", 2.0]]},
	{"key": "zombie_speed", "name": "Zombie Speed",
		"desc": "How fast the dead move.",
		"choices": [["Shamblers", 0.8], ["Normal", 1.0], ["Feral", 1.25]]},
	{"key": "zombie_damage", "name": "Zombie Strength",
		"desc": "Damage dealt by zombie attacks.",
		"choices": [["Weak", 0.6], ["Normal", 1.0], ["Deadly", 1.5]]},
	{"key": "zombie_senses", "name": "Zombie Senses",
		"desc": "Sight and hearing range of the dead.",
		"choices": [["Dull", 0.7], ["Normal", 1.0], ["Keen", 1.4]]},
	{"key": "wound_chance", "name": "Wounds & Bleeding",
		"desc": "Chance that zombie hits open a bleeding wound.",
		"choices": [["Rare", 0.5], ["Normal", 1.0], ["Brutal", 1.6]]},
	{"key": "loot", "name": "Loot Abundance",
		"desc": "Yield from props, chests, and zombie drops.",
		"choices": [["Scarce", 0.6], ["Normal", 1.0], ["Plentiful", 1.5]]},
	{"key": "xp_rate", "name": "XP Rate",
		"desc": "How quickly you earn levels and skill points.",
		"choices": [["Slow", 0.5], ["Normal", 1.0], ["Fast", 1.5]]},
	{"key": "day_length", "name": "Day Length",
		"desc": "Real time per in-game day.",
		"choices": [["Short (5 min)", 300.0], ["Normal (7 min)", 420.0], ["Long (10 min)", 600.0]]},
]
const SETTINGS_PATH := "user://settings.cfg"

## Starting backgrounds, chosen on the menu (Project Zomboid occupations).
const BACKGROUNDS := [
	{"id": "villager", "name": "Villager",
		"desc": "A balanced start: sword, food, and a bandage.",
		"kit": {"wooden_sword": 1, "berries": 5, "bandage": 1, "wood": 4, "stone": 2}, "equip": "wooden_sword"},
	{"id": "soldier", "name": "Soldier",
		"desc": "Iron sword and +20 health, but set in his ways: -25% XP.",
		"kit": {"iron_sword": 1, "berries": 3, "bandage": 1}, "equip": "iron_sword",
		"hp_bonus": 20, "xp_mult": 0.75},
	{"id": "hunter", "name": "Hunter",
		"desc": "Bow, a quiver of arrows, and +15% bow damage.",
		"kit": {"wooden_bow": 1, "arrow": 14, "berries": 4, "bandage": 1}, "equip": "wooden_bow",
		"bow_mult": 1.15},
	{"id": "apprentice", "name": "Mage Apprentice",
		"desc": "A staff, some essence, and +20 mana. Frail bookworm: -10 health.",
		"kit": {"apprentice_staff": 1, "essence": 3, "berries": 4}, "equip": "apprentice_staff",
		"mana_bonus": 20, "hp_bonus": -10},
]

var settings: Dictionary = {}
var background := "villager"

var day := 1
var time_of_day := 0.04  # ~07:00
var xp := 0
var level := 1
var skill_points := 0
var kills := 0

var player: Node = null
var world: Node = null

var _was_night := false
var _sfx_streams: Dictionary = {}
var _sfx_players: Array = []
var _sfx_next := 0

const SFX_NAMES := [
	"swing", "hit", "bow", "magic", "frost", "hurt", "zombie", "zombie_hit",
	"build", "pickup", "craft", "levelup", "explosion", "eat", "door", "crow", "splash",
]


func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	_load_settings()
	_setup_input()
	for sfx_name in SFX_NAMES:
		var path := "res://assets/sfx/%s.wav" % sfx_name
		if ResourceLoader.exists(path):
			_sfx_streams[sfx_name] = load(path)
	for i in 10:
		var p := AudioStreamPlayer.new()
		p.bus = "Master"
		add_child(p)
		_sfx_players.append(p)


func reset_run() -> void:
	day = 1
	time_of_day = 0.04
	xp = 0
	level = 1
	skill_points = 0
	kills = 0
	player = null
	world = null
	_was_night = false
	SkillTree.reset()


func setting(key: String) -> float:
	return float(settings.get(key, 1.0))


func set_setting(key: String, value: float) -> void:
	settings[key] = value
	_save_settings()


func _load_settings() -> void:
	for def in OPTION_DEFS:
		settings[def["key"]] = def["choices"][1][1] if def["key"] != "day_length" else 420.0
	var cfg := ConfigFile.new()
	if cfg.load(SETTINGS_PATH) == OK:
		for def in OPTION_DEFS:
			settings[def["key"]] = cfg.get_value("sandbox", def["key"], settings[def["key"]])
		background = cfg.get_value("player", "background", "villager")


func _save_settings() -> void:
	var cfg := ConfigFile.new()
	for def in OPTION_DEFS:
		cfg.set_value("sandbox", def["key"], settings[def["key"]])
	cfg.set_value("player", "background", background)
	cfg.save(SETTINGS_PATH)


func advance_time(delta: float) -> void:
	time_of_day += delta / setting("day_length")
	if time_of_day >= 1.0:
		time_of_day -= 1.0
		day += 1
		emit_signal("day_started", day)
	var night := is_night()
	if night and not _was_night:
		emit_signal("night_started", day)
	_was_night = night
	emit_signal("time_changed", day, time_of_day)


func is_night() -> bool:
	return time_of_day >= NIGHT_START and time_of_day < NIGHT_END


## 0.0 = full daylight, 1.0 = darkest night.
func darkness() -> float:
	var h := hour()
	if h >= 7.0 and h < 19.0:
		return 0.0
	if h >= 19.0 and h < 21.5:
		return (h - 19.0) / 2.5
	if h >= 4.5 and h < 7.0:
		return 1.0 - (h - 4.5) / 2.5
	return 1.0


func hour() -> float:
	return fposmod(time_of_day * 24.0 + 6.0, 24.0)


func clock_text() -> String:
	var h := hour()
	return "%02d:%02d" % [int(h), int(fmod(h, 1.0) * 60.0)]


func xp_needed() -> int:
	return 40 + level * 30


func bg_def() -> Dictionary:
	for b in BACKGROUNDS:
		if b["id"] == background:
			return b
	return BACKGROUNDS[0]


func set_background(id: String) -> void:
	background = id
	_save_settings()


func add_xp(amount: int) -> void:
	xp += maxi(1, roundi(amount * setting("xp_rate") * float(bg_def().get("xp_mult", 1.0))))
	while xp >= xp_needed():
		xp -= xp_needed()
		level += 1
		skill_points += 1
		emit_signal("level_gained", level)
		emit_signal("skill_points_changed", skill_points)
		play_sfx("levelup")
	emit_signal("xp_changed", xp, xp_needed(), level)


func spend_skill_point() -> bool:
	if skill_points <= 0:
		return false
	skill_points -= 1
	emit_signal("skill_points_changed", skill_points)
	return true


func play_sfx(sfx_name: String, volume_db := 0.0, pitch_jitter := 0.08) -> void:
	if not _sfx_streams.has(sfx_name):
		return
	var p: AudioStreamPlayer = _sfx_players[_sfx_next]
	_sfx_next = (_sfx_next + 1) % _sfx_players.size()
	p.stream = _sfx_streams[sfx_name]
	p.volume_db = volume_db
	p.pitch_scale = 1.0 + randf_range(-pitch_jitter, pitch_jitter)
	p.play()


# ----------------------------------------------------------------- input ----
func _setup_input() -> void:
	_key_action("move_up", [KEY_W, KEY_UP])
	_key_action("move_down", [KEY_S, KEY_DOWN])
	_key_action("move_left", [KEY_A, KEY_LEFT])
	_key_action("move_right", [KEY_D, KEY_RIGHT])
	_key_action("sprint", [KEY_SHIFT])
	_key_action("dodge", [KEY_SPACE])
	_key_action("interact", [KEY_E])
	_key_action("weapon_1", [KEY_1])
	_key_action("weapon_2", [KEY_2])
	_key_action("weapon_3", [KEY_3])
	_key_action("toggle_inventory", [KEY_TAB, KEY_I])
	_key_action("toggle_craft", [KEY_C])
	_key_action("toggle_build", [KEY_B])
	_key_action("toggle_skills", [KEY_K])
	_mouse_action("attack", MOUSE_BUTTON_LEFT)
	_mouse_action("special", MOUSE_BUTTON_RIGHT)


func _key_action(action: String, keys: Array) -> void:
	if InputMap.has_action(action):
		return
	InputMap.add_action(action)
	for k in keys:
		var ev := InputEventKey.new()
		ev.physical_keycode = k
		InputMap.action_add_event(action, ev)


func _mouse_action(action: String, button: int) -> void:
	if InputMap.has_action(action):
		return
	InputMap.add_action(action)
	var ev := InputEventMouseButton.new()
	ev.button_index = button
	InputMap.action_add_event(action, ev)
