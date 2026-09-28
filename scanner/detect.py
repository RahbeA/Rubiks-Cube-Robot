"""Read one cube face from the center of the camera.

The cube is held in a fixed guide, so nothing outside that square is allowed
to become a detection. Guided mode samples a fixed 3×3 inside the guide.
Automatic mode may look for one outer face quadrilateral, but only inside
the same guide, and it never keeps a previous quad after the face is lost.
"""

from __future__ import annotations

import base64

import cv2
import numpy as np

from scanner.colors import COLOR_TO_FACE, ColorClassifier, bgr_to_lab

# Fraction of the shorter frame side used for the centered guide.
ROI_SCALE = 0.62
WARP_SIZE = 300
# Inner fraction of each grid cell. Keeps the sample off the plastic borders.
SAMPLE_FRACTION = 0.42
# Automatic face must cover this much of the guide, and not the whole guide edge.
MIN_FACE_SIDE = 0.42
MAX_FACE_SIDE = 0.96
SQUARENESS_MIN = 0.75
# How far the face center may sit from the guide center, as a fraction of the guide side.
MAX_CENTER_OFFSET = 0.16
STABILITY_FRAMES = 5
# Corner motion, in guide pixels, that still counts as the same face.
CORNER_TOLERANCE = 14.0
AREA_RATIO_TOLERANCE = 0.18
MAX_COLOR_CHANGES = 2

STATUS_ALIGN = "Align cube inside guide"
STATUS_HOLD = "Cube detected — hold steady"
STATUS_STABLE = "Cube stable — press Space to capture"


def get_cube_roi(frame: np.ndarray) -> tuple[np.ndarray, tuple[int, int, int, int]]:
    """Crop the centered square. Everything outside this crop is ignored."""
    height, width = frame.shape[:2]
    side = max(12, int(round(min(height, width) * ROI_SCALE)))
    side = min(side, height, width)
    x = (width - side) // 2
    y = (height - side) // 2
    return frame[y : y + side, x : x + side].copy(), (x, y, side, side)


def order_quad_points(points: np.ndarray) -> np.ndarray:
    """Order corners as top-left, top-right, bottom-right, bottom-left."""
    pts = np.asarray(points, dtype=np.float32).reshape(4, 2)
    sums = pts.sum(axis=1)
    diff = pts[:, 0] - pts[:, 1]
    ordered = np.zeros((4, 2), dtype=np.float32)
    ordered[0] = pts[np.argmin(sums)]
    ordered[2] = pts[np.argmax(sums)]
    ordered[1] = pts[np.argmax(diff)]
    ordered[3] = pts[np.argmin(diff)]
    return ordered


def _quad_area(quad: np.ndarray) -> float:
    return float(cv2.contourArea(np.asarray(quad, dtype=np.float32).reshape(-1, 1, 2)))


def _corner_angles_ok(quad: np.ndarray) -> bool:
    pts = order_quad_points(quad)
    for index in range(4):
        previous = pts[(index - 1) % 4] - pts[index]
        nxt = pts[(index + 1) % 4] - pts[index]
        denom = float(np.linalg.norm(previous) * np.linalg.norm(nxt))
        if denom < 1e-3:
            return False
        cosine = float(np.dot(previous, nxt) / denom)
        angle = float(np.degrees(np.arccos(np.clip(cosine, -1.0, 1.0))))
        if angle < 55.0 or angle > 125.0:
            return False
    return True


def _candidate_from_contour(contour: np.ndarray) -> np.ndarray | None:
    peri = cv2.arcLength(contour, True)
    if peri < 40:
        return None
    approx = cv2.approxPolyDP(contour, 0.04 * peri, True)
    if len(approx) == 4 and cv2.isContourConvex(approx):
        return order_quad_points(approx.reshape(4, 2))
    (center_x, center_y), (rect_w, rect_h), angle = cv2.minAreaRect(contour)
    if rect_w < 8 or rect_h < 8:
        return None
    if min(rect_w, rect_h) / max(rect_w, rect_h) < SQUARENESS_MIN:
        return None
    return order_quad_points(cv2.boxPoints(((center_x, center_y), (rect_w, rect_h), angle)))


