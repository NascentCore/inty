import argparse
from dataclasses import dataclass
from math import floor
from typing import List, Tuple

import animeface
import cv2
import numpy as np
from loguru import logger
from PIL import Image
from pydantic import BaseModel

from app.utils.image import ImageSize

CROPPED_AVATAR_FILENAME_SUFFIX = "-cropped-avatar"
# 人脸检测器（默认）：haarcascade_frontalface_default。XML
# 人脸检测器（快速Harr）：haarcascade_frontalface_alt2。XML
# 人脸检测器（侧视图）：haarcascade_profileface.XML
# 眼睛检测器（左眼）：haarcascade_lefteye_2splits。XML
# 眼睛检测器（右眼）：haarcascade_righteye_2splits。XML
# 嘴巴检测器：haarcascade_mcs_mouth。XML
# 鼻子：haarcascade_mcs_nose。XML
# 人体检测器：haarcascade_fullbody。XML
# 人脸检测器（快速LBP）：lbpcascade_frontalface。XML
#只睁开眼睛才能被检测到：
# haarcascade_eye。XML
# haarcascade_eye_tree_eyeglasses。xml [仅当被测试者戴眼镜时]
# 人脸检测算法通常通过扫描几何尺寸（尺寸）的图像来工作
# 找到不同大小的托架。scaleFactor确定创建此“比例金字塔”的步长。
# 较小的scaleFactor意味着更详细的扫描，但也意味着更多的计算成本。
FACE_DETECTION_SCALE_FACTOR = (
    1.1  # Scale factor for face detection (smaller = more accurate but slower)
)
# 这用于过滤掉统计报告。
# 使用滑动窗口的重复测量的图像。
#这个process可能会导致许多错误报告，
# 一张脸可能被几个重叠的单一识别。
FACE_DETECTION_MIN_NEIGHBORS = (
    6  # Minimum overlapping detections required to confirm a face
)
# https://forum.opencv.org/t/face-detection-for-static-image-find-top-of-head-and-chin/3009/9
#查看完整列表：
# https://github.com/opencv/opencv/tree/master/data/haarcascades
# 注意：这通常无法检测到任何皮肤。
# 互联网声明 (https://stackoverflow.com/q/59466015/31283770)
# 它检测到左脸，但未按预期工作，请参见左脸。PNG。
#媒体管道等
HAAR_CASCADE_PROFILE_FACE = "haarcascade_profileface.xml"
HAAR_CASCADE_FRONTAL_FACE_DEFAULT = "haarcascade_frontalface_default.xml"
ANIME_FACE = "lbpcascade_animeface.xml"
CUSTOM_CASCADE_DIR = "app/utils/cascades/"

_CASCADE_CACHE = {
    HAAR_CASCADE_PROFILE_FACE: cv2.CascadeClassifier(
        cv2.data.haarcascades + HAAR_CASCADE_PROFILE_FACE
    ),
    HAAR_CASCADE_FRONTAL_FACE_DEFAULT: cv2.CascadeClassifier(
        cv2.data.haarcascades + HAAR_CASCADE_FRONTAL_FACE_DEFAULT
    ),
    ANIME_FACE: cv2.CascadeClassifier(CUSTOM_CASCADE_DIR + ANIME_FACE),
}


"""
Face coordinates, are represented as the top-left corner of the rectangle, and the width and height of the rectangle:
(x, y)  ┌─────────────┐
        │             │
        │     FACE    │ h
        │             │
        └─────────────┘
               w
"""


class AvatarCroppingConfig(BaseModel):
    """
    Each face detection requires different expansion ratio.
    """

    max_expansion_ratio: float
    face_detection_profile: str


PROFILE_FACE = AvatarCroppingConfig(
    max_expansion_ratio=1.0,
# 这对于非正面更有效。
#45度边小....jpg
    face_detection_profile=HAAR_CASCADE_PROFILE_FACE,
)
FRONTAL_FACE_DEFAULT = AvatarCroppingConfig(
    max_expansion_ratio=1.8,
# 对于正面，这更有效。
#由于profile 脸会尝试将眼睛居中。
#类似类似，请参阅半身额。....jpg。
    face_detection_profile=HAAR_CASCADE_FRONTAL_FACE_DEFAULT,
)

ANIME_FACE = AvatarCroppingConfig(
# 动漫通常会越来越多的头部和其他引人注目的特征被包围。
#因此我们需要进一步扩大预算。
    max_expansion_ratio=2.0,
    face_detection_profile=ANIME_FACE,
)


def _calculate_top_square_boundaries(width, height) -> Tuple[int, int, int, int]:
    """
    Calculate the boundaries of a square that is centered horizontally and limited by the smaller dimension of the image.
    Return (x, y, w, h) of the square.
    """
    square_size = min(width, height)
    left = (width - square_size) // 2
    top = 0
    return (left, top, square_size, square_size)


