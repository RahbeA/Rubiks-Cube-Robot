"""Scramble a solved cube and run the experimental two-phase solver."""

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