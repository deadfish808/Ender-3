extends CharacterBody2D
## The survivor: movement, melee/bow/staff combat, survival stats, inventory.

signal inventory_changed
signal died

const SPRITE_SCALE := Vector2(0.5, 0.5)  # textures are 2x resolution, rendered at half scale for finer pixels
const WALK_SPEED := 110.0
const SPRINT_SPEED := 170.0
const FISTS := {"name": "Fists", "type": "melee", "dmg": 6, "cooldown": 0.5, "knockback": 60}

var inventory: Dictionary = {}
var equipped := ""  # item id, "" = fists

var hp := 100.0
var stamina := 100.0
var mana := 50.0
var hunger := 100.0

var facing := "s"
var dead := false
var bleeding := false
var infected := false
var cold := false
var weapon_wear: Dictionary = {}  # item id -> accumulated wear (breaks at 100)
var aim_override := Vector2.ZERO  # used by the balance-sim bot
var _fishing := 0.0
var _warmth_check := 0.0
var _near_fire := false
var _bobber: Node2D

var _attack_cd := 0.0
var _special_cd := 0.0
var _iframes := 0.0
var _attack_anim := 0.0
var _stamina_delay := 0.0
var _knock := Vector2.ZERO
var _motion := Vector2.ZERO
var _dust_timer := 0.0
var _dodge_cd := 0.0
var _combo_stage := 0
var _combo_timer := 0.0

var _sprite: AnimatedSprite2D
var _light: PointLight2D
var _cam: Camera2D
var _target_zoom := 2.4


func _ready() -> void:
	add_to_group("player")
	collision_layer = 2
	collision_mask = 1 | 4
	var shape := CollisionShape2D.new()
	var circle := CircleShape2D.new()
	circle.radius = 7.0
	shape.shape = circle
	shape.position = Vector2(0, -4)
	add_child(shape)
	_build_sprite()
	_cam = Camera2D.new()
	_cam.zoom = Vector2(2.4, 2.4)
	_cam.position_smoothing_enabled = true
	_cam.position_smoothing_speed = 8.0
	add_child(_cam)
	_cam.make_current()
	_light = PointLight2D.new()
	_light.texture = load("res://assets/fx/light.png")
	_light.color = Color(1.0, 0.85, 0.6)
	_light.texture_scale = 1.3
	_light.energy = 0.0
	add_child(_light)
	var bg := Game.bg_def()
	for id in bg["kit"]:
		add_item(id, bg["kit"][id])
	equipped = bg.get("equip", "")
	hp = max_hp()
	mana = minf(mana, max_mana())


func _build_sprite() -> void:
	var tex: Texture2D = load("res://assets/chars/player_sheet.png")
	_sprite = AnimatedSprite2D.new()
	_sprite.sprite_frames = build_char_frames(tex)
	_sprite.offset = Vector2(0, -44)
	_sprite.scale = SPRITE_SCALE
	_sprite.animation = "idle_s"
	add_child(_sprite)
	_sprite.play("idle_s")


## Shared by Player and Zombie.
## Sheet layout (64x96 cells after Scale2x, 9 cols x 6 rows):
##   rows 0-2 (S/E/N): walk frames 0-5, idle frames 6-7
##   rows 3-5 (S/E/N): attack_melee 0-2, attack_bow 3-5, attack_staff 6-8
static func build_char_frames(tex: Texture2D) -> SpriteFrames:
	var fw := 64
	var fh := 96
	var frames := SpriteFrames.new()
	frames.remove_animation("default")
	var dirs := ["s", "e", "n"]
	for row in 3:
		var d: String = dirs[row]
		frames.add_animation("walk_" + d)
		frames.set_animation_speed("walk_" + d, 10.0)
		frames.set_animation_loop("walk_" + d, true)
		for f in 6:
			frames.add_frame("walk_" + d, _cell(tex, f, row, fw, fh))
		frames.add_animation("idle_" + d)
		frames.set_animation_speed("idle_" + d, 2.4)
		frames.set_animation_loop("idle_" + d, true)
		for f in 2:
			frames.add_frame("idle_" + d, _cell(tex, 6 + f, row, fw, fh))
		for k in 3:
			var kind: String = ["melee", "bow", "staff"][k]
			var anim := "attack_%s_%s" % [kind, d]
			frames.add_animation(anim)
			frames.set_animation_speed(anim, 18.0)
			frames.set_animation_loop(anim, false)
			for f in 3:
				frames.add_frame(anim, _cell(tex, k * 3 + f, row + 3, fw, fh))
	return frames


