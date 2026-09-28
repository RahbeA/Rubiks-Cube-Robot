from collections import deque

from cube_state import CubeState
from moves import ALL_MOVES


PHASE_2_MOVES = [
    "U", "U'", "U2",
    "D", "D'", "D2",
    "R2", "L2", "F2", "B2"
]


# --------------------------------------------------
# KEYS
# --------------------------------------------------

def corner_orientation_key(state):
    return tuple(state.corner_orientation)


def edge_orientation_key(state):
    return tuple(state.edge_orientation)


def corner_permutation_key(state):
    return tuple(state.corner_permutation)


def edge_permutation_key(state, tracked_edges):
    perm = state.edge_permutation
    positions = [0] * 12
    for index, edge_id in enumerate(perm):
        positions[edge_id] = index
    return tuple(positions[edge_id] for edge_id in tracked_edges)


def slice_membership_key(state):
    slice_edges = {8, 9, 10, 11}

    return tuple(
        edge_id in slice_edges
        for edge_id in state.edge_permutation
    )


# --------------------------------------------------
# CORNER ORIENTATION DATABASE
# --------------------------------------------------

def build_corner_orientation_database():
    solved_state = CubeState.solved()
    solved_key = corner_orientation_key(solved_state)

    distances = {
        solved_key: 0
    }

    queue = deque([solved_state])

    while queue:
        current_state = queue.popleft()
        current_key = corner_orientation_key(current_state)
        current_distance = distances[current_key]

        for move in ALL_MOVES:
            child_state = current_state.apply_move(move)
            child_key = corner_orientation_key(child_state)

            if child_key not in distances:
                distances[child_key] = current_distance + 1
                queue.append(child_state)

    return distances


# --------------------------------------------------
# EDGE ORIENTATION DATABASE
# --------------------------------------------------

def build_edge_orientation_database():
    solved_state = CubeState.solved()
    solved_key = edge_orientation_key(solved_state)

    distances = {
        solved_key: 0
    }

    queue = deque([solved_state])

    while queue:
        current_state = queue.popleft()
        current_key = edge_orientation_key(current_state)
        current_distance = distances[current_key]

        for move in ALL_MOVES:
            child_state = current_state.apply_move(move)
            child_key = edge_orientation_key(child_state)

            if child_key not in distances:
                distances[child_key] = current_distance + 1
                queue.append(child_state)

    return distances


# --------------------------------------------------
# SLICE MEMBERSHIP DATABASE
# --------------------------------------------------

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


# --------------------------------------------------
# CORNER PERMUTATION DATABASE
# --------------------------------------------------

def build_corner_permutation_database(
    allowed_moves=ALL_MOVES
):
    solved_state = CubeState.solved()
    solved_key = corner_permutation_key(solved_state)

    distances = {
        solved_key: 0
    }

    queue = deque([solved_state])

    while queue:
        current_state = queue.popleft()
        current_key = corner_permutation_key(current_state)
        current_distance = distances[current_key]

        for move in allowed_moves:
            child_state = current_state.apply_move(move)
            child_key = corner_permutation_key(child_state)

            if child_key not in distances:
                distances[child_key] = current_distance + 1
                queue.append(child_state)

    return distances


# --------------------------------------------------
# TRACKED EDGE PERMUTATION DATABASE
# --------------------------------------------------

def build_edge_permutation_database(
    tracked_edges,
    allowed_moves=ALL_MOVES
):
    solved_state = CubeState.solved()

    solved_key = edge_permutation_key(
        solved_state,
        tracked_edges
    )

    distances = {
        solved_key: 0
    }

    queue = deque([solved_state])

    while queue:
        current_state = queue.popleft()

        current_key = edge_permutation_key(
            current_state,
            tracked_edges
        )

        current_distance = distances[current_key]

        for move in allowed_moves:
            child_state = current_state.apply_move(move)

            child_key = edge_permutation_key(
                child_state,
                tracked_edges
            )

            if child_key not in distances:
                distances[child_key] = current_distance + 1
                queue.append(child_state)

    return distances


# --------------------------------------------------
# PHASE 2 DATABASE BUILDERS
# --------------------------------------------------

def build_phase_2_corner_permutation_database():
    return build_corner_permutation_database(
        allowed_moves=PHASE_2_MOVES
    )


def build_phase_2_edge_permutation_database(
    tracked_edges
):
    return build_edge_permutation_database(
        tracked_edges=tracked_edges,
        allowed_moves=PHASE_2_MOVES
    )


# --------------------------------------------------
# DATABASE TESTS
# --------------------------------------------------

if __name__ == "__main__":
    print("Building Phase 1 databases...")

    corner_orientation_database = (
        build_corner_orientation_database()
    )

    edge_orientation_database = (
        build_edge_orientation_database()
    )

    slice_membership_database = (
        build_slice_membership_database()
    )

    print(
        "Corner orientation:",
        len(corner_orientation_database),
        max(corner_orientation_database.values())
    )

    print(
        "Edge orientation:",
        len(edge_orientation_database),
        max(edge_orientation_database.values())
    )

    print(
        "Slice membership:",
        len(slice_membership_database),
        max(slice_membership_database.values())
    )

    print("\nBuilding Phase 2 databases...")

    phase_2_corner_database = (
        build_phase_2_corner_permutation_database()
    )

    phase_2_edge_database_1 = (
        build_phase_2_edge_permutation_database(
            (0, 1, 2, 3)
        )
    )

    phase_2_edge_database_2 = (
        build_phase_2_edge_permutation_database(
            (4, 5, 6, 7)
        )
    )

    phase_2_edge_database_3 = (
        build_phase_2_edge_permutation_database(
            (8, 9, 10, 11)
        )
    )

    print(
        "Phase 2 corner permutation:",
        len(phase_2_corner_database),
        max(phase_2_corner_database.values())
    )

    print(
        "Phase 2 edge group 1:",
        len(phase_2_edge_database_1),
        max(phase_2_edge_database_1.values())
    )

    print(
        "Phase 2 edge group 2:",
        len(phase_2_edge_database_2),
        max(phase_2_edge_database_2.values())
    )

    print(
        "Phase 2 slice edges:",
        len(phase_2_edge_database_3),
        max(phase_2_edge_database_3.values())
    )