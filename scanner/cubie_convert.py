"""Convert a classified six-face layout into the existing CubeState.

The scanner stores color names. This module does not import OpenCV and does
not turn faces on its own. Layouts are only valid in this scan orientation,
viewed directly, with the neighboring center toward the top of the image:

    Face    Neighbor pointing upward
    U       B
    R       U
    F       U
    D       F
    L       U
    B       U

Each face is nine labels in row-major order:

    0 1 2
    3 4 5
    6 7 8

Sticker numbers in the facelet tables below are those indexes. They are the
one-based positions from the cubie spec, minus one. Faces are not rotated
here; the capture step has to follow the orientation above.
"""

from __future__ import annotations

from collections import Counter

from cube_state import CubeState

FACE_ORDER = "URFDLB"

# Same permanent mapping as scanner.colors. Defined here so conversion tests
# do not need the camera stack.
COLOR_TO_FACE = {
    "blue": "U",
    "green": "D",
    "white": "F",
    "yellow": "B",
    "red": "R",
    "orange": "L",
}
FACE_TO_COLOR = {face: name for name, face in COLOR_TO_FACE.items()}

SCAN_ORIENTATION = (
    "View each face straight on. Keep yellow (B) above blue (U), "
    "white (F) above green (D), and blue (U) above red, white, orange, and yellow."
)

CORNER_NAMES = ["URF", "UFL", "ULB", "UBR", "DFR", "DLF", "DBL", "DRB"]
EDGE_NAMES = ["UR", "UF", "UL", "UB", "DR", "DF", "DL", "DB", "FR", "FL", "BL", "BR"]

CORNER_COLORS = [
    ("U", "R", "F"),  # 0 URF
    ("U", "F", "L"),  # 1 UFL
    ("U", "L", "B"),  # 2 ULB
    ("U", "B", "R"),  # 3 UBR
    ("D", "F", "R"),  # 4 DFR
    ("D", "L", "F"),  # 5 DLF
    ("D", "B", "L"),  # 6 DBL
    ("D", "R", "B"),  # 7 DRB
]

EDGE_COLORS = [
    ("U", "R"),  # 0 UR
    ("U", "F"),  # 1 UF
    ("U", "L"),  # 2 UL
    ("U", "B"),  # 3 UB
    ("D", "R"),  # 4 DR
    ("D", "F"),  # 5 DF
    ("D", "L"),  # 6 DL
    ("D", "B"),  # 7 DB
    ("F", "R"),  # 8 FR
    ("F", "L"),  # 9 FL
    ("B", "L"),  # 10 BL
    ("B", "R"),  # 11 BR
]

# (face, zero-based index). Comments show the one-based sticker number.
CORNER_FACELETS = [
    (("U", 8), ("R", 0), ("F", 2)),  # URF  9, 1, 3
    (("U", 6), ("F", 0), ("L", 2)),  # UFL  7, 1, 3
    (("U", 0), ("L", 0), ("B", 2)),  # ULB  1, 1, 3
    (("U", 2), ("B", 0), ("R", 2)),  # UBR  3, 1, 3
    (("D", 2), ("F", 8), ("R", 6)),  # DFR  3, 9, 7
    (("D", 0), ("L", 8), ("F", 6)),  # DLF  1, 9, 7
    (("D", 6), ("B", 8), ("L", 6)),  # DBL  7, 9, 7
    (("D", 8), ("R", 8), ("B", 6)),  # DRB  9, 9, 7
]

EDGE_FACELETS = [
    (("U", 5), ("R", 1)),  # UR  6, 2
    (("U", 7), ("F", 1)),  # UF  8, 2
    (("U", 3), ("L", 1)),  # UL  4, 2
    (("U", 1), ("B", 1)),  # UB  2, 2
    (("D", 5), ("R", 7)),  # DR  6, 8
    (("D", 1), ("F", 7)),  # DF  2, 8
    (("D", 3), ("L", 7)),  # DL  4, 8
    (("D", 7), ("B", 7)),  # DB  8, 8
    (("F", 5), ("R", 3)),  # FR  6, 4
    (("F", 3), ("L", 5)),  # FL  4, 6
    (("B", 5), ("L", 3)),  # BL  6, 4
    (("B", 3), ("R", 5)),  # BR  4, 6
]

_CORNER_BY_COLORS = {frozenset(colors): index for index, colors in enumerate(CORNER_COLORS)}
_EDGE_BY_COLORS = {frozenset(colors): index for index, colors in enumerate(EDGE_COLORS)}


class ScanLayoutError(ValueError):
    """The colored layout cannot become a reachable CubeState."""