static func _cell(tex: Texture2D, col: int, row: int, fw: int, fh: int) -> AtlasTexture:
	var at := AtlasTexture.new()
	at.atlas = tex
	at.region = Rect2(col * fw, row * fh, fw, fh)
	return at


# ------------------------------------------------------------ main loop -----
func _physics_process(delta: float) -> void:
	if dead:
		return
	_attack_cd = maxf(0.0, _attack_cd - delta)
	_special_cd = maxf(0.0, _special_cd - delta)
	_iframes = maxf(0.0, _iframes - delta)
	_attack_anim = maxf(0.0, _attack_anim - delta)
	_stamina_delay = maxf(0.0, _stamina_delay - delta)
	_dodge_cd = maxf(0.0, _dodge_cd - delta)
	_combo_timer = maxf(0.0, _combo_timer - delta)
	if _combo_timer <= 0.0:
		_combo_stage = 0

	var input_dir := Input.get_vector("move_left", "move_right", "move_up", "move_down")
	if _fishing > 0.0:
		if input_dir != Vector2.ZERO:
			_stop_fishing(false)
		else:
			_fishing -= delta
			if _fishing <= 0.0:
				_stop_fishing(true)
	var sprinting: bool = Input.is_action_pressed("sprint") and stamina > 1.0 and input_dir != Vector2.ZERO
	var speed := SPRINT_SPEED if sprinting else WALK_SPEED
	var move := input_dir.normalized() if input_dir != Vector2.ZERO else Vector2.ZERO
	move.y *= 0.6  # isometric foreshortening
	# smooth acceleration / deceleration
	_motion = _motion.lerp(move * speed, 1.0 - exp(-10.0 * delta))
	if _motion.length() < 2.0 and move == Vector2.ZERO:
		_motion = Vector2.ZERO
	velocity = _motion + _knock
	_knock = _knock.move_toward(Vector2.ZERO, delta * 600.0)
	move_and_slide()

	if sprinting:
		stamina = maxf(0.0, stamina - 12.0 * delta)
		_stamina_delay = 0.8
		_dust_timer -= delta
		if _dust_timer <= 0.0:
			_dust_timer = 0.22
			FX.dust(get_parent(), position)
			Game.world.alert_zombies(position, 90.0)
	elif _stamina_delay <= 0.0:
		stamina = minf(100.0, stamina + (7.5 if cold else 15.0) * delta)

	_update_survival(delta)
	_update_anim(input_dir)
	_update_light()

	if Input.is_action_just_pressed("dodge") and not _ui_blocked():
		_dodge(input_dir)
	if Input.is_action_pressed("attack") and _attack_cd <= 0.0 and not _ui_blocked():
		_attack()


func _update_survival(delta: float) -> void:
	_warmth_check -= delta
	if _warmth_check <= 0.0:
		_warmth_check = 0.5
		_near_fire = false
		for fire in get_tree().get_nodes_in_group("warmth"):
			if fire.position.distance_to(position) < 115.0:
				_near_fire = true
				break
		cold = (Game.is_night() or Game.world.weather == "rain") and not _near_fire
	var hunger_rate := 0.16 * (1.3 if cold else 1.0)
	hunger = maxf(0.0, hunger - hunger_rate * delta)
	if cold and Game.is_night() and Game.world.weather == "rain":
		_apply_damage(0.2 * delta, true)  # soaked and freezing in the dark
	if hunger <= 0.0:
		_apply_damage(0.5 * delta, true)  # starvation: slow doom, time to act
	elif hunger > 70.0:
		hp = minf(max_hp(), hp + 0.35 * delta)  # healing is slow; carry bandages
	if bleeding:
		_apply_damage(0.35 * delta, true)
	if infected:
		_apply_damage(0.15 * delta, true)  # wound-rot: slow doom without a remedy
	if SkillTree.has_skill("second_wind") and hp < max_hp() * 0.3:
		hp = minf(max_hp(), hp + 2.0 * delta)
	mana = minf(max_mana(), mana + SkillTree.mana_regen() * delta)


