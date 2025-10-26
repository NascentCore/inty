import random

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
# 左右img_shape和avatar_square，边缘为黑色，用白色填充图像
    from PIL import ImageDraw
#创建指定尺寸的白色图像
    img = Image.new("RGB", img_shape, (255, 255, 255))
    draw = ImageDraw.Draw(img)

    x, y, w, h = face_coords
# 使用浅蓝色填充和黑色视觉视觉
    draw.rectangle(
        (x, y, x + w, y + h),
        outline=(0, 0, 0),
        fill=(173, 216, 230),
        width=1,
    )
# 替换带有黑边的图像边界（完整图像）
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
# 断言引发断言错误
    with pytest.raises(AssertionError):
        _calculate_crop_square_boundaries(face_coords, 0.9, img_shape)
# 在一定的边界内，膨胀率在[3.9, 4/3)
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
# 看一下边界图像的限制 max_expansion_ratio >= 2。
    avatar_square = _calculate_crop_square_boundaries(face_coords, 2, img_shape)
    assert avatar_square == (0, 5, 40, 40)

    avatar_square = _calculate_crop_square_boundaries(face_coords, 2.1, img_shape)
    assert avatar_square == (0, 5, 40, 40)

    avatar_square = _calculate_crop_square_boundaries(face_coords, 3, img_shape)
    assert avatar_square == (0, 5, 40, 40)
#奇数尺寸，检查1个错误。
    img_shape = (100, 100)
    face_coords = (10, 10, 21, 31)
# 看一下边界图像的限制 max_expansion_ratio >= 2。
    avatar_square = _calculate_crop_square_boundaries(face_coords, 2, img_shape)
    assert avatar_square == (0, 5, 40, 40)

    avatar_square = _calculate_crop_square_boundaries(face_coords, 2.1, img_shape)
    assert avatar_square == (0, 5, 40, 40)

    avatar_square = _calculate_crop_square_boundaries(face_coords, 3, img_shape)
    assert avatar_square == (0, 5, 40, 40)

    img_shape = (100, 100)
# 现在由图像边界的边界限制。
    face_coords = (10, 10, 30, 20)
# 在一定的边界内，膨胀率在[3.9, 4/3)
    avatar_square = _calculate_crop_square_boundaries(face_coords, 3.9 / 3, img_shape)
# _draw_setup（img_shape，face_coords，avatar_square）
    assert avatar_square == (6, 1, 39, 39)
    avatar_square = _calculate_crop_square_boundaries(face_coords, 3.99 / 3, img_shape)
    assert avatar_square == (6, 1, 39, 39)
    avatar_square = _calculate_crop_square_boundaries(
        face_coords, 3.999999 / 3, img_shape
    )
    assert avatar_square == (6, 1, 39, 39)

    avatar_square = _calculate_crop_square_boundaries(face_coords, 4 / 3, img_shape)
    assert avatar_square == (5, 0, 40, 40)
# 看一下边界图像的限制 max_expansion_ratio >= 2。
    avatar_square = _calculate_crop_square_boundaries(face_coords, 2, img_shape)
    assert avatar_square == (5, 0, 40, 40)

    avatar_square = _calculate_crop_square_boundaries(face_coords, 2.1, img_shape)
    assert avatar_square == (5, 0, 40, 40)

    avatar_square = _calculate_crop_square_boundaries(face_coords, 3, img_shape)
    assert avatar_square == (5, 0, 40, 40)
#奇数尺寸，检查1个错误。
    img_shape = (100, 100)
    face_coords = (10, 10, 31, 21)
# 看一下边界图像的限制 max_expansion_ratio >= 2。
    avatar_square = _calculate_crop_square_boundaries(face_coords, 2, img_shape)
    assert avatar_square == (5, 0, 40, 40)

    avatar_square = _calculate_crop_square_boundaries(face_coords, 2.1, img_shape)
    assert avatar_square == (5, 0, 40, 40)

    avatar_square = _calculate_crop_square_boundaries(face_coords, 3, img_shape)
    assert avatar_square == (5, 0, 40, 40)


def test_crop_square_face_handle_all_image_formats():
    img_path = "tests/files/test.jpg"
    img_data = open(img_path, "rb").read()
    crop_avatar_result = crop_avatar(img_data)
    cropped_img = crop_avatar_result.image
    cropped_img.save("avatar_test_image.jpg")
    assert cropped_img.size == (214, 214)
    assert crop_avatar_result.size == ImageSize(width=214, height=214)

    img_path = "tests/files/test.png"
    img_data = open(img_path, "rb").read()
    crop_avatar_result = crop_avatar(img_data)
    cropped_img = crop_avatar_result.image
    cropped_img.save("avatar_test_image.png")
    assert cropped_img.size == (214, 214)
    assert crop_avatar_result.size == ImageSize(width=214, height=214)

    img_path = "tests/files/test.webp"
    img_data = open(img_path, "rb").read()
    crop_avatar_result = crop_avatar(img_data)
    cropped_img = crop_avatar_result.image
    cropped_img.save("avatar_test_image.webp")
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
