extends Node
## Dev helper: drives the game and saves screenshots, then quits.
## Enabled only when the MZS_SHOT_DIR environment variable is set.

var dir := ""
var frame := 0


func _ready() -> void:
	dir = OS.get_environment("MZS_SHOT_DIR")


func _process(_delta: float) -> void:
	frame += 1
	var world = Game.world
	var hud = world.hud
	var player = Game.player
	match frame:
		40:
			_shot("01_day_world")
		45:
			hud.inventory_panel.visible = true
			hud.inventory_panel.refresh()
		55:
			_shot("02_inventory")
			hud.close_all_panels()
			hud.crafting_panel.visible = true
			hud.crafting_panel.refresh()
		65:
			_shot("03_crafting")
			hud.close_all_panels()
			Game.skill_points = 3
			hud.skills_panel.visible = true
			hud.skills_panel.refresh()
		75:
			_shot("04_skills")
			hud.close_all_panels()
			player.add_item("wooden_wall", 5)
			world.build_manager.enter_build("wooden_wall")
		85:
			_shot("05_build_mode")
			world.build_manager.exit_build()
			# set up a defended camp: walls, campfire, spikes
			var t: Vector2i = world.tilemap.local_to_map(player.position)
			world.occupied.erase(t + Vector2i(2, 0))
			world.place_structure("wooden_wall", t + Vector2i(2, 0))
			world.place_structure("wooden_wall", t + Vector2i(2, 1))
			world.place_structure("wooden_door", t + Vector2i(2, -1))
			world.place_structure("spike_trap", t + Vector2i(3, 0))
			world.place_structure("campfire", t + Vector2i(0, 2))
			world.place_structure("workbench", t + Vector2i(-1, 2))
		90:
			# night raid scene
			Game.time_of_day = 0.7
			for i in 6:
				var z = preload("res://scripts/enemies/Zombie.gd").new()
				z.setup(["walker", "runner", "brute"][i % 3])
				z.position = player.position + Vector2(120 + i * 30, -40 + i * 25)
				world.entities.add_child(z)
		120:
			player.add_item("apprentice_staff", 1)
			player.equipped = "apprentice_staff"
			player._spawn_projectile("fire", Vector2.RIGHT, 20.0, 0, false)
		126:
			_shot("06_night_battle")
		130:
			get_tree().quit()


func _shot(shot_name: String) -> void:
	var img := get_viewport().get_texture().get_image()
	img.save_png(dir.path_join(shot_name + ".png"))
	print("saved ", shot_name)