func _update_light() -> void:
	_light.energy = Game.darkness() * 0.85


func _update_anim(input_dir: Vector2) -> void:
	if _attack_anim > 0.0:
		return
	var moving := _motion.length() > 8.0
	var aim := _aim_dir()
	var dir_source := input_dir if input_dir != Vector2.ZERO else (_motion if moving else aim)
	facing = _dir_name(dir_source)
	var anim_dir := "e" if facing == "w" else facing
	_sprite.flip_h = facing == "w"
	var anim := ("walk_" if moving else "idle_") + anim_dir
	_sprite.speed_scale = clampf(_motion.length() / WALK_SPEED, 0.7, 1.7) if moving else 1.0
	if _sprite.animation != anim:
		_sprite.play(anim)


func _dir_name(v: Vector2) -> String:
	if absf(v.x) > absf(v.y) * 1.2:
		return "e" if v.x > 0 else "w"
	return "s" if v.y > 0 else "n"


func _aim_dir() -> Vector2:
	var d := (aim_override - position) if aim_override != Vector2.ZERO else (get_global_mouse_position() - position)
	return d.normalized() if d.length() > 2.0 else Vector2.DOWN


func _ui_blocked() -> bool:
	var world = Game.world
	if world == null:
		return false
	if world.build_manager and world.build_manager.is_building():
		return true
	return world.hud and world.hud.ui_blocking()


func _dodge(input_dir: Vector2) -> void:
	if _dodge_cd > 0.0 or stamina < 15.0:
		return
	var dir := input_dir.normalized() if input_dir != Vector2.ZERO else _aim_dir()
	dir.y *= 0.6
	stamina -= 15.0
	_stamina_delay = 0.7
	_dodge_cd = 0.9
	_iframes = maxf(_iframes, 0.35)
	_knock += dir * 300.0
	FX.dust(get_parent(), position)
	Game.play_sfx("swing", -10.0, 0.2)
	_sprite.scale = Vector2(1.1, 0.82) * SPRITE_SCALE
	var tw := create_tween()
	tw.tween_property(_sprite, "scale", SPRITE_SCALE, 0.25)


## Weapons wear out with use and eventually break (carry a spare).
func _wear_weapon(amount: float) -> void:
	if equipped == "":
		return
	weapon_wear[equipped] = weapon_wear.get(equipped, 0.0) + amount
	if weapon_wear[equipped] >= 100.0:
		var broken := equipped
		weapon_wear.erase(broken)
		remove_item(broken, 1)
		Game.play_sfx("hit", -2.0)
		FX.float_text(get_parent(), position, "%s broke!" % ItemDB.display_name(broken), Color(1.0, 0.5, 0.3))


func weapon_condition(id: String) -> int:
	return clampi(100 - int(weapon_wear.get(id, 0.0)), 0, 100)


func _roll_crit(dmg: float) -> Array:
	if randf() < 0.10:
		return [dmg * 1.6, true]
	return [dmg, false]


# --------------------------------------------------------------- combat -----
func weapon_stats() -> Dictionary:
	if equipped != "" and inventory.get(equipped, 0) > 0:
		return ItemDB.get_item(equipped)
	return FISTS


func _attack() -> void:
	var w := weapon_stats()
	var kind: String = w["type"]
	match kind:
		"melee":
			_melee_attack(w)
		"bow":
			_bow_attack(w)
		"staff":
			_staff_attack(w)
		"tool":
			_cast_line()


func _play_attack_anim(kind: String) -> void:
	var aim := _aim_dir()
	facing = _dir_name(aim)
	var anim_dir := "e" if facing == "w" else facing
	_sprite.flip_h = facing == "w"
	_sprite.speed_scale = 1.0
	_sprite.play("attack_%s_%s" % [kind, anim_dir])
	_attack_anim = 0.18


