"""Converter tests. No camera and no OpenCV.

cube_state_to_colored_faces is the inverse of the facelet tables. It exists
only so a CubeState from the move engine can be painted back into the
scanner's six-face layout. The geometric turns below are a second check:
they move stickers the way a physical quarter turn does in the scan
orientation, then the converter has to match the engine.
"""

from cube_state import CubeState
from scanner.colors import COLOR_TO_FACE as SCANNER_COLOR_TO_FACE
from scanner.cubie_convert import (
    COLOR_TO_FACE,
    CORNER_COLORS,
    CORNER_FACELETS,
    EDGE_COLORS,
    EDGE_FACELETS,
    FACE_ORDER,
    FACE_TO_COLOR,
    ScanLayoutError,
    colored_faces_to_cube_state,
    cube_state_to_colored_faces,
    faces_to_kociemba_string,
)

MOVES = ["U", "D", "F", "B", "R", "L"]
VARIANTS = [move + suffix for move in MOVES for suffix in ("", "'", "2")]
SEQUENCES = [
    ["R", "U", "R'", "U'"],
    ["F", "D", "U", "R", "B2"],
    ["R", "U", "F", "L", "D", "B", "R2", "U2", "F'"],
]


def solved_letters():
    return {face: [face] * 9 for face in FACE_ORDER}


def solved_colors():
    return {face: [FACE_TO_COLOR[face]] * 9 for face in FACE_ORDER}


def copy_faces(faces):
    return {face: stickers[:] for face, stickers in faces.items()}


def rotate_cw(face):
    return [face[6], face[3], face[0], face[7], face[4], face[1], face[8], face[5], face[2]]


def place_corner(colors, orientation):
    placed = [None] * 3
    for index, color in enumerate(colors):
        placed[(index + orientation) % 3] = color
    return placed


# Four boundary groups around the turned face, in clockwise order as viewed
# in the scan orientation. Each group moves onto the next one.
SIDE_CYCLES = {
    "U": [
        [("B", 2), ("B", 1), ("B", 0)],
        [("R", 2), ("R", 1), ("R", 0)],
        [("F", 2), ("F", 1), ("F", 0)],
        [("L", 2), ("L", 1), ("L", 0)],
    ],
    "D": [
        [("F", 6), ("F", 7), ("F", 8)],
        [("R", 6), ("R", 7), ("R", 8)],
        [("B", 6), ("B", 7), ("B", 8)],
        [("L", 6), ("L", 7), ("L", 8)],
    ],
    "F": [
        [("U", 6), ("U", 7), ("U", 8)],
        [("R", 0), ("R", 3), ("R", 6)],
        [("D", 2), ("D", 1), ("D", 0)],
        [("L", 8), ("L", 5), ("L", 2)],
    ],
    "B": [
        [("U", 2), ("U", 1), ("U", 0)],
        [("L", 0), ("L", 3), ("L", 6)],
        [("D", 6), ("D", 7), ("D", 8)],
        [("R", 8), ("R", 5), ("R", 2)],
    ],
    "R": [
        [("U", 8), ("U", 5), ("U", 2)],
        [("B", 0), ("B", 3), ("B", 6)],
        [("D", 8), ("D", 5), ("D", 2)],
        [("F", 8), ("F", 5), ("F", 2)],
    ],
    "L": [
        [("U", 0), ("U", 3), ("U", 6)],
        [("F", 0), ("F", 3), ("F", 6)],
        [("D", 0), ("D", 3), ("D", 6)],
        [("B", 8), ("B", 5), ("B", 2)],
    ],
}


def quarter_turn(faces, face):
    faces = copy_faces(faces)
    faces[face] = rotate_cw(faces[face])
    groups = SIDE_CYCLES[face]
    stored = [[faces[side][index] for side, index in group] for group in groups]
    for index, group in enumerate(groups):
        source = stored[(index - 1) % 4]
        for (side, sticker), value in zip(group, source):
            faces[side][sticker] = value
    return faces


