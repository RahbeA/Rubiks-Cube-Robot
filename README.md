# Cube Engine Visualizer

This adds a Three.js view to Rahbe's cubie-based Python engine. Python remains
the source of truth: every button sends notation such as `F`, `R2`, or `U'` to
`CubeState.apply_move()`, then the page displays the returned arrays.

## Run

```bash
python app.py
```

Open http://127.0.0.1:8000. No packages need to be installed.

## Files

- `cube_state.py` — the original cube engine
- `app.py` — the small standard-library HTTP bridge between Python and the browser
- `templates/index.html` — 3D rendering and move animation

The renderer never calculates cubie permutation or orientation. It only
animates the move accepted by the Python engine and displays Python's returned
state.
