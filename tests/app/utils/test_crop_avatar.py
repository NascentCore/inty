"""Tests for avatar crop boundary helpers and image cropping behavior."""

import os
import random
import tempfile

import pytest
from PIL import Image, ImageChops

from app.utils.crop_avatar import (
    _calculate_crop_square_boundaries,
    _calculate_top_square_boundaries,
    crop_avatar,
)
from app.utils.image import ImageSize


def _gen_random_image(width, height):
    img = Image.new("RGB", (width, height), (255, 255, 255))
    pixels = img.load()
    for x in range(width):
        for y in range(height):
            pixels[x, y] = (
                random.randint(0, 255),
                random.randint(0, 255),
                random.randint(0, 255),
            )
    return img


def test_crop_top_square_for_square_image():
    img = _gen_random_image(100, 100)
    x, y, w, h = _calculate_top_square_boundaries(100, 100)
    cropped_img = img.crop((x, y, x + w, y + h))
    assert cropped_img == img


def test_crop_top_square_for_portrait_image():
    img = _gen_random_image(100, 200)
    x, y, w, h = _calculate_top_square_boundaries(100, 200)
    cropped_img = img.crop((x, y, x + w, y + h))
    assert cropped_img == img.crop((0, 0, 100, 100))


def test_crop_top_square_for_landscape_image():
    img = _gen_random_image(200, 100)
    x, y, w, h = _calculate_top_square_boundaries(200, 100)
    cropped_img = img.crop((x, y, x + w, y + h))
    assert cropped_img == img.crop((50, 0, 150, 100))


def _draw_setup(img_shape, face_coords, avatar_square):
    # Draw img_shape and avatar_square with edges in black, fill the image with white
    from PIL import ImageDraw

    # Create a white image with the specified dimensions
    img = Image.new("RGB", img_shape, (255, 255, 255))
    draw = ImageDraw.Draw(img)

    x, y, w, h = face_coords
    # Draw the face rectangle with light blue fill and black outline
    draw.rectangle(
        (x, y, x + w, y + h),
        outline=(0, 0, 0),
        fill=(173, 216, 230),
        width=1,
    )

    # Draw the image boundary (full image) with black edges
    draw.rectangle(
        [0, 0, img_shape[0] - 1, img_shape[1] - 1], outline=(0, 0, 0), width=1
    )

    x1, y1, x2, y2 = (
        avatar_square[0],
        avatar_square[1],
        avatar_square[0] + avatar_square[2],
        avatar_square[1] + avatar_square[3],
    )
    draw.rectangle((x1, y1, x2, y2), outline=(0, 0, 0), width=1)

    img.show()


