"""Run the two-phase solver in an isolated process with a hard wall-clock limit."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOLVE_CLI = ROOT / "cubealgorithm" / "solve_cli.py"
SOLVE_TIMEOUT_SECONDS = 90

_SOLVED_PAYLOAD = {
    "corner_permutation": list(range(8)),
    "corner_orientation": [0] * 8,
    "edge_permutation": list(range(12)),
    "edge_orientation": [0] * 12,
}


def warm_solver_worker() -> None:
    """Load pattern databases once so the first real solve is faster."""
    subprocess.run(
        [sys.executable, str(SOLVE_CLI)],
        input=json.dumps(_SOLVED_PAYLOAD).encode("utf-8"),
        capture_output=True,
        timeout=120,
        cwd=str(ROOT / "cubealgorithm"),
        check=False,
    )


def run_two_phase_solver(state: dict, faces: dict | None = None) -> dict:
    required = (
        "corner_permutation",
        "corner_orientation",
        "edge_permutation",
        "edge_orientation",
    )
    if not all(key in state for key in required):
        raise ValueError("Missing cubie arrays for the solver.")
    payload = {key: state[key] for key in required}
    if faces:
        payload["faces"] = faces

    try:
        completed = subprocess.run(
            [sys.executable, str(SOLVE_CLI)],
            input=json.dumps(payload).encode("utf-8"),
            capture_output=True,
            timeout=SOLVE_TIMEOUT_SECONDS,
            cwd=str(ROOT / "cubealgorithm"),
            check=False,
        )
    except subprocess.TimeoutExpired as error:
        raise ValueError(
            f"The solver did not finish within {SOLVE_TIMEOUT_SECONDS // 60} minutes. "
            "Install the kociemba package for fast facelet solving, or fix sticker colors on the layout."
        ) from error

    if completed.returncode != 0:
        stderr = completed.stderr.decode("utf-8", errors="replace").strip()
        raise ValueError(stderr or "The solver exited with an error.")

    try:
        result = json.loads(completed.stdout.decode("utf-8"))
    except json.JSONDecodeError as error:
        raise ValueError("The solver returned invalid output.") from error

    if "error" in result:
        raise ValueError(result["error"])
    return result
