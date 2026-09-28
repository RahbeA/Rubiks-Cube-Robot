import cv2
import numpy as np

from scanner.colors import ColorClassifier
from scanner.detect import sample_face


COLORS = {
    "white": (236, 236, 236),
    "yellow": (40, 210, 245),
    "red": (45, 40, 190),
    "orange": (30, 110, 235),
    "blue": (190, 75, 35),
    "green": (70, 175, 45),
}
NAMES = ["white", "yellow", "red", "orange", "blue", "green", "white", "red", "green"]


def _gapped_face(origin=(30, 40), canvas=(420, 460)):
    image = np.full((canvas[1], canvas[0], 3), 18, np.uint8)
    y0, x0 = origin
    for index, name in enumerate(NAMES):
        row, col = divmod(index, 3)
        y = y0 + row * 78
        x = x0 + col * 78
        image[y : y + 62, x : x + 62] = COLORS[name]
    return image


def _room_with_face(names, angle=0, origin=(90, 380)):
    image = np.full((720, 1280, 3), (90, 80, 70), np.uint8)
    for y in range(image.shape[0]):
        image[y, :, 0] = np.clip(70 + y // 12, 0, 255)
    size, gap = 100, 22
    pitch = size + gap
    span = pitch * 3 - gap
    patch = np.full((span + 56, span + 56, 3), (25, 25, 25), np.uint8)
    for index, name in enumerate(names):
        row, col = divmod(index, 3)
        y = 28 + row * pitch
        x = 28 + col * pitch
        patch[y : y + size, x : x + size] = COLORS[name]
    if angle:
        height, width = patch.shape[:2]
        matrix = cv2.getRotationMatrix2D((width / 2, height / 2), angle, 1)
        cosine, sine = abs(matrix[0, 0]), abs(matrix[0, 1])
        bound_w = int(height * sine + width * cosine)
        bound_h = int(height * cosine + width * sine)
        matrix[0, 2] += (bound_w / 2) - width / 2
        matrix[1, 2] += (bound_h / 2) - height / 2
        patch = cv2.warpAffine(patch, matrix, (bound_w, bound_h), borderValue=(80, 75, 70))
    y0, x0 = origin
    image[y0 : y0 + patch.shape[0], x0 : x0 + patch.shape[1]] = patch
    noise = np.random.default_rng(1).integers(-8, 8, image.shape, dtype=np.int16)
    return np.clip(image.astype(np.int16) + noise, 0, 255).astype(np.uint8)


def test_grid_locks_onto_offset_face():
    result = sample_face(_gapped_face(), ColorClassifier())
    assert result["locked"] is True
    assert [sticker["color"] for sticker in result["stickers"]] == NAMES
    assert len(result["quad"]) == 4


def test_face_locks_on_a_cube_in_a_room():
    image = _room_with_face(NAMES)
    ok, encoded = cv2.imencode(".jpg", image, [int(cv2.IMWRITE_JPEG_QUALITY), 72])
    assert ok
    decoded = cv2.imdecode(encoded, cv2.IMREAD_COLOR)
    result = sample_face(decoded, ColorClassifier())
    assert result["locked"] is True
    assert [sticker["color"] for sticker in result["stickers"]] == NAMES
    assert len(result["quad"]) == 4


def test_tilted_face_stays_in_reading_order():
    result = sample_face(_room_with_face(NAMES, angle=18), ColorClassifier())
    assert result["locked"] is True
    assert [sticker["color"] for sticker in result["stickers"]] == NAMES


def test_plain_wall_does_not_lock():
    image = np.full((480, 640, 3), (150, 140, 130), np.uint8)
    result = sample_face(image, ColorClassifier())
    assert result["locked"] is False
    assert result["stickers"] == []


def test_manual_guide_reads_a_solid_face():
    image = np.zeros((300, 300, 3), np.uint8)
    image[:] = COLORS["green"]
    result = sample_face(image, ColorClassifier(), manual=True)
    assert result["locked"] is True
    assert result["method"] == "guide"
    assert all(sticker["color"] == "green" for sticker in result["stickers"])
