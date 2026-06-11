extends Node
## Global game state: clock, day counter, XP/levels, input map, sound.

signal time_changed(day: int, time_of_day: float)
signal day_started(day: int)
signal night_started(day: int)
signal xp_changed(xp: int, needed: int, level: int)
signal level_gained(level: int)
signal skill_points_changed(points: int)

const DAY_LENGTH := 420.0  # real seconds per in-game day
const NIGHT_START := 0.625  # 21:00 (time_of_day 0.0 == 06:00)
const NIGHT_END := 0.958    # 05:00

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
	"build", "pickup", "craft", "levelup", "explosion", "eat", "door",
]


func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
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


func advance_time(delta: float) -> void:
	time_of_day += delta / DAY_LENGTH
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


func add_xp(amount: int) -> void:
	xp += amount
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