func _melee_attack(w: Dictionary) -> void:
	if stamina < 4.0:
		return
	stamina = maxf(0.0, stamina - 7.0)
	_stamina_delay = 0.6
	var combo_mult: float = [1.0, 1.15, 1.5][_combo_stage]
	var finisher := _combo_stage == 2
	var exhausted := stamina < 20.0
	if exhausted:
		combo_mult *= 0.6  # too tired to swing properly
	_attack_cd = float(w["cooldown"]) * (1.5 if finisher else 1.0) * (1.4 if exhausted else 1.0)
	_combo_timer = 1.1
	_play_attack_anim("melee")
	var aim := _aim_dir()
	_knock += aim * (60.0 if finisher else 46.0)  # forward lunge
	var origin := position + aim * 14.0
	FX.slash(get_parent(), position + aim * 24.0 + Vector2(0, -14), aim.angle(),
			1.35 if finisher else 1.0)
	Game.play_sfx("swing", -6.0 if not finisher else -2.0)
	Game.world.alert_zombies(position, 130.0)
	var dmg := float(w["dmg"]) * SkillTree.melee_mult() * combo_mult
	var crit_roll := _roll_crit(dmg)
	dmg = crit_roll[0]
	var crit: bool = crit_roll[1]
	var knockback := float(w.get("knockback", 60)) * SkillTree.knockback_mult() * (1.8 if finisher else 1.0)
	# zombies in arc
	var hit_zombies := []
	for z in get_tree().get_nodes_in_group("zombies"):
		var to_z: Vector2 = z.position - position
		if to_z.length() < 46.0 and absf(aim.angle_to(to_z.normalized())) < 1.35:
			hit_zombies.append(z)
	_wear_weapon(0.8)
	if not hit_zombies.is_empty():
		hit_zombies.sort_custom(func(a, b): return a.position.distance_squared_to(origin) < b.position.distance_squared_to(origin))
		var count := hit_zombies.size() if SkillTree.has_skill("cleave") else 1
		for i in mini(count, hit_zombies.size()):
			hit_zombies[i].hit(dmg, position, knockback * (1.3 if crit else 1.0))
		_combo_stage = (_combo_stage + 1) % 3
	# harvest the closest node in the arc
	var best: Node = null
	var best_d := 52.0
	for h in get_tree().get_nodes_in_group("harvestable"):
		var to_h: Vector2 = h.position - position
		if to_h.length() < best_d and absf(aim.angle_to(to_h.normalized())) < 1.35:
			best = h
			best_d = to_h.length()
	if best:
		best.hit(dmg)


func _bow_attack(w: Dictionary) -> void:
	if inventory.get("arrow", 0) <= 0:
		FX.float_text(get_parent(), position, "no arrows!", Color(1, 0.6, 0.5))
		_attack_cd = 0.4
		return
	remove_item("arrow", 1)
	_wear_weapon(0.4)
	_attack_cd = float(w["cooldown"]) * SkillTree.bow_cooldown_mult()
	_play_attack_anim("bow")
	Game.play_sfx("bow", -4.0)
	Game.world.alert_zombies(position, 60.0)  # bows are quiet: the smart choice
	var aim := _aim_dir()
	var crit_roll := _roll_crit(float(w["dmg"]) * SkillTree.bow_mult() * float(Game.bg_def().get("bow_mult", 1.0)))
	var dmg: float = crit_roll[0]
	var angles := [0.0]
	if SkillTree.has_skill("multishot"):
		angles = [-0.16, 0.0, 0.16]
	for a in angles:
		_spawn_projectile("arrow", aim.rotated(a), dmg, SkillTree.arrow_pierce(), false)


func _staff_attack(w: Dictionary) -> void:
	var cost := float(w["mana"])
	if mana < cost:
		FX.float_text(get_parent(), position, "no mana!", Color(0.6, 0.7, 1))
		_attack_cd = 0.4
		return
	mana -= cost
	_wear_weapon(0.3)
	_attack_cd = float(w["cooldown"])
	_play_attack_anim("staff")
	Game.play_sfx("magic", -6.0)
	Game.world.alert_zombies(position, 200.0)  # magic rings out across the fields
	var crit_roll := _roll_crit(float(w["dmg"]) * SkillTree.spell_mult())
	_spawn_projectile("fire", _aim_dir(), crit_roll[0], 0, SkillTree.has_skill("fireball"))


