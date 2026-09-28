# Cube Engine CV

Webcam scanner for Rahbe's cubie engine. Hold each face in the on-screen
grid; Python reads the nine sticker colors, builds the full six-face layout,
and maps it onto the same `CubeState` arrays the visualizer already uses.

Color matching uses CIE Lab + CIEDE2000, the same approach popularized by
open-source webcam solvers such as [QBR](https://github.com/kkoomen/qbr).
Detection is a guided 3×3 overlay (reliable in ordinary room light) with an
optional contour snap when nine sticker squares are visible.

## Run

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cd web && npm install && npm run build && cd ..
python app.py
```

Open http://127.0.0.1:8000 and allow the camera. The page is a React app
built into `web/dist`. While changing the UI, run `npm run dev` in `web`
(it proxies `/api` to the Python server on port 8000).

## Scan

The page walks through six faces. Hold the cube in one hand. MediaPipe follows
the hand, and the scanner locks an outline onto the nine stickers, so the cube
does not have to sit inside a fixed box.

| Step | Show this center | Along the top |
| --- | --- | --- |
| 1 | green | white |
| 2 | red | blue |
| 3 | white | blue |
| 4 | orange | blue |
| 5 | yellow | blue |
| 6 | blue | white along the **bottom** |

Hold the outline steady and the face saves itself. If a sticker is wrong, tap
it and then a color. "Line it up myself" switches to a fixed guide. After six
faces the page prints the cubie permutation and orientation arrays.

## Files

- `app.py` — local HTTP app
- `scanner/detect.py` — 3×3 sampling
- `scanner/colors.py` — Lab / CIEDE2000 classifier
- `scanner/mapper.py` — stickers → `CubeState`
- `cube_state.py` — copy of the cubie engine
- `web/` — React camera, net, and 3D preview
