"""Tuple-based cube state used inside IDA* search."""

from __future__ import annotations

from dataclasses import dataclass

from move_tables import MOVE_INDEX, apply_move_index, ensure_tables
from moves import ALL_MOVES


_SOLVED_CORNER_PERM = (0, 1, 2, 3, 4, 5, 6, 7)
_SOLVED_CORNER_ORI = (0, 0, 0, 0, 0, 0, 0, 0)
_SOLVED_EDGE_PERM = (0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11)
_SOLVED_EDGE_ORI = (0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)


@dataclass(frozen=True, slots=True)
class SearchState:
    corner_permutation: tuple[int, ...]
    corner_orientation: tuple[int, ...]
    edge_permutation: tuple[int, ...]
    edge_orientation: tuple[int, ...]

    def key(self) -> tuple[tuple[int, ...], tuple[int, ...], tuple[int, ...], tuple[int, ...]]:
        return (
            self.corner_permutation,
            self.corner_orientation,
            self.edge_permutation,
            self.edge_orientation,
        )

    def is_solved(self) -> bool:
        return (
            self.corner_permutation == _SOLVED_CORNER_PERM
            and self.corner_orientation == _SOLVED_CORNER_ORI
            and self.edge_permutation == _SOLVED_EDGE_PERM
            and self.edge_orientation == _SOLVED_EDGE_ORI
        )

    def apply_move(self, move: str) -> SearchState:
        ensure_tables()
        cp, co, ep, eo = apply_move_index(
            self.corner_permutation,
            self.corner_orientation,
            self.edge_permutation,
            self.edge_orientation,
            MOVE_INDEX[move],
        )
        return SearchState(cp, co, ep, eo)


def from_cube_state(state) -> SearchState:
    return SearchState(
        tuple(state.corner_permutation),
        tuple(state.corner_orientation),
        tuple(state.edge_permutation),
        tuple(state.edge_orientation),
    )


def to_cube_state(search_state: SearchState):
    from cube_state import CubeState

    return CubeState(
        list(search_state.corner_permutation),
        list(search_state.corner_orientation),
        list(search_state.edge_permutation),
        list(search_state.edge_orientation),
    )