def _score_quad(quad: np.ndarray, roi_side: int, previous: np.ndarray | None) -> float | None:
    """Score a face candidate. Area alone is not enough to win."""
    pts = order_quad_points(quad)
    sides = [float(np.linalg.norm(pts[(i + 1) % 4] - pts[i])) for i in range(4)]
    if min(sides) < 1:
        return None
    squareness = min(sides) / max(sides)
    if squareness < SQUARENESS_MIN or not _corner_angles_ok(pts):
        return None
    side = float(np.mean(sides))
    if side < roi_side * MIN_FACE_SIDE or side > roi_side * MAX_FACE_SIDE:
        return None
    center = pts.mean(axis=0)
    offset = float(np.linalg.norm(center - np.array([roi_side / 2, roi_side / 2])))
    if offset > roi_side * MAX_CENTER_OFFSET:
        return None
    expected = roi_side * 0.78
    size_score = 1.0 - min(1.0, abs(side - expected) / expected)
    center_score = 1.0 - min(1.0, offset / (roi_side * MAX_CENTER_OFFSET))
    score = 0.45 * squareness + 0.30 * size_score + 0.25 * center_score
    if previous is not None:
        shift = float(np.mean(np.linalg.norm(pts - order_quad_points(previous), axis=1)))
        score += 0.2 * max(0.0, 1.0 - shift / max(CORNER_TOLERANCE * 2, 1.0))
    return score


