from cube_state import CubeState
from scanner.mapper import faces_to_state, layout_report, solved_faces


def rotate_cw(face):
    return [face[6], face[3], face[0], face[7], face[4], face[1], face[8], face[5], face[2]]


def copy_faces(faces):
    return {key: value[:] for key, value in faces.items()}


def move_u(faces):
    faces = copy_faces(faces)
    faces["U"] = rotate_cw(faces["U"])
    front = faces["F"][0:3]
    faces["F"][0:3] = faces["L"][0:3]
    faces["L"][0:3] = faces["B"][0:3]
    faces["B"][0:3] = faces["R"][0:3]
    faces["R"][0:3] = front
    return faces


def move_f(faces):
    faces = copy_faces(faces)
    faces["F"] = rotate_cw(faces["F"])
    up = [faces["U"][6], faces["U"][7], faces["U"][8]]
    faces["U"][6], faces["U"][7], faces["U"][8] = faces["L"][8], faces["L"][5], faces["L"][2]
    faces["L"][8], faces["L"][5], faces["L"][2] = faces["D"][2], faces["D"][1], faces["D"][0]
    faces["D"][2], faces["D"][1], faces["D"][0] = faces["R"][0], faces["R"][3], faces["R"][6]
    faces["R"][0], faces["R"][3], faces["R"][6] = up
    return faces


def test_solved_layout_is_identity():
    state = faces_to_state(solved_faces())
    assert state == CubeState.solved()
    assert state.is_valid()
    assert layout_report(solved_faces())["valid_layout"]


def test_u_move_matches_engine():
    # The cubie engine's U is counterclockwise relative to a standard
    # clockwise U on the sticker net, so clockwise U matches U'.
    state = faces_to_state(move_u(solved_faces()))
    assert state == CubeState.solved().apply_move("U'")


def test_f_move_matches_engine():
    state = faces_to_state(move_f(solved_faces()))
    assert state == CubeState.solved().apply_move("F")
    assert state.is_valid()


def test_sequence_matches_engine():
    faces = solved_faces()
    faces = move_u(faces)
    faces = move_f(faces)
    state = faces_to_state(faces)
    assert state == CubeState.solved().apply_sequence(["U'", "F"])
