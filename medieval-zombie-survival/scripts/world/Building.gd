extends StaticBody2D
## A pre-built town building: large multi-tile scenery with collision and light.

const CONFIG := {
	"cottage_a": {"tex": "res://assets/buildings/cottage_a.png", "w": 3, "h": 3},
	"cottage_b": {"tex": "res://assets/buildings/cottage_b.png", "w": 3, "h": 3},
	"tavern": {"tex": "res://assets/buildings/tavern.png", "w": 5, "h": 3},
	"forge": {"tex": "res://assets/buildings/forge.png", "w": 4, "h": 3,
			"light": Vector2(48, -108), "light_color": Color(1.0, 0.62, 0.3),
			"light_energy": 0.9, "always_lit": true},
	"manor": {"tex": "res://assets/buildings/manor.png", "w": 6, "h": 3},
	"castle_keep": {"tex": "res://assets/buildings/castle_keep.png", "w": 5, "h": 4},
	"round_tower": {"tex": "res://assets/buildings/round_tower.png", "w": 1, "h": 1, "small": true,
			"light": Vector2(0, -60), "light_color": Color(1.0, 0.78, 0.5), "light_energy": 0.9},
	"well": {"tex": "res://assets/buildings/well.png", "w": 1, "h": 1, "small": true},
	"lamp_post": {"tex": "res://assets/buildings/lamp_post.png", "w": 1, "h": 1, "small": true,
			"light": Vector2(0, -46), "light_color": Color(1.0, 0.8, 0.5), "light_energy": 1.2},
}

var kind := ""
var _cfg: Dictionary
var _light: PointLight2D


func setup(p_kind: String) -> void:
	kind = p_kind
	_cfg = CONFIG[kind]


func _ready() -> void:
	collision_layer = 1
	collision_mask = 0
	var tex: Texture2D = load(_cfg["tex"])
	var spr := Sprite2D.new()
	spr.texture = tex
	var tw := float(tex.get_width())
	var th := float(tex.get_height())
	if _cfg.get("small", false):
		# node sits at the tile center; sprite feet at the bottom of the image
		spr.offset = Vector2(0, 2.0 - th / 2.0)
		var shape := CollisionShape2D.new()
		var circle := CircleShape2D.new()
		circle.radius = 8.0
		shape.shape = circle
		shape.position = Vector2(0, -3)
		add_child(shape)
	else:
		# node sits at the south corner of the footprint diamond
		var w := int(_cfg["w"])
		var h := int(_cfg["h"])
		var south := Vector2(32.0 * w, th - 2.0)
		spr.offset = Vector2(tw / 2.0 - south.x, th / 2.0 - south.y)
		var poly := CollisionPolygon2D.new()
		poly.polygon = PackedVector2Array([
			Vector2(0, 0),
			Vector2(-32.0 * w, -16.0 * w),
			Vector2(32.0 * (h - w), -16.0 * (w + h)),
			Vector2(32.0 * h, -16.0 * h),
		])
		add_child(poly)
	add_child(spr)
	if _cfg.has("light"):
		_light = PointLight2D.new()
		_light.texture = load("res://assets/fx/light.png")
		_light.position = _cfg["light"]
		_light.color = _cfg["light_color"]
		_light.texture_scale = 1.0
		_light.energy = 0.0
		add_child(_light)


func _process(_delta: float) -> void:
	if _light:
		var base: float = 0.45 if _cfg.get("always_lit", false) else 0.0
		_light.energy = base + Game.darkness() * float(_cfg["light_energy"])