func _spawn_projectile(kind: String, dir: Vector2, dmg: float, pierce: int, explode: bool) -> void:
	var p := preload("res://scripts/combat/Projectile.gd").new()
	p.setup(kind, dir, dmg, pierce, explode)
	p.position = position + dir * 12.0 + Vector2(0, -16)
	get_parent().add_child(p)


## Fishing: cast at open water, stand still, wait for the bite.
func _cast_line() -> void:
	if _fishing > 0.0:
		return
	var target := get_global_mouse_position()
	var world = Game.world
	if position.distance_to(target) > 95.0:
		FX.float_text(get_parent(), position, "too far to cast", Color(0.8, 0.8, 0.8))
		_attack_cd = 0.4
		return
	if world.terrain_mat.get(world.world_to_tile(target), "") != "water":
		FX.float_text(get_parent(), position, "cast at open water", Color(0.8, 0.8, 0.8))
		_attack_cd = 0.4
		return
	_attack_cd = 0.5
	_fishing = randf_range(2.8, 5.5)
	_play_attack_anim("bow")
	Game.play_sfx("splash", -10.0)
	Game.world.alert_zombies(position, 40.0)
	FX.ring(get_parent(), target, 14.0, Color(0.6, 0.75, 0.9))
	_bobber = FX.bobber(get_parent(), target)
	_wear_weapon(0.5)


func _stop_fishing(success: bool) -> void:
	_fishing = 0.0
	if _bobber and is_instance_valid(_bobber):
		_bobber.queue_free()
	_bobber = null
	if success:
		if randf() < 0.7:
			add_item("raw_fish", 1)
			Game.play_sfx("pickup", -4.0)
			Game.add_xp(3)
			FX.float_text(get_parent(), position, "caught a fish!", Color(0.7, 0.85, 1.0))
		else:
			FX.float_text(get_parent(), position, "it got away...", Color(0.7, 0.7, 0.75))


func _frost_nova() -> void:
	if not SkillTree.has_skill("frost_nova") or _special_cd > 0.0 or mana < 20.0:
		return
	mana -= 20.0
	_special_cd = 6.0
	Game.play_sfx("frost")
	Game.world.alert_zombies(position, 220.0)
	FX.ring(get_parent(), position, 130.0, Color(0.6, 0.85, 1.0))
	var dmg := 12.0 * SkillTree.spell_mult()
	for z in get_tree().get_nodes_in_group("zombies"):
		if z.position.distance_to(position) < 130.0:
			z.apply_slow(0.4, 4.0)
			z.hit(dmg, position, 40.0)


func take_damage(amount: float, from_pos: Vector2, wound_chance := 0.0) -> void:
	if _iframes > 0.0 or dead:
		return
	_stop_fishing(false)
	_iframes = 0.6
	_knock = (position - from_pos).normalized() * 140.0
	shake_camera(3.5)
	Game.play_sfx("hurt")
	if not bleeding and randf() < wound_chance:
		bleeding = true
		FX.float_text(get_parent(), position, "wounded — bleeding!", Color(1.0, 0.35, 0.3))
		if not infected and randf() < 0.25:
			infected = true
			Game.world.hud.announce("The wound festers... find or brew a Plague Remedy", Color(0.8, 0.5, 0.9))
	_apply_damage(amount * SkillTree.damage_taken_mult(), false)
	_sprite.modulate = Color(1, 0.4, 0.4)
	var tw := create_tween()
	tw.tween_property(_sprite, "modulate", Color.WHITE, 0.25)


func _apply_damage(amount: float, _quiet: bool) -> void:
	hp -= amount
	if hp <= 0.0 and not dead:
		dead = true
		hp = 0.0
		_sprite.modulate = Color(0.6, 0.5, 0.5)
		emit_signal("died")
		Game.world.game_over()


