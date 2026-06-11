extends Node2D
## Ghost-preview placement of buildable structures on the iso grid.

var active_item := ""
var _ghost: Sprite2D


func _ready() -> void:
	z_index = 90


func enter_build(item_id: String) -> void:
	exit_build()
	active_item = item_id
	_ghost = Sprite2D.new()
	var cfg: Dictionary = ItemDB.BUILDABLES[item_id]
	if cfg.get("frames", 0) > 0:
		var fs: Vector2i = cfg["frame_size"]
		var at := AtlasTexture.new()
		at.atlas = load(cfg["texture"])
		at.region = Rect2(0, 0, fs.x, fs.y)
		_ghost.texture = at
		_ghost.offset = Vector2(0, 16.0 - fs.y / 2.0)
	else:
		_ghost.texture = load(cfg["texture"])
		_ghost.offset = Vector2(0, 16.0 - _ghost.texture.get_height() / 2.0)
	add_child(_ghost)


func exit_build() -> void:
	active_item = ""
	if _ghost:
		_ghost.queue_free()
		_ghost = null


func is_building() -> bool:
	return active_item != ""


func _process(_delta: float) -> void:
	if not is_building():
		return
	var world := Game.world
	var tile: Vector2i = world.tilemap.local_to_map(get_global_mouse_position())
	_ghost.position = world.tilemap.map_to_local(tile)
	var ok: bool = world.can_place(tile)
	_ghost.modulate = Color(0.5, 1.0, 0.5, 0.6) if ok else Color(1.0, 0.4, 0.4, 0.6)


func _unhandled_input(event: InputEvent) -> void:
	if not is_building():
		return
	if event.is_action_pressed("attack"):
		var player = Game.player
		if player == null or player.inventory.get(active_item, 0) <= 0:
			exit_build()
			return
		var tile: Vector2i = Game.world.tilemap.local_to_map(get_global_mouse_position())
		if Game.world.place_structure(active_item, tile):
			player.remove_item(active_item, 1)
			if player.inventory.get(active_item, 0) <= 0:
				exit_build()
		get_viewport().set_input_as_handled()
	elif event.is_action_pressed("special") or event.is_action_pressed("ui_cancel"):
		exit_build()
		get_viewport().set_input_as_handled()
