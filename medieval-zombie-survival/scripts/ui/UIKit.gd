class_name UIKit
## Shared styling helpers for the parchment-and-timber UI look.

const BG := Color(0.12, 0.09, 0.07, 0.94)
const BORDER := Color(0.45, 0.31, 0.18)
const TEXT := Color(0.91, 0.86, 0.74)
const TEXT_DIM := Color(0.62, 0.57, 0.48)


static func panel_style(bg := BG, border := BORDER) -> StyleBoxFlat:
	var s := StyleBoxFlat.new()
	s.bg_color = bg
	s.border_color = border
	s.set_border_width_all(2)
	s.set_corner_radius_all(4)
	s.set_content_margin_all(10)
	return s


static func panel(min_size := Vector2.ZERO) -> PanelContainer:
	var p := PanelContainer.new()
	p.add_theme_stylebox_override("panel", panel_style())
	p.custom_minimum_size = min_size
	return p


static func label(text: String, size := 13, color := TEXT) -> Label:
	var l := Label.new()
	l.text = text
	l.add_theme_font_size_override("font_size", size)
	l.add_theme_color_override("font_color", color)
	return l


static func title(text: String) -> Label:
	var l := label(text, 18, Color(0.98, 0.92, 0.7))
	l.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	return l


static func button(text: String, size := 13) -> Button:
	var b := Button.new()
	b.text = text
	b.add_theme_font_size_override("font_size", size)
	var normal := panel_style(Color(0.2, 0.15, 0.1, 0.95))
	normal.set_content_margin_all(6)
	var hover := panel_style(Color(0.3, 0.22, 0.13, 0.95), Color(0.7, 0.52, 0.3))
	hover.set_content_margin_all(6)
	var pressed := panel_style(Color(0.09, 0.07, 0.05, 0.95))
	pressed.set_content_margin_all(6)
	var disabled := panel_style(Color(0.14, 0.12, 0.11, 0.8), Color(0.3, 0.27, 0.24))
	disabled.set_content_margin_all(6)
	b.add_theme_stylebox_override("normal", normal)
	b.add_theme_stylebox_override("hover", hover)
	b.add_theme_stylebox_override("pressed", pressed)
	b.add_theme_stylebox_override("disabled", disabled)
	b.add_theme_color_override("font_color", TEXT)
	b.add_theme_color_override("font_disabled_color", TEXT_DIM)
	return b


static func stat_bar(fill: Color) -> ProgressBar:
	var bar := ProgressBar.new()
	bar.show_percentage = false
	bar.custom_minimum_size = Vector2(170, 13)
	bar.max_value = 100.0
	var bg_style := StyleBoxFlat.new()
	bg_style.bg_color = Color(0.07, 0.06, 0.08, 0.85)
	bg_style.border_color = Color(0.3, 0.24, 0.18)
	bg_style.set_border_width_all(1)
	var fill_style := StyleBoxFlat.new()
	fill_style.bg_color = fill
	bar.add_theme_stylebox_override("background", bg_style)
	bar.add_theme_stylebox_override("fill", fill_style)
	return bar


static func icon_rect(tex: Texture2D, size := 36) -> TextureRect:
	var t := TextureRect.new()
	t.texture = tex
	t.custom_minimum_size = Vector2(size, size)
	t.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
	t.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	return t