def test_calculate_crop_square_boundaries():
    img_shape = (100, 100)
    face_coords = (10, 10, 20, 30)

    with pytest.raises(ValueError):
        _calculate_crop_square_boundaries(face_coords, 0.9, img_shape)

    # In certain bounary, expansion ration in [3.9, 4/3)
    avatar_square = _calculate_crop_square_boundaries(face_coords, 3.9 / 3, img_shape)
    assert avatar_square == (1, 6, 39, 39)
    avatar_square = _calculate_crop_square_boundaries(face_coords, 3.99 / 3, img_shape)
    assert avatar_square == (1, 6, 39, 39)
    avatar_square = _calculate_crop_square_boundaries(
        face_coords, 3.999999 / 3, img_shape
    )
    assert avatar_square == (1, 6, 39, 39)

    avatar_square = _calculate_crop_square_boundaries(face_coords, 4 / 3, img_shape)
    assert avatar_square == (0, 5, 40, 40)

    # The avatar square is limited by the image boundary for max_expansion_ratio >= 2.
    avatar_square = _calculate_crop_square_boundaries(face_coords, 2, img_shape)
    assert avatar_square == (0, 5, 40, 40)

    avatar_square = _calculate_crop_square_boundaries(face_coords, 2.1, img_shape)
    assert avatar_square == (0, 5, 40, 40)

    avatar_square = _calculate_crop_square_boundaries(face_coords, 3, img_shape)
    assert avatar_square == (0, 5, 40, 40)

    # Odd sizes, to check off by 1 error.
    img_shape = (100, 100)
    face_coords = (10, 10, 21, 31)

    # The avatar square is limited by the image boundary for max_expansion_ratio >= 2.
    avatar_square = _calculate_crop_square_boundaries(face_coords, 2, img_shape)
    assert avatar_square == (0, 5, 40, 40)

    avatar_square = _calculate_crop_square_boundaries(face_coords, 2.1, img_shape)
    assert avatar_square == (0, 5, 40, 40)

    avatar_square = _calculate_crop_square_boundaries(face_coords, 3, img_shape)
    assert avatar_square == (0, 5, 40, 40)

    img_shape = (100, 100)
    # Now limit by the left boundary of the image.
    face_coords = (10, 10, 30, 20)

    # In certain bounary, expansion ration in [3.9, 4/3)
    avatar_square = _calculate_crop_square_boundaries(face_coords, 3.9 / 3, img_shape)
    # _draw_setup(img_shape, face_coords, avatar_square)
    assert avatar_square == (6, 1, 39, 39)
    avatar_square = _calculate_crop_square_boundaries(face_coords, 3.99 / 3, img_shape)
    assert avatar_square == (6, 1, 39, 39)
    avatar_square = _calculate_crop_square_boundaries(
        face_coords, 3.999999 / 3, img_shape
    )
    assert avatar_square == (6, 1, 39, 39)

    avatar_square = _calculate_crop_square_boundaries(face_coords, 4 / 3, img_shape)
    assert avatar_square == (5, 0, 40, 40)

    # The avatar square is limited by the image boundary for max_expansion_ratio >= 2.
    avatar_square = _calculate_crop_square_boundaries(face_coords, 2, img_shape)
    assert avatar_square == (5, 0, 40, 40)

    avatar_square = _calculate_crop_square_boundaries(face_coords, 2.1, img_shape)
    assert avatar_square == (5, 0, 40, 40)

    avatar_square = _calculate_crop_square_boundaries(face_coords, 3, img_shape)
    assert avatar_square == (5, 0, 40, 40)

    # Odd sizes, to check off by 1 error.
    img_shape = (100, 100)
    face_coords = (10, 10, 31, 21)

    # The avatar square is limited by the image boundary for max_expansion_ratio >= 2.
    avatar_square = _calculate_crop_square_boundaries(face_coords, 2, img_shape)
    assert avatar_square == (5, 0, 40, 40)

    avatar_square = _calculate_crop_square_boundaries(face_coords, 2.1, img_shape)
    assert avatar_square == (5, 0, 40, 40)

    avatar_square = _calculate_crop_square_boundaries(face_coords, 3, img_shape)
    assert avatar_square == (5, 0, 40, 40)


@pytest.fixture()
def tmp_dir():
    """Set up temporary directory for test files."""
    tmp_dir = tempfile.TemporaryDirectory()
    yield tmp_dir.name
    tmp_dir.cleanup()


def test_crop_square_face_handle_all_image_formats(tmp_dir):
    img_path = "tests/files/test.jpg"
    img_data = open(img_path, "rb").read()
    crop_avatar_result = crop_avatar(img_data)
    cropped_img = crop_avatar_result.image
    cropped_img.save(os.path.join(tmp_dir, "avatar_test_image.jpg"))
    assert cropped_img.size == (214, 214)
    assert crop_avatar_result.size == ImageSize(width=214, height=214)

    img_path = "tests/files/test.png"
    img_data = open(img_path, "rb").read()
    crop_avatar_result = crop_avatar(img_data)
    cropped_img = crop_avatar_result.image
    cropped_img.save(os.path.join(tmp_dir, "avatar_test_image.png"))
    assert cropped_img.size == (214, 214)
    assert crop_avatar_result.size == ImageSize(width=214, height=214)

    img_path = "tests/files/test.webp"
    img_data = open(img_path, "rb").read()
    crop_avatar_result = crop_avatar(img_data)
    cropped_img = crop_avatar_result.image
    cropped_img.save(os.path.join(tmp_dir, "avatar_test_image.webp"))
    assert cropped_img.size == (214, 214)
    assert crop_avatar_result.size == ImageSize(width=214, height=214)

    img_path = "tests/files/2-faces.png"
    img_data = open(img_path, "rb").read()
    crop_avatar_result = crop_avatar(img_data)
    cropped_img = crop_avatar_result.image
    assert cropped_img.size == (288, 288)
    assert crop_avatar_result.size == ImageSize(width=288, height=288)
    golden_img = Image.open("tests/files/avatar-2-faces.png")
    diff = ImageChops.difference(cropped_img, golden_img)
    assert diff.getbbox() is None
