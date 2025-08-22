import argparse
import os

from math import floor
from typing import Tuple

import cv2
from PIL import Image

# At module level, outside any function
_FACE_CASCADE = None
FACE_EXPANSION_RATIO = 2.0  # How many times larger than the face to make the crop
FACE_DETECTION_SCALE_FACTOR = (
    1.1  # Scale factor for face detection (smaller = more accurate but slower)
)
FACE_DETECTION_MIN_NEIGHBORS = (
    4  # Minimum overlapping detections required to confirm a face
)


"""
Face coordinates, are represented as the top-left corner of the rectangle, and the width and height of the rectangle:
(x, y)  ┌─────────────┐
        │             │
        │     FACE    │ h
        │             │
        └─────────────┘
               w
"""


def _get_face_cascade():
    global _FACE_CASCADE
    if _FACE_CASCADE is None:
        _FACE_CASCADE = cv2.CascadeClassifier(
            cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        )
    return _FACE_CASCADE


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
    max_square_size_within_img = 2 * min(
        max_to_top, max_to_left, max_to_bottom, max_to_right
    )
    print(f"max_square_size_within_img: {max_square_size_within_img}")
    max_square_size = min(max_square_size, max_square_size_within_img)
    print(f"max_square_size: {max_square_size}")

    x = face_center_x - max_square_size // 2
    y = face_center_y - max_square_size // 2

    return (x, y, max_square_size, max_square_size)


def crop_square_face(
    image_path: str, max_expansion_ratio=FACE_EXPANSION_RATIO
) -> Image.Image:
    # Haar cascade classifier only works with grayscale images.
    img = cv2.imread(image_path)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # Load the Haar Cascade for face detection
    face_cascade = _get_face_cascade()

    # Detect faces
    faces = face_cascade.detectMultiScale(
        gray, FACE_DETECTION_SCALE_FACTOR, FACE_DETECTION_MIN_NEIGHBORS
    )

    if len(faces) == 0:
        x, y, w, h = _calculate_top_square_boundaries(img.shape[1], img.shape[0])
        cropped_face = img[y : y + h, x : x + w]
        return Image.fromarray(cv2.cvtColor(cropped_face, cv2.COLOR_BGR2RGB))

    avatar_square = _calculate_crop_square_boundaries(
        faces[0], max_expansion_ratio, (img.shape[1], img.shape[0])
    )
    x, y, w, h = avatar_square
    # Crop the image to a square
    cropped_face = img[y : y + h, x : x + w]

    return Image.fromarray(cv2.cvtColor(cropped_face, cv2.COLOR_BGR2RGB))


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--image-path", type=str, required=True)
    parser.add_argument(
        "--expansion-ratio",
        type=float,
        default=FACE_EXPANSION_RATIO,
        help=f"Ratio to expand crop beyond face size (default: {FACE_EXPANSION_RATIO})",
    )
    return parser.parse_args()


def main():
    # Example usage:
    args = parse_args()
    original_image = Image.open(args.image_path)
    original_image.show()
    cropped_image = crop_square_face(args.image_path, args.expansion_ratio)
    original_image_file_name = os.path.basename(args.image_path)
    cropped_image_file_name = f"avatar_{original_image_file_name}"
    cropped_image.save(cropped_image_file_name)
    cropped_image.show()
    print("Avatar created successfully!")


if __name__ == "__main__":
    main()