def colored_faces_to_cube_state(scanned_faces) -> CubeState:
    """Normalize six classified faces and return a valid CubeState.

    ``scanned_faces`` is the scanner's dictionary: each key is a face letter
    or a color name, and each value is nine sticker labels (color names or
    face letters). The center sticker is the face's identity.
    """
    faces = _normalize_faces(scanned_faces)
    corner_permutation, corner_orientation = _read_corners(faces)
    edge_permutation, edge_orientation = _read_edges(faces)
    state = CubeState(
        corner_permutation,
        corner_orientation,
        edge_permutation,
        edge_orientation,
    )
    return _require_valid(state)


def _normalize_faces(scanned_faces) -> dict[str, list[str]]:
    if not isinstance(scanned_faces, dict):
        raise ScanLayoutError("Expected a dictionary of six faces.")
    if len(scanned_faces) != 6:
        raise ScanLayoutError(f"Expected 6 faces but detected {len(scanned_faces)}.")

    parsed: list[tuple[str, list[str]]] = []
    seen_keys: set[str] = set()
    for key, stickers in scanned_faces.items():
        face_key = _face_name(key)
        if face_key in seen_keys:
            raise ScanLayoutError(f"Face {face_key} was detected more than once.")
        seen_keys.add(face_key)
        if not isinstance(stickers, (list, tuple)):
            raise ScanLayoutError(f"Face {face_key} contains {len(stickers) if hasattr(stickers, '__len__') else 0} stickers instead of 9.")
        if len(stickers) != 9:
            raise ScanLayoutError(f"Face {face_key} contains {len(stickers)} stickers instead of 9.")
        parsed.append((face_key, [_sticker_face(value) for value in stickers]))

    centers = [labels[4] for _, labels in parsed]
    center_counts = Counter(centers)
    duplicated = [face for face in FACE_ORDER if center_counts[face] > 1]
    if duplicated:
        raise ScanLayoutError(f"Duplicated center color {duplicated[0]}.")
    missing_centers = [face for face in FACE_ORDER if center_counts[face] == 0]
    if missing_centers:
        raise ScanLayoutError(f"Missing center for face {missing_centers[0]}.")

    faces: dict[str, list[str]] = {}
    for face_key, labels in parsed:
        center = labels[4]
        if center != face_key:
            raise ScanLayoutError(f"Face {face_key} center is {center}, expected {face_key}.")
        faces[face_key] = labels

    counts = Counter(label for labels in faces.values() for label in labels)
    mismatches = [
        f"Expected 9 {face} stickers but detected {counts[face]}."
        for face in FACE_ORDER
        if counts[face] != 9
    ]
    if mismatches:
        raise ScanLayoutError(" ".join(mismatches))
    return faces


def _face_name(value) -> str:
    if not isinstance(value, str):
        raise ScanLayoutError(f"Unknown face {value!r}.")
    token = value.strip()
    if token.upper() in FACE_ORDER and len(token) == 1:
        return token.upper()
    lowered = token.lower()
    if lowered in COLOR_TO_FACE:
        return COLOR_TO_FACE[lowered]
    raise ScanLayoutError(f"Unknown face {value!r}.")


def _sticker_face(value) -> str:
    if not isinstance(value, str):
        raise ScanLayoutError(f"Unknown sticker value {value!r}.")
    token = value.strip()
    if token.upper() in FACE_ORDER and len(token) == 1:
        return token.upper()
    lowered = token.lower()
    if lowered in COLOR_TO_FACE:
        return COLOR_TO_FACE[lowered]
    raise ScanLayoutError(f"Unknown sticker value {value!r}.")


def _read_corners(faces: dict[str, list[str]]) -> tuple[list[int], list[int]]:
    permutation = [0] * 8
    orientation = [0] * 8
    seen: dict[int, str] = {}
    for slot, facelets in enumerate(CORNER_FACELETS):
        observed = tuple(faces[face][index] for face, index in facelets)
        cubie = _CORNER_BY_COLORS.get(frozenset(observed))
        if cubie is None or len(set(observed)) != 3:
            raise ScanLayoutError(
                f"Corner position {CORNER_NAMES[slot]} contains {observed}, which is not a legal corner cubie."
            )
        if cubie in seen:
            raise ScanLayoutError(f"Corner cubie {CORNER_NAMES[cubie]} was detected more than once.")
        seen[cubie] = CORNER_NAMES[slot]
        permutation[slot] = cubie
        ud_color = CORNER_COLORS[cubie][0]
        twist = observed.index(ud_color)
        placed = _place_corner(CORNER_COLORS[cubie], twist)
        if placed != observed:
            raise ScanLayoutError(
                f"Corner position {CORNER_NAMES[slot]} contains {observed}, which is not a legal corner cubie."
            )
        orientation[slot] = twist
    missing = [CORNER_NAMES[index] for index in range(8) if index not in seen]
    if missing:
        raise ScanLayoutError(f"Corner cubie {missing[0]} is missing.")
    return permutation, orientation


