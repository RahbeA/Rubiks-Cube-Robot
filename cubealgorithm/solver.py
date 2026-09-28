from moves import ALL_MOVES

from pattern_database import (
    build_corner_orientation_database,
    build_edge_orientation_database,
    build_corner_permutation_database,
    build_edge_permutation_database,
    build_slice_membership_database,
    build_phase_2_corner_permutation_database,
    build_phase_2_edge_permutation_database,
    corner_orientation_key,
    edge_orientation_key,
    corner_permutation_key,
    edge_permutation_key,
    slice_membership_key,
)

from two_phase_solver import (
    PHASE_2_MOVES,
    is_phase_1_solved,
    build_slice_permutation_database,
    phase_1_slice_distance,
)
from search_state import SearchState, from_cube_state


# Edge groups must exist before any database uses them.
EDGE_GROUP_1 = (0, 1, 2, 3)
EDGE_GROUP_2 = (4, 5, 6, 7)
EDGE_GROUP_3 = (8, 9, 10, 11)


# Phase 1 databases
CORNER_ORIENTATION_DATABASE = build_corner_orientation_database()
EDGE_ORIENTATION_DATABASE = build_edge_orientation_database()
SLICE_MEMBERSHIP_DATABASE = build_slice_membership_database()
SLICE_PERMUTATION_DATABASE = build_slice_permutation_database()


# Full-cube databases (used by the original full-cube IDA* search)
_FULL_CUBE_DATABASES = None


def _full_cube_heuristic_databases():
    global _FULL_CUBE_DATABASES
    if _FULL_CUBE_DATABASES is None:
        _FULL_CUBE_DATABASES = (
            build_corner_permutation_database(),
            build_edge_permutation_database(EDGE_GROUP_1),
            build_edge_permutation_database(EDGE_GROUP_2),
            build_edge_permutation_database(EDGE_GROUP_3),
        )
    return _FULL_CUBE_DATABASES


# Phase 2 databases, built using only legal Phase 2 moves
PHASE_2_CORNER_PERMUTATION_DATABASE = (
    build_phase_2_corner_permutation_database()
)

PHASE_2_EDGE_PERMUTATION_DATABASE_1 = (
    build_phase_2_edge_permutation_database(EDGE_GROUP_1)
)

PHASE_2_EDGE_PERMUTATION_DATABASE_2 = (
    build_phase_2_edge_permutation_database(EDGE_GROUP_2)
)

PHASE_2_EDGE_PERMUTATION_DATABASE_3 = (
    build_phase_2_edge_permutation_database(EDGE_GROUP_3)
)


OPPOSITE_FACES = {
    "U": "D",
    "D": "U",
    "F": "B",
    "B": "F",
    "R": "L",
    "L": "R",
}


def should_skip_move(current_path, move):
    if not current_path:
        return False

    previous_face = current_path[-1][0]
    next_face = move[0]

    # Consecutive turns of one face can be represented by one move.
    if previous_face == next_face:
        return True

    # Opposite faces commute, so search only one ordering.
    if OPPOSITE_FACES[previous_face] == next_face:
        if previous_face > next_face:
            return True

    return False


def heuristic(state):
    (
        corner_permutation_database,
        edge_permutation_database_1,
        edge_permutation_database_2,
        edge_permutation_database_3,
    ) = _full_cube_heuristic_databases()

    corner_orientation_distance = CORNER_ORIENTATION_DATABASE[
        corner_orientation_key(state)
    ]

    edge_orientation_distance = EDGE_ORIENTATION_DATABASE[
        edge_orientation_key(state)
    ]

    corner_permutation_distance = corner_permutation_database[
        corner_permutation_key(state)
    ]

    edge_permutation_distance_1 = edge_permutation_database_1[
        edge_permutation_key(state, EDGE_GROUP_1)
    ]

    edge_permutation_distance_2 = edge_permutation_database_2[
        edge_permutation_key(state, EDGE_GROUP_2)
    ]

    edge_permutation_distance_3 = edge_permutation_database_3[
        edge_permutation_key(state, EDGE_GROUP_3)
    ]

    return max(
        corner_orientation_distance,
        edge_orientation_distance,
        corner_permutation_distance,
        edge_permutation_distance_1,
        edge_permutation_distance_2,
        edge_permutation_distance_3,
    )


def phase_1_heuristic(state):
    corner_distance = CORNER_ORIENTATION_DATABASE[
        corner_orientation_key(state)
    ]

    edge_distance = EDGE_ORIENTATION_DATABASE[
        edge_orientation_key(state)
    ]

    slice_distance = phase_1_slice_distance(
        state,
        SLICE_MEMBERSHIP_DATABASE,
        SLICE_PERMUTATION_DATABASE,
    )

    return max(corner_distance, edge_distance, slice_distance)


