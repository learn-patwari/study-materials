"""Tests for the asset pipeline's caption removal and canvas normalization.

The raw artwork carries its filename burned into the picture. These tests build
synthetic images with known geometry so the trimming rules are pinned down
without depending on the shipped art.
"""
import pytest

PIL = pytest.importorskip("PIL", reason="Pillow is only needed for the asset pipeline")

from PIL import Image  # noqa: E402

from prepare_assets import (  # noqa: E402
    CANVAS_H,
    CANVAS_W,
    band_width,
    find_content_bands,
    fit_to_canvas,
    is_caption_band,
    row_ink,
    square_pad,
    strip_caption,
    trim_alpha,
)


def blank(width=200, height=400):
    return Image.new("RGBA", (width, height), (0, 0, 0, 0))


def draw(image, left, top, right, bottom, alpha=255):
    """Fill an opaque rectangle, inclusive of the given bounds."""
    for y in range(top, bottom + 1):
        for x in range(left, right + 1):
            image.putpixel((x, y), (20, 20, 20, alpha))
    return image


def caption_strip(image, top, height=10, width=180):
    """A thin, wide line of 'text' like the one baked into the raw art."""
    left = (image.width - width) // 2
    return draw(image, left, top, left + width - 1, top + height - 1)


class TestBandDetection:
    def test_single_shape_is_one_band(self):
        img = draw(blank(), 40, 50, 160, 300)
        assert len(find_content_bands(row_ink(img), img.width, img.height)) == 1

    def test_detached_shapes_are_separate_bands(self):
        img = draw(blank(), 40, 50, 160, 200)
        draw(img, 40, 280, 160, 340)
        bands = find_content_bands(row_ink(img), img.width, img.height)
        assert len(bands) == 2

    def test_narrow_gaps_are_merged(self):
        """A faint seam through one shape must not split it in two."""
        img = draw(blank(), 40, 50, 160, 200)
        draw(img, 40, 203, 160, 300)  # 2px gap, under MERGE_GAP_FRAC of 400
        assert len(find_content_bands(row_ink(img), img.width, img.height)) == 1

    def test_empty_image_has_no_bands(self):
        img = blank()
        assert find_content_bands(row_ink(img), img.width, img.height) == []

    def test_band_reports_its_extent(self):
        img = draw(blank(), 40, 50, 160, 200)
        (top, bottom, mass), = find_content_bands(row_ink(img), img.width, img.height)
        assert (top, bottom) == (50, 200)
        assert mass == 121 * 151

    def test_band_width_measures_ink(self):
        img = draw(blank(), 40, 50, 160, 200)
        assert band_width(img, 50, 200) == 121


class TestCaptionDetection:
    def test_bottom_caption_is_detected(self):
        img = caption_strip(blank(), top=385)
        assert is_caption_band(img, 385, 394)

    def test_top_caption_is_detected(self):
        img = caption_strip(blank(), top=8)
        assert is_caption_band(img, 8, 17)

    def test_thin_wide_band_in_the_middle_is_kept(self):
        """Shape, not size — a belt or outstretched arm is not a caption."""
        img = caption_strip(blank(), top=200)
        assert not is_caption_band(img, 200, 209)

    def test_tall_band_at_the_edge_is_kept(self):
        """Shoes reach the bottom of the frame but are far too tall to be text."""
        img = draw(blank(), 40, 330, 160, 399)
        assert not is_caption_band(img, 330, 399)

    def test_narrow_band_at_the_edge_is_kept(self):
        """A caption spans the frame; a foot does not."""
        img = draw(blank(), 90, 380, 120, 399)
        assert not is_caption_band(img, 380, 399)


class TestStripCaption:
    def test_removes_bottom_caption(self):
        img = draw(blank(), 40, 30, 160, 300)
        caption_strip(img, top=385)
        result = strip_caption(img)
        assert result.height == 300 - 30 + 1

    def test_removes_top_and_bottom_captions(self):
        img = draw(blank(), 40, 40, 160, 300)
        caption_strip(img, top=8)
        caption_strip(img, top=385)
        result = strip_caption(img)
        assert result.height == 300 - 40 + 1

    def test_keeps_a_detached_figure_below_the_body(self):
        """Regression: keeping only the heaviest band amputated the legs.

        The caption carries more ink than the shoes do, so ink alone cannot
        tell them apart.
        """
        img = draw(blank(), 60, 30, 140, 200)   # body
        draw(img, 70, 250, 130, 260)            # legs
        draw(img, 50, 300, 150, 350)            # shoes
        caption_strip(img, top=385)

        result = strip_caption(img)

        assert result.height == 350 - 30 + 1, "figure below the body was cut off"

    def test_untouched_when_there_is_no_caption(self):
        img = draw(blank(), 40, 30, 160, 300)
        assert strip_caption(img).size == img.size

    def test_never_strips_everything(self):
        """A lone caption-shaped band is all there is — keep it rather than
        return an empty image."""
        img = caption_strip(blank(), top=385)
        assert strip_caption(img).size == img.size


class TestNormalization:
    def test_trim_alpha_crops_to_ink(self):
        img = draw(blank(), 40, 50, 160, 200)
        assert trim_alpha(img).size == (121, 151)

    def test_fit_to_canvas_exact_size(self):
        img = draw(blank(100, 300), 10, 10, 90, 290)
        assert fit_to_canvas(trim_alpha(img), CANVAS_W, CANVAS_H).size == (CANVAS_W, CANVAS_H)

    def test_fit_to_canvas_anchors_to_the_bottom(self):
        """Feet stay planted so the character doesn't hover between poses."""
        img = draw(blank(100, 300), 10, 10, 90, 290)
        canvas = fit_to_canvas(trim_alpha(img), CANVAS_W, CANVAS_H)
        bbox = canvas.getchannel("A").getbbox()
        assert bbox[3] == CANVAS_H

    def test_fit_to_canvas_centres_horizontally(self):
        img = draw(blank(100, 300), 10, 10, 90, 290)
        canvas = fit_to_canvas(trim_alpha(img), CANVAS_W, CANVAS_H)
        bbox = canvas.getchannel("A").getbbox()
        assert abs((CANVAS_W - bbox[2]) - bbox[0]) <= 1

    def test_wide_and_tall_poses_land_on_the_same_canvas(self):
        tall = trim_alpha(draw(blank(216, 400), 10, 10, 200, 390))
        wide = trim_alpha(draw(blank(409, 337), 10, 10, 400, 330))
        assert (
            fit_to_canvas(tall, CANVAS_W, CANVAS_H).size
            == fit_to_canvas(wide, CANVAS_W, CANVAS_H).size
        )

    def test_square_pad_makes_a_square(self):
        img = draw(blank(234, 240), 0, 0, 233, 239)
        padded = square_pad(img)
        assert padded.width == padded.height == 240