def _read_edges(faces: dict[str, list[str]]) -> tuple[list[int], list[int]]:
    permutation = [0] * 12
    orientation = [0] * 12
    seen: dict[int, str] = {}
    for slot, facelets in enumerate(EDGE_FACELETS):
        observed = tuple(faces[face][index] for face, index in facelets)
        cubie = _EDGE_BY_COLORS.get(frozenset(observed))
        if cubie is None or len(set(observed)) != 2:
            raise ScanLayoutError(
                f"Edge position {EDGE_NAMES[slot]} contains {observed}, which is not a legal edge cubie."
            )
        if cubie in seen:
            raise ScanLayoutError(f"Edge cubie {EDGE_NAMES[cubie]} was detected more than once.")
        seen[cubie] = EDGE_NAMES[slot]
        permutation[slot] = cubie
        canonical = EDGE_COLORS[cubie]
        if observed == canonical:
            orientation[slot] = 0
        elif observed == (canonical[1], canonical[0]):
            orientation[slot] = 1
        else:
            raise ScanLayoutError(
                f"Edge position {EDGE_NAMES[slot]} contains {observed}, which is not a legal edge cubie."
            )
    missing = [EDGE_NAMES[index] for index in range(12) if index not in seen]
    if missing:
        raise ScanLayoutError(f"Edge cubie {missing[0]} is missing.")
    return permutation, orientation


def _place_corner(colors: tuple[str, str, str], orientation: int) -> tuple[str, str, str]:
    placed = [""] * 3
    for index, color in enumerate(colors):
        placed[(index + orientation) % 3] = color
    return tuple(placed)


def _require_valid(state: CubeState) -> CubeState:
    if state.is_valid():
        return state
    messages = []
    if state.permutation_parity(state.corner_permutation) != state.permutation_parity(state.edge_permutation):
        messages.append("Edge and corner permutation parity do not match.")
    if sum(state.corner_orientation) % 3 != 0:
        messages.append("Corner orientation sum is impossible.")
    if sum(state.edge_orientation) % 2 != 0:
        messages.append("Edge orientation sum is impossible.")
    if not messages:
        messages.append("Cube state is not reachable.")
    raise ScanLayoutError(" ".join(messages))


def _place_corner_on_faces(
    colors: tuple[str, str, str], orientation: int
) -> tuple[str, str, str]:
    return _place_corner(colors, orientation)


def cube_state_to_colored_faces(state: CubeState) -> dict[str, list[str]]:
    """Paint scanner color names from a cubie state using the facelet tables."""
    faces = {face: [face] * 9 for face in FACE_ORDER}
    for slot, facelets in enumerate(CORNER_FACELETS):
        cubie = state.corner_permutation[slot]
        placed = _place_corner_on_faces(CORNER_COLORS[cubie], state.corner_orientation[slot])
        for (face, index), label in zip(facelets, placed):
            faces[face][index] = label
    for slot, facelets in enumerate(EDGE_FACELETS):
        first, second = EDGE_COLORS[state.edge_permutation[slot]]
        if state.edge_orientation[slot]:
            first, second = second, first
        for (face, index), label in zip(facelets, (first, second)):
            faces[face][index] = label
    return {
        face: [FACE_TO_COLOR[label] for label in stickers]
        for face, stickers in faces.items()
    }


def compare_colored_faces(
    left: dict[str, list[str]], right: dict[str, list[str]]
) -> list[str]:
    """Return human-readable mismatches between two six-face layouts."""
    issues: list[str] = []
    for face in FACE_ORDER:
        left_row = left.get(face)
        right_row = right.get(face)
        if left_row is None or right_row is None:
            issues.append(f"Face {face} is missing from one layout.")
            continue
        for index, (a, b) in enumerate(zip(left_row, right_row)):
            if a != b:
                issues.append(
                    f"{face} sticker {index}: scan has {a!r}, cubie layout has {b!r}."
                )
    return issues


def layout_consistency_issues(scanned_faces) -> list[str]:
    """Check that stickers convert to cubies and paint back to the same colors."""
    try:
        normalized = _normalize_faces(scanned_faces)
    except ScanLayoutError as error:
        return [str(error)]
    try:
        state = colored_faces_to_cube_state(normalized)
    except ScanLayoutError as error:
        return [str(error)]
    roundtrip = cube_state_to_colored_faces(state)
    return compare_colored_faces(normalized, roundtrip)


def faces_to_kociemba_string(scanned_faces) -> str:
    """Build the 54-character facelet string in URFDLB order for Herbert Kociemba's solver."""
    faces = _normalize_faces(scanned_faces)
    letters: list[str] = []
    for face in FACE_ORDER:
        for sticker in faces[face]:
            letters.append(sticker)
    return "".join(letters)
