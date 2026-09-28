"""Read cubie state and optional face layout from stdin; print JSON solution."""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cube_state import CubeState
from solver import solve_two_phase


def solve_from_faces(scanned_faces: dict) -> list[str] | None:
    try:
        from scanner.kociemba_solve import kociemba_available, solve_colored_faces
    except ImportError:
        return None
    if not kociemba_available():
        return None
    return solve_colored_faces(scanned_faces)


def solve_from_cubies(state: CubeState) -> list[str] | None:
    if state.is_solved():
        return []
    solution = solve_two_phase(state)
    if solution is None:
        return None
    if solution:
        check = state.apply_sequence(solution)
        if not check.is_solved():
            raise RuntimeError("Internal two-phase solver returned an invalid solution.")
    return solution


def main() -> None:
    payload = json.load(sys.stdin)
    state = CubeState(
        payload["corner_permutation"],
        payload["corner_orientation"],
        payload["edge_permutation"],
        payload["edge_orientation"],
    )
    if not state.is_valid():
        print(json.dumps({"error": "Cube state is not valid."}))
        return

    faces = payload.get("faces")
    solution = None
    solver_used = "two_phase"

    if faces:
        try:
            solution = solve_from_faces(faces)
            if solution is not None:
                solver_used = "kociemba"
        except Exception as error:  # noqa: BLE001 — surface to HTTP layer
            print(json.dumps({"error": f"Facelet solver failed: {error}"}))
            return

    if solution is None:
        try:
            solution = solve_from_cubies(state)
        except RuntimeError as error:
            print(json.dumps({"error": str(error)}))
            return

    if solution is None:
        print(json.dumps({"error": "No solution was found."}))
        return

    print(json.dumps({"solution": solution, "solver": solver_used}))


if __name__ == "__main__":
    main()
