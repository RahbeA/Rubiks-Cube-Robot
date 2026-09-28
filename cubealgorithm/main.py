#Implementation of cubstate class with features such as storing CubeState as an object with 4 lists using orientation and permutation of each peice on the cube
#How this works is each piece is numbered. Edges (0-11) and Corners (0-7)
#Each move (U, F, B, D, R, L) and their inverses as well as doubles but  only 6 methods for each move was implemented
#Implemented methods for checking if cubestate is solved and valid
import random
from cube_state import CubeState
import time
from two_phase_solver import is_phase_1_solved, slice_membership_key, build_slice_membership_database
import time

from cube_state import CubeState
from solver import (
    solve_two_phase,
    phase_1_ida_star
)
import random
import threading
import time

from cube_state import CubeState
from moves import ALL_MOVES
from solver import solve_two_phase


def generate_scramble(length):
    scramble = []
    previous_face = None

    while len(scramble) < length:
        move = random.choice(ALL_MOVES)
        face = move[0]

        if face == previous_face:
            continue

        scramble.append(move)
        previous_face = face

    return scramble


def display_progress(stop_event, start_time):
    spinner = ["|", "/", "-", "\\"]
    spinner_index = 0

    while not stop_event.is_set():
        elapsed = time.time() - start_time

        print(
            f"\r{spinner[spinner_index]} Searching... "
            f"{elapsed:.1f} seconds",
            end="",
            flush=True
        )

        spinner_index = (spinner_index + 1) % len(spinner)

        # Wait 0.1 seconds, unless the solver finishes first.
        stop_event.wait(0.1)


scramble = generate_scramble(20)
cube = CubeState.solved().apply_sequence(scramble)

print("Scramble:", scramble)
print("Starting two-phase search...")

stop_event = threading.Event()
start_time = time.time()

progress_thread = threading.Thread(
    target=display_progress,
    args=(stop_event, start_time),
    daemon=True
)

progress_thread.start()

try:
    solution = solve_two_phase(cube)
finally:
    stop_event.set()
    progress_thread.join()

elapsed = time.time() - start_time

# Clear the progress line.
print("\r" + " " * 60, end="\r")

print("Search finished.")
print("Solution:", solution)

if solution is not None:
    solved_state = cube.apply_sequence(solution)

    print("Solution length:", len(solution))
    print("Solved:", solved_state.is_solved())
else:
    print("No solution found.")

print(f"Seconds: {elapsed:.3f}")