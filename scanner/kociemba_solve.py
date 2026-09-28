"""Fast facelet solving via the kociemba package (optional dependency)."""

from __future__ import annotations


def kociemba_available() -> bool:
    try:
        import kociemba  # noqa: F401
    except ImportError:
        return False
    return True


def parse_kociemba_solution(text: str) -> list[str]:
    moves = text.strip().split()
    if not moves:
        return []
    return moves


def solve_facelets(facelet_string: str) -> list[str]:
    import kociemba

    solution = kociemba.solve(facelet_string)
    return parse_kociemba_solution(solution)


def solve_colored_faces(scanned_faces) -> list[str]:
    from scanner.cubie_convert import faces_to_kociemba_string

    facelets = faces_to_kociemba_string(scanned_faces)
    return solve_facelets(facelets)