# -------------------------------------------------------------- actions -----
func _unhandled_input(event: InputEvent) -> void:
	if dead:
		return
	if event is InputEventMouseButton and event.pressed:
		if event.button_index == MOUSE_BUTTON_WHEEL_UP:
			_set_zoom(_target_zoom * 1.13)
			return
		if event.button_index == MOUSE_BUTTON_WHEEL_DOWN:
			_set_zoom(_target_zoom / 1.13)
			return
	if event.is_action_pressed("special"):
		if not _ui_blocked():
			_frost_nova()
	elif event.is_action_pressed("interact"):
		_interact()
	elif event.is_action_pressed("weapon_1"):
		_cycle_weapon("melee")
	elif event.is_action_pressed("weapon_2"):
		_cycle_weapon("bow")
	elif event.is_action_pressed("weapon_3"):
		_cycle_weapon("staff")


func _interact() -> void:
	var best: Node = null
	var best_d := 52.0
	for n in get_tree().get_nodes_in_group("interactable"):
		var d: float = n.position.distance_to(position)
		if d < best_d:
			best = n
			best_d = d
	if best:
		best.interact(self)


func _cycle_weapon(kind: String) -> void:
	var owned := []
	for id in inventory:
		if inventory[id] > 0 and ItemDB.get_item(id).get("type", "") == kind:
			owned.append(id)
	if owned.is_empty():
		FX.float_text(get_parent(), position, "no %s weapon" % kind, Color(0.8, 0.8, 0.8))
		return
	owned.sort_custom(func(a, b): return ItemDB.get_item(a)["dmg"] < ItemDB.get_item(b)["dmg"])
	if equipped in owned:
		var idx := (owned.find(equipped) + 1) % owned.size()
		equipped = owned[idx]
	else:
		equipped = owned[owned.size() - 1]
	emit_signal("inventory_changed")


func use_item(id: String) -> void:
	if inventory.get(id, 0) <= 0:
		return
	var item := ItemDB.get_item(id)
	match item.get("type", ""):
		"food":
			remove_item(id, 1)
			hunger = minf(100.0, hunger + float(item.get("food", 0)))
			hp = minf(max_hp(), hp + float(item.get("heal", 0)))
			if item.get("cures", false):
				bleeding = false
			if item.get("cures_infection", false):
				infected = false
				FX.float_text(get_parent(), position, "the rot recedes", Color(0.7, 0.9, 0.7))
			Game.play_sfx("eat")
		"melee", "bow", "staff", "tool":
			equipped = id
			emit_signal("inventory_changed")
		"buildable":
			Game.world.hud.close_all_panels()
			Game.world.build_manager.enter_build(id)


# ------------------------------------------------------------ inventory -----
func add_item(id: String, count := 1) -> void:
	inventory[id] = inventory.get(id, 0) + count
	emit_signal("inventory_changed")


func remove_item(id: String, count := 1) -> bool:
	if inventory.get(id, 0) < count:
		return false
	inventory[id] -= count
	if inventory[id] <= 0:
		inventory.erase(id)
		if equipped == id:
			equipped = ""
	emit_signal("inventory_changed")
	return true


func has_all(cost: Dictionary) -> bool:
	for mat in cost:
		if inventory.get(mat, 0) < cost[mat]:
			return false
	return true


func max_hp() -> float:
	return 100.0 + SkillTree.bonus_hp() + float(Game.bg_def().get("hp_bonus", 0))


func max_mana() -> float:
	return 50.0 + SkillTree.bonus_mana() + float(Game.bg_def().get("mana_bonus", 0))


func _set_zoom(value: float) -> void:
	_target_zoom = clampf(value, 1.1, 3.6)
	var tw := create_tween()
	tw.tween_property(_cam, "zoom", Vector2.ONE * _target_zoom, 0.18).set_trans(Tween.TRANS_SINE)


func shake_camera(amount := 3.0) -> void:
	var tw := create_tween()
	for i in 4:
		var falloff := amount * (1.0 - i / 4.0)
		tw.tween_property(_cam, "offset",
				Vector2(randf_range(-falloff, falloff), randf_range(-falloff, falloff)), 0.04)
	tw.tween_property(_cam, "offset", Vector2.ZERO, 0.05)


func on_skills_changed() -> void:
	hp = minf(hp, max_hp())
	mana = minf(mana, max_mana())
