from collections import deque

from cube_state import CubeState
from moves import ALL_MOVES


PHASE_2_MOVES = [
    "U", "U'", "U2",
    "D", "D'", "D2",
    "R2",
    "L2",
    "F2",
    "B2"
]


SLICE_EDGE_IDS = {8, 9, 10, 11}


def is_phase_1_solved(state):
    corners_oriented = all(
        orientation == 0
        for orientation in state.corner_orientation
    )

    edges_oriented = all(
        orientation == 0
        for orientation in state.edge_orientation
    )

    slice_edges_placed = (
        set(state.edge_permutation[8:12])
        == SLICE_EDGE_IDS
    )

    return (
        corners_oriented
        and edges_oriented
        and slice_edges_placed
    )


def slice_membership_key(state):
    membership = []

    for edge_id in state.edge_permutation:
        membership.append(
            edge_id in SLICE_EDGE_IDS
        )

    return tuple(membership)


def slice_permutation_key(state):
    return tuple(state.edge_permutation[8:12])


def build_slice_permutation_database():
    """Distance to place FR, FL, BL, BR in the U/D slice slots (order included)."""
    solved_state = CubeState.solved()
    solved_key = slice_permutation_key(solved_state)

    distances = {
        solved_key: 0
    }

    queue = deque([solved_state])

    while queue:
        current_state = queue.popleft()
        current_key = slice_permutation_key(current_state)
        current_distance = distances[current_key]

        for move in ALL_MOVES:
            child_state = current_state.apply_move(move)
            child_key = slice_permutation_key(child_state)

            if child_key not in distances:
                distances[child_key] = current_distance + 1
                queue.append(child_state)

    return distances


def phase_1_slice_distance(state, membership_database, permutation_database):
    tail = tuple(state.edge_permutation[8:12])
    if set(tail) == SLICE_EDGE_IDS:
        return permutation_database[tail]
    return membership_database[slice_membership_key(state)]


def build_slice_membership_database():
    solved_state = CubeState.solved()
    solved_key = slice_membership_key(solved_state)

    distances = {
        solved_key: 0
    }

    queue = deque([solved_state])

    while queue:
        current_state = queue.popleft()
        current_key = slice_membership_key(current_state)
        current_distance = distances[current_key]

        for move in ALL_MOVES:
            child_state = current_state.apply_move(move)
            child_key = slice_membership_key(child_state)

            if child_key not in distances:
                distances[child_key] = current_distance + 1
                queue.append(child_state)

    return distances


if __name__ == "__main__":
    database = build_slice_membership_database()

    print(
        "Slice membership patterns:",
        len(database)
    )

    print(
        "Maximum slice distance:",
        max(database.values())
    )