def _calculate_crop_square_boundaries(
    face_coords: Tuple[int, int, int, int],
    max_expansion_ratio: float,
    img_shape: Tuple[int, int],
) -> Tuple[int, int, int, int]:
    """
    img_shape: (width, height)
    Face_coords is within the boundaries of the image_shape.

    1. Find the center of the rectangle identified by face_coords, call it face center.
    2. Find the size of a square that:
        a) center on the face center
        b) is square
        c) is within the image boundaries
        d) is no larger than max_expansion_ratio * max(face_coords.width, face_coords.height)

    Return the coordinates (x, y, w, h) of the square.
    """
    assert (
        max_expansion_ratio >= 1
    ), "It's not possible to crop a square smaller than the face."

    print(f"image shape: {img_shape}")
    x, y, w, h = face_coords
    face_center_x = x + w // 2
    face_center_y = y + h // 2

    print(f"face_center_x: {face_center_x}, face_center_y: {face_center_y}")

    max_square_size = floor(max(w, h) * max_expansion_ratio)
    print(f"max_square_size: {max_square_size}")

    max_to_top = face_center_y
    max_to_left = face_center_x
    max_to_bottom = img_shape[1] - face_center_y
    max_to_right = img_shape[0] - face_center_x
    print(
        f"max_to_top: {max_to_top}, max_to_left: {max_to_left}, max_to_bottom: {max_to_bottom}, max_to_right: {max_to_right}"
    )
    max_square_size_within_img = 2 * min(
        max_to_top, max_to_left, max_to_bottom, max_to_right
    )
    print(f"max_square_size_within_img: {max_square_size_within_img}")
    max_square_size = min(max_square_size, max_square_size_within_img)
    print(f"max_square_size: {max_square_size}")

    x = face_center_x - max_square_size // 2
    y = face_center_y - max_square_size // 2

    return (x, y, max_square_size, max_square_size)


def _detect_faces(
    gray: np.ndarray, avatar_cropping_config: AvatarCroppingConfig
) -> List[Tuple[int, int, int, int]]:
    face_cascade = _CASCADE_CACHE[avatar_cropping_config.face_detection_profile]
    return face_cascade.detectMultiScale(
        gray, FACE_DETECTION_SCALE_FACTOR, FACE_DETECTION_MIN_NEIGHBORS
    )


@dataclass
class CropAvatarResult:
    """
    Cropped avatar image and its size. Used as a container for return value for easy extension.
    """
# 不使用Basemodel，因为Image。无法进行图像序列化。
    image: Image.Image
    size: ImageSize
# TODO：我们尝试将profile人脸和正面人脸检测结合起来，
#但profile人脸始终检测到返回空列表。
# 可以尝试很多想法：
＃1。先检测眼睛，再计算人脸方向，检测profile人脸。
#2.媒体管道：https://colab.research.google.com/github/googlesamples/mediapipe/blob/main/examples/object_detection/python/object_detector.ipynb
#
# 现有的 approach 速度很快，但远非完美。
def crop_avatar(img_data: bytes) -> CropAvatarResult:
# Haar 级联分类器仅适用于灰度图像。
    img = cv2.imdecode(np.frombuffer(img_data, np.uint8), cv2.IMREAD_COLOR)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    logger.debug(f"Detecting faces with py animeface ...")
    pil_img = Image.fromarray(img)
    avatar_cropping_config = ANIME_FACE
    faces = animeface.detect(pil_img)
    faces = [
# 需要进行数据格式转换。
        (face.face.pos.x, face.face.pos.y, face.face.pos.width, face.face.pos.height)
        for face in faces
    ]

    if len(faces) == 0:
        logger.debug("Detecting faces with opencv anime face cascade ...")
        avatar_cropping_config = ANIME_FACE
        faces = _detect_faces(gray, avatar_cropping_config)

    if len(faces) == 0:
        logger.debug("Detecting faces with frontal face default (realistic style) ...")
        avatar_cropping_config = FRONTAL_FACE_DEFAULT
        faces = _detect_faces(gray, avatar_cropping_config)
########################################################################################
# 在此处添加新的人脸检测通道。
########################################################################################

    if len(faces) == 0:
        logger.warning("No faces detected, using top square boundaries")
        x, y, w, h = _calculate_top_square_boundaries(img.shape[1], img.shape[0])
        cropped_face = img[y : y + h, x : x + w]
        return CropAvatarResult(
            image=Image.fromarray(cv2.cvtColor(cropped_face, cv2.COLOR_BGR2RGB)),
            size=ImageSize(width=w, height=h),
        )

    largest_face = max(faces, key=lambda x: x[2] * x[3])
    avatar_square = _calculate_crop_square_boundaries(
        largest_face,
        avatar_cropping_config.max_expansion_ratio,
        (img.shape[1], img.shape[0]),
    )
#Image 上日益严重的以供调试。
# x, y, w, h = 最大面
# 简历2。形状(img, (x, y), (x + w, y + h), (0, 0, 255), 2)

    x, y, w, h = avatar_square
#Image将作为礼物
    cropped_face = img[y : y + h, x : x + w]
# OpenCV使用BGR颜色顺序（蓝、绿、红），需要转换为RGB。
    return CropAvatarResult(
        image=Image.fromarray(cv2.cvtColor(cropped_face, cv2.COLOR_BGR2RGB)),
        size=ImageSize(width=w, height=h),
    )


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--image-path", type=str, required=True)
    return parser.parse_args()


def main():
#最后示例：
    args = parse_args()
    original_image = Image.open(args.image_path)
    original_image.show()
    img_data = open(args.image_path, "rb").read()

    crop_avatar_result = crop_avatar(img_data)
    cropped_image = crop_avatar_result.image
    cropped_image.show()


if __name__ == "__main__":
    main()
