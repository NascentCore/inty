import argparse
import os

from math import floor
from typing import Tuple

import cv2
from PIL import Image
from loguru import logger
import numpy as np
from pydantic import BaseModel


# Face detector (default): haarcascade_frontalface_default.xml
# Face detector (fast Harr): haarcascade_frontalface_alt2.xml
# Face detector (side view): haarcascade_profileface.xml
# Eye detector (left eye): haarcascade_lefteye_2splits.xml
# Eye detector (right eye): haarcascade_righteye_2splits.xml
# Mouth detector: haarcascade_mcs_mouth.xml
# Nose detector: haarcascade_mcs_nose.xml
# Body detector: haarcascade_fullbody.xml
# Face detector (fast LBP): lbpcascade_frontalface.xml
# Only open eyes can be detected:
# haarcascade_eye.xml
# haarcascade_eye_tree_eyeglasses.xml [Only when the person being tested is wearing glasses]

# Face detection algorithms often work by scanning an image at multiple scales (sizes)
# to find faces of varying sizes. scaleFactor determines the step size for creating this "scale pyramid".
# A smaller scaleFactor means more detailed scanning, but also more computational cost.
FACE_DETECTION_SCALE_FACTOR = (
    1.1  # Scale factor for face detection (smaller = more accurate but slower)
)

# This is used to filter out false-positive rectangles.
# An image at multiple scales using a sliding window.
# This process can result in many false-positive rectangles,
# with a single face potentially being identified by several overlapping rectangles.
FACE_DETECTION_MIN_NEIGHBORS = (
    6  # Minimum overlapping detections required to confirm a face
)

# https://forum.opencv.org/t/face-detection-for-static-image-find-top-of-head-and-chin/3009/9
# See full list at:
# https://github.com/opencv/opencv/tree/master/data/haarcascades
# NOTE: This usally cannot detect any faces.
# Internet claims (https://stackoverflow.com/q/59466015/31283770)
# it detecst left facing faces, but not working as expected, see left-facing.png.
# Media pipe etc.
HAAR_CASCADE_PROFILE_FACE = "haarcascade_profileface.xml"
HAAR_CASCADE_FRONTAL_FACE_DEFAULT = "haarcascade_frontalface_default.xml"

_CASCADE_CACHE = {
    HAAR_CASCADE_PROFILE_FACE: cv2.CascadeClassifier(
        cv2.data.haarcascades + HAAR_CASCADE_PROFILE_FACE
    ),
    HAAR_CASCADE_FRONTAL_FACE_DEFAULT: cv2.CascadeClassifier(
        cv2.data.haarcascades + HAAR_CASCADE_FRONTAL_FACE_DEFAULT
    ),
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
    # This is more effective for non-frontal faces.
    # 45-degree-side-small.jpg
    face_detection_profile=HAAR_CASCADE_PROFILE_FACE,
)
FRONTAL_FACE_DEFAULT = AvatarCroppingConfig(
    max_expansion_ratio=1.8,
    # For a frontal face, this is more effective.
    # As profile face will try to center eyes in the middle.
    # See half-body-frontal.jpg for such an example.
    face_detection_profile=HAAR_CASCADE_FRONTAL_FACE_DEFAULT,
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


# TODO: We tried to combine profile face and frontal face detection,
# but profile face detection always returns empty list.
# Many ideas can be tried:
# 1. Detect eyes first, then calculate face direction, to detect profile face.
# 2. Media pipe: https://colab.research.google.com/github/googlesamples/mediapipe/blob/main/examples/object_detection/python/object_detector.ipynb
#
# The existing approach is fast, but far from perfect.
def crop_avatar(img_data: bytes) -> Image.Image:
    # Haar cascade classifier only works with grayscale images.
    img = cv2.imdecode(np.frombuffer(img_data, np.uint8), cv2.IMREAD_COLOR)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # Load the Haar Cascade for face detection
    face_cascade = _CASCADE_CACHE[FRONTAL_FACE_DEFAULT.face_detection_profile]

    # Detect faces
    faces = face_cascade.detectMultiScale(
        gray, FACE_DETECTION_SCALE_FACTOR, FACE_DETECTION_MIN_NEIGHBORS
    )

    if len(faces) == 0:
        logger.warning("No faces detected, using top square boundaries")
        x, y, w, h = _calculate_top_square_boundaries(img.shape[1], img.shape[0])
        cropped_face = img[y : y + h, x : x + w]
        return Image.fromarray(cv2.cvtColor(cropped_face, cv2.COLOR_BGR2RGB))

    largest_face = max(faces, key=lambda x: x[2] * x[3])
    avatar_square = _calculate_crop_square_boundaries(
        largest_face,
        FRONTAL_FACE_DEFAULT.max_expansion_ratio,
        (img.shape[1], img.shape[0]),
    )
    x, y, w, h = avatar_square
    # Crop the image to a square
    cropped_face = img[y : y + h, x : x + w]

    return Image.fromarray(cv2.cvtColor(cropped_face, cv2.COLOR_BGR2RGB))


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--image-path", type=str, required=True)
    return parser.parse_args()


def main():
    # Example usage:
    args = parse_args()
    original_image = Image.open(args.image_path)
    original_image.show()
    img_data = open(args.image_path, "rb").read()

    cropped_image = crop_avatar(img_data)
    cropped_image.show()


if __name__ == "__main__":
    main()