def find_cube_face(roi: np.ndarray, previous: np.ndarray | None = None) -> dict:
    """Find one outer face quadrilateral inside the guide, or nothing."""
    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(blur, 40, 130)
    edges = cv2.dilate(edges, np.ones((3, 3), np.uint8))
    contours, _ = cv2.findContours(edges, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    roi_side = roi.shape[0]
    accepted = []
    rejected = []
    for contour in contours:
        area = cv2.contourArea(contour)
        if area < (roi_side * roi_side) * 0.08:
            continue
        quad = _candidate_from_contour(contour)
        if quad is None:
            continue
        score = _score_quad(quad, roi_side, previous)
        if score is None:
            rejected.append(quad)
            continue
        accepted.append((score, quad))
    if not accepted:
        return {"quad": None, "score": None, "rejected": rejected}
    score, quad = max(accepted, key=lambda item: item[0])
    return {"quad": quad, "score": round(float(score), 3), "rejected": rejected}


def warp_cube_face(roi: np.ndarray, points: np.ndarray) -> np.ndarray:
    """Warp the face to a fixed square so sticker rows stay in reading order."""
    source = order_quad_points(points)
    destination = np.array(
        [[0, 0], [WARP_SIZE - 1, 0], [WARP_SIZE - 1, WARP_SIZE - 1], [0, WARP_SIZE - 1]],
        dtype=np.float32,
    )
    transform = cv2.getPerspectiveTransform(source, destination)
    return cv2.warpPerspective(roi, transform, (WARP_SIZE, WARP_SIZE))


def get_sticker_regions(size: int = WARP_SIZE, fraction: float = SAMPLE_FRACTION) -> list[tuple[float, float, float, float]]:
    """Small squares around the nine cell centers, inset from the grid lines."""
    cell = size / 3.0
    sample = cell * fraction
    regions = []
    for row in range(3):
        for col in range(3):
            center_x = (col + 0.5) * cell
            center_y = (row + 0.5) * cell
            regions.append((center_x - sample / 2, center_y - sample / 2, sample, sample))
    return regions


def sample_sticker_colors(warped: np.ndarray) -> list[np.ndarray]:
    """Median BGR of each center sample. Row-major, indexes 0 through 8."""
    samples = []
    height, width = warped.shape[:2]
    for x, y, sample_w, sample_h in get_sticker_regions(width):
        x0 = int(np.clip(round(x), 0, width - 1))
        y0 = int(np.clip(round(y), 0, height - 1))
        x1 = int(np.clip(round(x + sample_w), x0 + 1, width))
        y1 = int(np.clip(round(y + sample_h), y0 + 1, height))
        patch = warped[y0:y1, x0:x1]
        if patch.size == 0:
            samples.append(np.zeros(3, dtype=np.float64))
        else:
            samples.append(np.median(patch.reshape(-1, 3), axis=0))
    return samples


def _as_sticker(bgr: np.ndarray, classifier: ColorClassifier) -> dict:
    lab = bgr_to_lab(tuple(int(v) for v in bgr))
    name, delta = classifier.classify_lab(lab)
    return {
        "color": name,
        "face": COLOR_TO_FACE[name],
        "delta_e": round(float(delta), 2),
        "lab": [round(float(v), 2) for v in lab],
        "bgr": [int(round(float(v))) for v in bgr],
    }


class DetectionState:
    """Short history so a passing hand cannot replace a steady face."""

    def __init__(self) -> None:
        self.count = 0
        self.previous_quad: np.ndarray | None = None
        self.previous_colors: list[str] | None = None
        self.previous_area: float | None = None

    def reset(self) -> None:
        self.count = 0
        self.previous_quad = None
        self.previous_colors = None
        self.previous_area = None

    def update(self, quad: np.ndarray | None, colors: list[str]) -> tuple[int, bool]:
        if quad is None or len(colors) != 9:
            self.reset()
            return 0, False
        current = order_quad_points(quad)
        area = _quad_area(current)
        if self.previous_quad is None or self.previous_colors is None or not self.previous_area:
            self.count = 1
        else:
            shift = float(np.max(np.linalg.norm(current - self.previous_quad, axis=1)))
            area_ratio = area / self.previous_area
            changes = sum(left != right for left, right in zip(colors, self.previous_colors))
            steady = (
                shift <= CORNER_TOLERANCE
                and abs(area_ratio - 1.0) <= AREA_RATIO_TOLERANCE
                and changes <= MAX_COLOR_CHANGES
            )
            self.count = self.count + 1 if steady else 1
        self.previous_quad = current
        self.previous_colors = list(colors)
        self.previous_area = area
        return self.count, self.count >= STABILITY_FRAMES


def update_detection_stability(state: DetectionState, quad: np.ndarray | None, colors: list[str]) -> tuple[int, bool]:
    return state.update(quad, colors)


def _guide_quad(side: int) -> np.ndarray:
    last = float(side - 1)
    return np.array([[0, 0], [last, 0], [last, last], [0, last]], dtype=np.float32)


def _roi_is_dark(roi: np.ndarray) -> bool:
    return float(roi.mean()) < 28.0


def _normalize_points(points: np.ndarray, width: int, height: int) -> list[list[float]]:
    return [[round(float(x) / width, 4), round(float(y) / height, 4)] for x, y in points]


def _map_regions_to_frame(quad: np.ndarray, origin: tuple[int, int], frame_shape: tuple[int, ...]) -> list[list[list[float]]]:
    source = order_quad_points(quad)
    destination = np.array(
        [[0, 0], [WARP_SIZE - 1, 0], [WARP_SIZE - 1, WARP_SIZE - 1], [0, WARP_SIZE - 1]],
        dtype=np.float32,
    )
    inverse = cv2.getPerspectiveTransform(destination, source)
    height, width = frame_shape[:2]
    ox, oy = origin
    mapped = []
    for x, y, sample_w, sample_h in get_sticker_regions():
        corners = np.array(
            [[x, y], [x + sample_w, y], [x + sample_w, y + sample_h], [x, y + sample_h]],
            dtype=np.float32,
        ).reshape(-1, 1, 2)
        back = cv2.perspectiveTransform(corners, inverse).reshape(4, 2)
        back[:, 0] += ox
        back[:, 1] += oy
        mapped.append(_normalize_points(back, width, height))
    return mapped


def _quad_to_frame(quad: np.ndarray, origin: tuple[int, int], frame_shape: tuple[int, ...]) -> list[list[float]]:
    ox, oy = origin
    shifted = order_quad_points(quad).copy()
    shifted[:, 0] += ox
    shifted[:, 1] += oy
    height, width = frame_shape[:2]
    return _normalize_points(shifted, width, height)


def draw_debug_overlay(
    frame: np.ndarray,
    roi_rect: tuple[int, int, int, int],
    selected: np.ndarray | None,
    rejected: list[np.ndarray],
    origin: tuple[int, int],
) -> np.ndarray:
    canvas = frame.copy()
    x, y, side, _side = roi_rect
    cv2.rectangle(canvas, (x, y), (x + side, y + side), (230, 230, 230), 2)
    ox, oy = origin
    for quad in rejected:
        shifted = order_quad_points(quad).copy()
        shifted[:, 0] += ox
        shifted[:, 1] += oy
        cv2.polylines(canvas, [shifted.astype(np.int32)], True, (40, 40, 210), 1)
    if selected is not None:
        shifted = order_quad_points(selected).copy()
        shifted[:, 0] += ox
        shifted[:, 1] += oy
        cv2.polylines(canvas, [shifted.astype(np.int32)], True, (80, 210, 90), 2)
    return canvas


def _encode_jpeg(image: np.ndarray) -> str:
    marked = image.copy()
    for x, y, sample_w, sample_h in get_sticker_regions(marked.shape[1]):
        cv2.rectangle(
            marked,
            (int(x), int(y)),
            (int(x + sample_w), int(y + sample_h)),
            (255, 255, 255),
            1,
        )
    ok, encoded = cv2.imencode(".jpg", marked, [int(cv2.IMWRITE_JPEG_QUALITY), 70])
    if not ok:
        return ""
    return "data:image/jpeg;base64," + base64.b64encode(encoded.tobytes()).decode("ascii")


def _empty(roi_norm: dict, status: str = STATUS_ALIGN) -> dict:
    return {
        "stickers": [],
        "locked": False,
        "stable": False,
        "stability": 0,
        "method": "searching",
        "status": status,
        "quad": [],
        "roi": roi_norm,
        "samples": [],
        "rejected": [],
        "score": None,
        "warped": "",
    }


def read_cube(
    frame: np.ndarray,
    classifier: ColorClassifier,
    mode: str = "guide",
    state: DetectionState | None = None,
    debug: bool = False,
) -> dict:
    """Guide by default. Automatic outline search stays inside the guide."""
    if frame is None or frame.size == 0:
        raise ValueError("empty image")
    if state is None:
        state = DetectionState()
    mode = "auto" if mode == "auto" else "guide"

    roi, (ox, oy, side, _side) = get_cube_roi(frame)
    height, width = frame.shape[:2]
    roi_norm = {
        "x": round(ox / width, 4),
        "y": round(oy / height, 4),
        "w": round(side / width, 4),
        "h": round(side / height, 4),
    }
    if roi.size == 0 or _roi_is_dark(roi):
        update_detection_stability(state, None, [])
        return _empty(roi_norm)

    rejected: list[np.ndarray] = []
    score = None
    if mode == "guide":
        quad = _guide_quad(side)
        method = "guide"
    else:
        found = find_cube_face(roi, state.previous_quad)
        rejected = found["rejected"]
        score = found["score"]
        quad = found["quad"]
        method = "face"
        if quad is None:
            update_detection_stability(state, None, [])
            payload = _empty(roi_norm)
            if debug:
                payload["rejected"] = [_quad_to_frame(item, (ox, oy), frame.shape) for item in rejected]
            return payload

    warped = warp_cube_face(roi, quad)
    stickers = [_as_sticker(bgr, classifier) for bgr in sample_sticker_colors(warped)]
    colors = [sticker["color"] for sticker in stickers]
    stability, stable = update_detection_stability(state, quad, colors)
    status = STATUS_STABLE if stable else STATUS_HOLD
    payload = {
        "stickers": stickers,
        "locked": True,
        "stable": stable,
        "stability": stability,
        "method": method,
        "status": status,
        "quad": _quad_to_frame(quad, (ox, oy), frame.shape),
        "roi": roi_norm,
        "samples": _map_regions_to_frame(quad, (ox, oy), frame.shape),
        "rejected": [_quad_to_frame(item, (ox, oy), frame.shape) for item in rejected] if debug else [],
        "score": score,
        "warped": _encode_jpeg(warped) if debug else "",
    }
    return payload


def sample_face(
    image: np.ndarray,
    classifier: ColorClassifier,
    manual: bool | None = None,
    focus: tuple[float, float] | None = None,
    mode: str | None = None,
    state: DetectionState | None = None,
    debug: bool = False,
) -> dict:
    """Backward-compatible entry. The focus point is ignored on purpose."""
    del focus
    if mode is None:
        mode = "auto" if manual is False else "guide"
    return read_cube(image, classifier, mode=mode, state=state, debug=debug)
