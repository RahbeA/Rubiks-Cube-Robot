"""Scan order and layout checks for the webcam scanner.

Cubie conversion lives in scanner.cubie_convert. Faces are stored as nine
color names, row-major, in the orientation printed on each scan step.
"""

from __future__ import annotations

from collections import Counter

from cube_state import CubeState
from scanner.colors import COLOR_TO_FACE, FACE_ORDER, FACE_TO_COLOR
from scanner.cubie_convert import colored_faces_to_cube_state

SCAN_STEPS = [
    {
        "face": "D",
        "color": "green",
        "title": "Show the green center",
        "hold": "Point the green center at the camera. Keep the white face along the top.",
        "nudge": "Green toward you, white on top.",
    },
    {
        "face": "R",
        "color": "red",
        "title": "Show the red center",
        "hold": "Point the red center at the camera. Roll the cube until blue is along the top.",
        "nudge": "Turn until red faces you, then roll blue to the top.",
    },
    {
        "face": "F",
        "color": "white",
        "title": "Show the white center",
        "hold": "Point the white center at the camera. Keep blue along the top.",
        "nudge": "Keep blue on top and turn until white faces you.",
    },
    {
        "face": "L",
        "color": "orange",
        "title": "Show the orange center",
        "hold": "Point the orange center at the camera. Keep blue along the top.",
        "nudge": "Keep blue on top and turn until orange faces you.",
    },
    {
        "face": "B",
        "color": "yellow",
        "title": "Show the yellow center",
        "hold": "Point the yellow center at the camera. Keep blue along the top.",
        "nudge": "Keep blue on top and turn until yellow faces you.",
    },
    {
        "face": "U",
        "color": "blue",
        "title": "Show the blue center",
        "hold": "Point the blue center at the camera. Keep white along the bottom.",
        "nudge": "Tip blue toward you, then turn it until white is at the bottom.",
    },
]

SCAN_GUIDE = {
    "U": {
        "title": "Blue on camera",
        "detail": "Hold the cube with the blue center toward the camera. Keep white at the bottom of the screen.",
        "top": "yellow",
        "bottom": "white",
    },
    "R": {
        "title": "Red on camera",
        "detail": "Red center toward the camera. Keep blue at the top of the screen.",
        "top": "blue",
        "bottom": "green",
    },
    "F": {
        "title": "White on camera",
        "detail": "White center toward the camera. Keep blue at the top of the screen.",
        "top": "blue",
        "bottom": "green",
    },
    "D": {
        "title": "Green on camera",
        "detail": "Green center toward the camera. Keep white at the top of the screen.",
        "top": "white",
        "bottom": "yellow",
    },
    "L": {
        "title": "Orange on camera",
        "detail": "Orange center toward the camera. Keep blue at the top of the screen.",
        "top": "blue",
        "bottom": "green",
    },
    "B": {
        "title": "Yellow on camera",
        "detail": "Yellow center toward the camera. Keep blue at the top of the screen.",
        "top": "blue",
        "bottom": "green",
    },
}


def _color_at(faces: dict[str, list[str]], face: str, index: int) -> str:
    value = faces[face][index]
    if value in COLOR_TO_FACE:
        return COLOR_TO_FACE[value]
    if value in FACE_TO_COLOR:
        return value
    raise ValueError(f"Unknown sticker value {value!r}")


def layout_report(faces: dict[str, list[str]]) -> dict:
    missing = [face for face in FACE_ORDER if face not in faces or len(faces[face]) != 9]
    colors = []
    for face in FACE_ORDER:
        if face in faces and len(faces[face]) == 9:
            colors.extend(_color_at(faces, face, i) for i in range(9))
    counts = Counter(colors)
    issues = []
    if missing:
        issues.append("Scan every face: " + ", ".join(missing))
    for face in FACE_ORDER:
        if face in faces and len(faces[face]) == 9:
            center = _color_at(faces, face, 4)
            if center != face:
                issues.append(f"{face} center should be {FACE_TO_COLOR[face]}, got {FACE_TO_COLOR.get(center, center)}")
    if not missing:
        for face in FACE_ORDER:
            if counts.get(face, 0) != 9:
                issues.append(f"{FACE_TO_COLOR[face]} appears {counts.get(face, 0)} times, expected 9")
    return {
        "complete": not missing,
        "counts": {FACE_TO_COLOR[face]: counts.get(face, 0) for face in FACE_ORDER},
        "issues": issues,
        "valid_layout": not issues,
    }


def faces_to_state(faces: dict[str, list[str]]) -> CubeState:
    """Scanner entry used by older callers. Validation lives in cubie_convert."""
    report = layout_report(faces)
    if not report["complete"]:
        raise ValueError("; ".join(report["issues"]))
    return colored_faces_to_cube_state(faces)


def facelet_string(faces: dict[str, list[str]]) -> str:
    chars = []
    for face in FACE_ORDER:
        for index in range(9):
            chars.append(_color_at(faces, face, index))
    return "".join(chars)


def solved_faces() -> dict[str, list[str]]:
    return {face: [FACE_TO_COLOR[face]] * 9 for face in FACE_ORDER}
