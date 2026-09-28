"""Precomputed cubie move tables for fast search."""

from __future__ import annotations

from cube_state import CubeState
from moves import ALL_MOVES

MOVE_INDEX = {move: index for index, move in enumerate(ALL_MOVES)}

# Each table entry: (corner_src, corner_twist, edge_src, edge_flip)
_CORNER_SRC: tuple[tuple[int, ...], ...] = ()
_CORNER_TWIST: tuple[tuple[int, ...], ...] = ()
_EDGE_SRC: tuple[tuple[int, ...], ...] = ()
_EDGE_FLIP: tuple[tuple[int, ...], ...] = ()


def _build_tables() -> None:
    global _CORNER_SRC, _CORNER_TWIST, _EDGE_SRC, _EDGE_FLIP
    corner_src_rows: list[tuple[int, ...]] = []
    corner_twist_rows: list[tuple[int, ...]] = []
    edge_src_rows: list[tuple[int, ...]] = []
    edge_flip_rows: list[tuple[int, ...]] = []

    solved = CubeState.solved()
    for move in ALL_MOVES:
        after = solved.apply_move(move)
        corner_src = tuple(after.corner_permutation[position] for position in range(8))
        corner_twist = tuple(
            after.corner_orientation[position] for position in range(8)
        )
        edge_src = tuple(after.edge_permutation[position] for position in range(12))
        edge_flip = tuple(after.edge_orientation[position] for position in range(12))
        corner_src_rows.append(corner_src)
        corner_twist_rows.append(corner_twist)
        edge_src_rows.append(edge_src)
        edge_flip_rows.append(edge_flip)

    _CORNER_SRC = tuple(corner_src_rows)
    _CORNER_TWIST = tuple(corner_twist_rows)
    _EDGE_SRC = tuple(edge_src_rows)
    _EDGE_FLIP = tuple(edge_flip_rows)


def ensure_tables() -> None:
    if not _CORNER_SRC:
        _build_tables()


def apply_move_index(
    corner_permutation: tuple[int, ...],
    corner_orientation: tuple[int, ...],
    edge_permutation: tuple[int, ...],
    edge_orientation: tuple[int, ...],
    move_index: int,
) -> tuple[tuple[int, ...], tuple[int, ...], tuple[int, ...], tuple[int, ...]]:
    corner_src = _CORNER_SRC[move_index]
    corner_twist = _CORNER_TWIST[move_index]
    edge_src = _EDGE_SRC[move_index]
    edge_flip = _EDGE_FLIP[move_index]

    new_corner_perm = tuple(corner_permutation[corner_src[i]] for i in range(8))
    new_corner_ori = tuple(
        (corner_orientation[corner_src[i]] + corner_twist[i]) % 3 for i in range(8)
    )
    new_edge_perm = tuple(edge_permutation[edge_src[i]] for i in range(12))
    new_edge_ori = tuple(
        (edge_orientation[edge_src[i]] + edge_flip[i]) % 2 for i in range(12)
    )
    return new_corner_perm, new_corner_ori, new_edge_perm, new_edge_ori


def apply_move_name(
    corner_permutation: tuple[int, ...],
    corner_orientation: tuple[int, ...],
    edge_permutation: tuple[int, ...],
    edge_orientation: tuple[int, ...],
    move: str,
) -> tuple[tuple[int, ...], tuple[int, ...], tuple[int, ...], tuple[int, ...]]:
    ensure_tables()
    return apply_move_index(
        corner_permutation,
        corner_orientation,
        edge_permutation,
        edge_orientation,
        MOVE_INDEX[move],
    )
