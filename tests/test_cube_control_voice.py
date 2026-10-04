from cube_control.session import CubeControlSession, invert_sequence
from cube_control.voice import parse_voice_best, parse_voice_transcript


def test_voice_single_and_prime():
    assert parse_voice_transcript("R") == {"type": "moves", "moves": ["R"]}
    assert parse_voice_transcript("R prime") == {"type": "moves", "moves": ["R'"]}
    assert parse_voice_transcript("R 2") == {"type": "moves", "moves": ["R2"]}


def test_voice_commands():
    assert parse_voice_transcript("Scramble") == {"type": "command", "command": "scramble"}
    assert parse_voice_transcript("solve") == {"type": "command", "command": "solve"}
    assert parse_voice_transcript("Scramble the cube") == {"type": "command", "command": "scramble"}
    assert parse_voice_transcript("solve it now") == {"type": "command", "command": "solve"}


def test_voice_best_alternative():
    parsed = parse_voice_best("scramble the cube", ["our prime"])
    assert parsed == {"type": "command", "command": "scramble"}
    parsed = parse_voice_best("garbage", ["R prime"])
    assert parsed["type"] == "moves"
    assert parsed["moves"] == ["R'"]
    assert parsed.get("heard") == "R prime"


def test_scramble_solve_inverse():
    session = CubeControlSession()
    scramble = session.scramble(10)
    assert not session.state.is_solved()
    solution = session.solve()
    assert invert_sequence(scramble) == solution
    assert session.state.is_solved()
