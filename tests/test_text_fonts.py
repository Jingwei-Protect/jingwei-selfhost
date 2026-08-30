"""Shared CJK-capable font resolution for visible text layers."""

from __future__ import annotations

from PIL import Image, ImageDraw

from core.text_fonts import font_renders_text, get_text_font, text_needs_cjk


def test_text_needs_cjk() -> None:
    assert text_needs_cjk("小明")
    assert not text_needs_cjk("Jingwei")


def test_get_text_font_renders_chinese() -> None:
    font = get_text_font(32, "画师")
    assert font_renders_text(font, "画师", 32)


def test_visible_layers_render_chinese_masks() -> None:
    from core.artist_emboss import _measure_text
    from core.displacement_watermark import _render_word_mask
    from core.emboss_texture import _build_text_layer

    text = "小明"
    assert _render_word_mask(text, 48).max() > 0.5
    assert _build_text_layer(400, 300, text, "normal", 42).max() > 0

    font = get_text_font(24, text)
    probe = Image.new("RGB", (1, 1))
    tw, th = _measure_text(ImageDraw.Draw(probe), text, font)
    assert tw > 10 and th > 10
