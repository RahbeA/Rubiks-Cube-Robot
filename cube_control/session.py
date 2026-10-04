"""Track a virtual cube for Cube Control (moves, scramble, solve)."""

from __future__ import annotations

import random
from typing import Any

from cube_state import CubeState

from cube_control.moves import ALL_MOVES


def invert_move(move: str) -> str:
    if move.endswith("2"):
        return move
    if move.endswith("'"):
        return move[0]
    return f"{move}'"


def invert_sequence(moves: list[str]) -> list[str]:
    return [invert_move(move) for move in reversed(moves)]


def generate_scramble(length: int = 20) -> list[str]:
    scramble: list[str] = []
    previous_face: str | None = None
    while len(scramble) < length:
        move = random.choice(ALL_MOVES)
        face = move[0]
        if face == previous_face:
            continue
        scramble.append(move)
        previous_face = face
    return scramble


def moves_to_algorithm(moves: list[str]) -> str:
    return " ".join(moves)


class CubeControlSession:
    def __init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        self.state = CubeState.solved()
        self.history: list[str] = []
        self.last_scramble: list[str] = []

    def apply_moves(self, moves: list[str]) -> None:
        for move in moves:
            self.state = self.state.apply_move(move)
            self.history.append(move)

    def apply_one(self, move: str) -> None:
        self.apply_moves([move])

    def scramble(self, length: int = 20) -> list[str]:
        moves = generate_scramble(length)
        self.apply_moves(moves)
        self.last_scramble = list(moves)
        return moves

    def solve(self) -> list[str]:
        if self.last_scramble:
            solution = invert_sequence(self.last_scramble)
        else:
            solution = self._kociemba_solution()
            if solution is None:
                raise ValueError("No scramble to reverse and the cube is not solvable from here.")
        self.apply_moves(solution)
        self.last_scramble = []
        return solution

    def _kociemba_solution(self) -> list[str] | None:
        if self.state.is_solved():
            return []
        try:
            from scanner.cubie_convert import cube_state_to_colored_faces
            from scanner.kociemba_solve import kociemba_available, solve_colored_faces
        except ImportError:
            return None
        if not kociemba_available():
            return None
        painted = cube_state_to_colored_faces(self.state)
        return solve_colored_faces(painted)

    def serialize(self) -> dict[str, Any]:
        return {
            "solved": self.state.is_solved(),
            "valid": self.state.is_valid(),
            "history": self.history,
            "last_scramble": self.last_scramble,
            "algorithm": moves_to_algorithm(self.history),
            "state": {
                "corner_permutation": self.state.corner_permutation,
                "corner_orientation": self.state.corner_orientation,
                "edge_permutation": self.state.edge_permutation,
                "edge_orientation": self.state.edge_orientation,
            },
        }


cube_control_session = CubeControlSession()