def apply_geometric(moves):
    faces = solved_letters()
    for move in moves:
        repeats = {"": 1, "2": 2, "'": 3}[move[1:]]
        for _ in range(repeats):
            faces = quarter_turn(faces, move[0])
    return faces


def letters_to_colors(faces):
    return {face: [FACE_TO_COLOR[label] for label in stickers] for face, stickers in faces.items()}


def test_color_map_matches_scanner():
    assert COLOR_TO_FACE == SCANNER_COLOR_TO_FACE


def test_facelets_cover_each_sticker_once():
    seen = []
    for facelets in (*CORNER_FACELETS, *EDGE_FACELETS):
        seen.extend(facelets)
    assert len(seen) == len(set(seen)) == 48
    centers = {(face, 4) for face in FACE_ORDER}
    assert not centers.intersection(seen)


def test_solved_colored_layout():
    state = colored_faces_to_cube_state(solved_colors())
    assert state.corner_permutation == [0, 1, 2, 3, 4, 5, 6, 7]
    assert state.corner_orientation == [0, 0, 0, 0, 0, 0, 0, 0]
    assert state.edge_permutation == [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11]
    assert state.edge_orientation == [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
    assert state == CubeState.solved()
    assert state.is_solved()
    assert state.is_valid()


def test_solved_accepts_face_letters_and_color_case():
    assert colored_faces_to_cube_state(solved_letters()) == CubeState.solved()
    mixed = {FACE_TO_COLOR[face].upper(): [FACE_TO_COLOR[face].title()] * 9 for face in FACE_ORDER}
    assert colored_faces_to_cube_state(mixed) == CubeState.solved()


def test_every_base_move_matches_engine():
    for move in MOVES:
        expected = CubeState.solved().apply_move(move)
        painted = colored_faces_to_cube_state(cube_state_to_colored_faces(expected))
        geometric = colored_faces_to_cube_state(apply_geometric([move]))
        assert painted == expected
        assert geometric == expected
        assert painted.corner_orientation == expected.corner_orientation
        assert painted.edge_orientation == expected.edge_orientation


def test_move_variants_match_engine():
    for move in VARIANTS:
        expected = CubeState.solved().apply_move(move)
        actual = colored_faces_to_cube_state(cube_state_to_colored_faces(expected))
        geometric = colored_faces_to_cube_state(apply_geometric([move]))
        assert actual == expected
        assert geometric == expected


def test_known_sequences_match_engine():
    for sequence in SEQUENCES:
        expected = CubeState.solved().apply_sequence(sequence)
        actual = colored_faces_to_cube_state(cube_state_to_colored_faces(expected))
        geometric = colored_faces_to_cube_state(letters_to_colors(apply_geometric(sequence)))
        assert actual == expected
        assert geometric == expected
        assert actual.is_valid()


def test_faces_to_kociemba_matches_standard_solved_string():
    facelets = faces_to_kociemba_string(solved_colors())
    assert facelets == "UUUUUUUUURRRRRRRRRFFFFFFFFFDDDDDDDDDLLLLLLLLLBBBBBBBBB"


def test_kociemba_solution_solves_cubie_state():
    pytest = __import__("pytest")
    from scanner.kociemba_solve import kociemba_available, solve_colored_faces

    if not kociemba_available():
        pytest.skip("kociemba is not installed")
    state = CubeState.solved().apply_sequence(["R", "U", "F", "L", "D", "B"])
    faces = cube_state_to_colored_faces(state)
    moves = solve_colored_faces(faces)
    assert state.apply_sequence(moves).is_solved()


def test_missing_sticker_is_rejected():
    faces = solved_colors()
    faces["F"] = faces["F"][:-1]
    _reject(faces, "Face F contains 8 stickers instead of 9.")


def test_ten_stickers_of_one_color_are_rejected():
    faces = solved_colors()
    faces["F"][0] = "blue"
    _reject(
        faces,
        "Expected 9 U stickers but detected 10. Expected 9 F stickers but detected 8.",
    )


def test_duplicate_corner_is_rejected():
    faces = solved_letters()
    faces["F"][0] = "R"
    faces["L"][2] = "F"
    faces["R"][1] = "L"
    _reject(letters_to_colors(faces), "Corner cubie URF was detected more than once.")


def test_duplicate_edge_is_rejected():
    faces = solved_letters()
    faces["R"][1] = "F"
    faces["F"][7] = "R"
    _reject(letters_to_colors(faces), "Edge cubie UF was detected more than once.")


def test_twisted_corner_is_rejected():
    state = CubeState.solved()
    state.corner_orientation[0] = 1
    _reject(cube_state_to_colored_faces(state), "Corner orientation sum is impossible.")


def test_flipped_edge_is_rejected():
    state = CubeState.solved()
    state.edge_orientation[0] = 1
    _reject(cube_state_to_colored_faces(state), "Edge orientation sum is impossible.")


def test_parity_mismatch_is_rejected():
    state = CubeState.solved()
    state.corner_permutation = [1, 0, 2, 3, 4, 5, 6, 7]
    _reject(cube_state_to_colored_faces(state), "Edge and corner permutation parity do not match.")


def test_duplicated_center_is_rejected():
    faces = solved_colors()
    faces["R"][4] = "blue"
    _reject(faces, "Duplicated center color U.")


def test_rotated_face_is_rejected():
    faces = apply_geometric(["R"])
    faces["U"] = rotate_cw(faces["U"])
    try:
        colored_faces_to_cube_state(faces)
    except ScanLayoutError:
        return
    raise AssertionError("A rotated face was accepted")


def test_scanner_keeps_faces_and_skips_state_when_invalid():
    import app

    saved = app.faces
    twisted = cube_state_to_colored_faces(CubeState.solved())
    twisted = {face: stickers[:] for face, stickers in twisted.items()}
    # Twist the URF corner in the stored color layout: cycle U, R, F stickers.
    twisted["U"][8], twisted["R"][0], twisted["F"][2] = twisted["R"][0], twisted["F"][2], twisted["U"][8]
    try:
        app.faces = twisted
        payload = app.serialize_faces()
        assert payload["state"] is None
        assert payload["cubies"] is None
        assert payload["report"]["valid_layout"] is False
        assert payload["report"]["issues"][-1] == "Corner orientation sum is impossible."
        assert set(payload["faces"]) == set(FACE_ORDER)

        del app.faces["R"]
        rescanned = app.serialize_faces()
        assert rescanned["state"] is None
        assert "R" not in rescanned["faces"]
        assert set(rescanned["faces"]) == set("UFDLB")
    finally:
        app.faces = saved


def test_scanner_returns_solved_state():
    import app

    saved = app.faces
    try:
        app.faces = solved_colors()
        payload = app.serialize_faces()
        assert payload["state"]["valid"] is True
        assert payload["state"]["solved"] is True
        assert payload["state"]["corner_permutation"] == [0, 1, 2, 3, 4, 5, 6, 7]
        assert payload["state"]["edge_orientation"] == [0] * 12
    finally:
        app.faces = saved


def test_illegal_corner_message():
    faces = solved_letters()
    faces["R"][0] = "B"
    faces["B"][0] = "R"
    with_error = letters_to_colors(faces)
    try:
        colored_faces_to_cube_state(with_error)
    except ScanLayoutError as error:
        assert "Corner position URF contains" in str(error)
        assert "not a legal corner cubie" in str(error)
        return
    raise AssertionError("Illegal corner was accepted")


def _reject(faces, message):
    try:
        colored_faces_to_cube_state(faces)
    except ScanLayoutError as error:
        assert str(error) == message
        return
    raise AssertionError(f"Expected rejection: {message}")