def phase_2_heuristic(state):
    corner_distance = PHASE_2_CORNER_PERMUTATION_DATABASE[
        corner_permutation_key(state)
    ]

    edge_distance_1 = PHASE_2_EDGE_PERMUTATION_DATABASE_1[
        edge_permutation_key(state, EDGE_GROUP_1)
    ]

    edge_distance_2 = PHASE_2_EDGE_PERMUTATION_DATABASE_2[
        edge_permutation_key(state, EDGE_GROUP_2)
    ]

    edge_distance_3 = PHASE_2_EDGE_PERMUTATION_DATABASE_3[
        edge_permutation_key(state, EDGE_GROUP_3)
    ]

    return max(
        corner_distance,
        edge_distance_1,
        edge_distance_2,
        edge_distance_3,
    )


def ida_star_search(
    start_state,
    goal_function,
    heuristic_function,
    allowed_moves,
):
    threshold = heuristic_function(start_state)

    while True:
        path_keys = {start_state.key()}
        transposition = {}

        solution, next_threshold = ida_recursive_search(
            current_state=start_state,
            current_path=[],
            threshold=threshold,
            path_keys=path_keys,
            transposition=transposition,
            goal_function=goal_function,
            heuristic_function=heuristic_function,
            allowed_moves=allowed_moves,
        )

        if solution is not None:
            return solution

        if next_threshold == float("inf"):
            return None

        threshold = next_threshold


def ida_recursive_search(
    current_state,
    current_path,
    threshold,
    path_keys,
    transposition,
    goal_function,
    heuristic_function,
    allowed_moves,
):
    g = len(current_path)
    h = heuristic_function(current_state)
    f = g + h

    if f > threshold:
        return None, f

    if goal_function(current_state):
        return list(current_path), None

    state_key = current_state.key()
    best_g = transposition.get(state_key)
    if best_g is not None and best_g <= g:
        return None, f

    transposition[state_key] = g

    minimum_exceeded = float("inf")
    child_moves = []

    for move in allowed_moves:
        if should_skip_move(current_path, move):
            continue

        child_state = current_state.apply_move(move)
        child_key = child_state.key()

        if child_key in path_keys:
            continue

        child_h = heuristic_function(child_state)
        child_f = g + 1 + child_h
        if child_f > threshold:
            if child_f < minimum_exceeded:
                minimum_exceeded = child_f
            continue

        child_moves.append((child_h, move, child_state, child_key))

    child_moves.sort(key=lambda item: item[0])

    for _, move, child_state, child_key in child_moves:
        current_path.append(move)
        path_keys.add(child_key)

        solution, exceeded = ida_recursive_search(
            current_state=child_state,
            current_path=current_path,
            threshold=threshold,
            path_keys=path_keys,
            transposition=transposition,
            goal_function=goal_function,
            heuristic_function=heuristic_function,
            allowed_moves=allowed_moves,
        )

        path_keys.remove(child_key)
        current_path.pop()

        if solution is not None:
            return solution, None

        if exceeded < minimum_exceeded:
            minimum_exceeded = exceeded

    return None, minimum_exceeded


def ida_star(start_state):
    return ida_star_search(
        start_state=start_state,
        goal_function=lambda state: state.is_solved(),
        heuristic_function=heuristic,
        allowed_moves=ALL_MOVES,
    )


def phase_1_ida_star(start_state):
    return ida_star_search(
        start_state=start_state,
        goal_function=is_phase_1_solved,
        heuristic_function=phase_1_heuristic,
        allowed_moves=ALL_MOVES,
    )


def phase_2_ida_star(start_state):
    if not is_phase_1_solved(start_state):
        raise ValueError(
            "Phase 2 can only begin from a Phase 1 solved state."
        )

    return ida_star_search(
        start_state=start_state,
        goal_function=lambda state: state.is_solved(),
        heuristic_function=phase_2_heuristic,
        allowed_moves=PHASE_2_MOVES,
    )


def solve_two_phase(start_state):
    if start_state.is_solved():
        return []

    search_start = from_cube_state(start_state)

    phase_1_solution = phase_1_ida_star(search_start)

    if phase_1_solution is None:
        return None

    phase_1_state = search_start
    for move in phase_1_solution:
        phase_1_state = phase_1_state.apply_move(move)

    phase_2_solution = phase_2_ida_star(phase_1_state)

    if phase_2_solution is None:
        return None

    return phase_1_solution + phase_2_solution
