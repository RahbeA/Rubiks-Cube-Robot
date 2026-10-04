# Cube Engine

Local tools for a stepper-driven Rubik’s Cube robot: a cubie-state engine, an experimental two-phase solver, a webcam color scanner, a React UI, and USB serial output to an Arduino.

Kociemba is the practical fast solver when the `kociemba` package imports. The custom two-phase search is a separate experiment. Solver time on the computer is not the time the robot spends turning faces.

The robot firmware is `firmware/rubi_x/rubi_x.ino`. The mechanical models come from [t33devv/rubik](https://github.com/t33devv/rubik) and are not copied into this repository.

## Architecture

```text
webcam / React UI  →  app.py  →  cubie engine (cube_state.py)
                         │
                         ├─ /api/solve
                         │    faces present and kociemba imports → Kociemba
                         │    otherwise → experimental two-phase solver
                         │
                         └─ /api/cube-control/*
                              virtual cube, voice phrases, USB serial
```

- `cube_state.py` stores 8 corners and 12 edges as permutation and orientation arrays. Face colors in this project are U blue, D green, F white, B yellow, R red, L orange.
- `cubealgorithm/` is the experimental solver: pattern databases and a two-phase IDA* search. `app.py` runs it in a subprocess (`cubealgorithm/solve_cli.py`) with a 90-second limit.
- `scanner/` classifies sticker colors and maps a six-face layout onto that cubie state.
- `cube_control/` keeps a virtual cube, parses typed or spoken phrases, and writes move lines to serial.
- `web/` is the React UI. `app.py` serves the Vite build from `web/dist`.

`cube_state.py` is copied at the repository root and in `cubealgorithm/`. The solver subprocess imports the copy inside `cubealgorithm/`. Keep the two files the same.

## Hardware

RUBI X is the sketch in `firmware/rubi_x/rubi_x.ino`. Open that folder in the Arduino IDE and flash it. The up face uses pins 22–24, so the board has to expose those pins. An Arduino Uno does not.

Six stepper drivers, one per face. The sketch comments say the enable pin is TMC2209 style, active low. Each quarter turn sends 400 step pulses. Step delays are microseconds: 120 for a single quarter turn, 90 for a single half turn, and 150 while two motors move together.

| Face | Step | Direction | Enable |
| --- | --- | --- | --- |
| D | 2 | 3 | 4 |
| F | 5 | 6 | 7 |
| B | 8 | 9 | 10 |
| R | 11 | 12 | 13 |
| L | A0 | A1 | A2 |
| U | 22 | 23 | 24 |

All six `DIRECTION_REVERSED` flags in the sketch are currently `true`. Change a flag only when that face turns the wrong way.

Serial is 115200 baud. The sketch reads one line and accepts spaces, commas, or tabs between moves (`R`, `R'`, `R2`). If the next move is the opposite face (`U`/`D`, `F`/`B`, or `R`/`L`), those two run on the same step loop. Any other pair runs one after the other. A line such as `R U` does not run together, because R and U are not opposites.

After a successful line the sketch prints `DONE` and `Robot execution time:` in seconds. That timer wraps the move loop only. Cube Control writes the line and does not read this reply, so the number shows on the serial port rather than in the web page.

- On macOS, prefer a `/dev/cu.*` port over `/dev/tty.*`
- Close the Arduino Serial Monitor before connecting from this app; it holds the port
- The “one move per line” checkbox is browser serial only. Separate lines cannot be paired, because pairing looks at the next move on the same line

The printed parts are from [t33devv/rubik](https://github.com/t33devv/rubik). That project’s README points at a [parts list](https://docs.google.com/spreadsheets/d/11R_L9FSNaaHHE8eK1LpuwcLbCis_kUPEcZf2wtLlFHg/edit?usp=sharing) and a [build video](https://www.youtube.com/watch?v=QUscG2dRllM). It has no license file, so the CAD is not vendored here.

## Setup

Python 3.10 or newer, and Node.js with npm.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cd web && npm install && npm run build && cd ..
```

`requirements.txt` installs NumPy, OpenCV, Kociemba, and pyserial. If `kociemba` cannot be imported, scan solving falls back to the experimental solver.

## Run

```bash
source .venv/bin/activate
python app.py
```

Open http://127.0.0.1:8000 and allow the camera.

While editing the UI, leave `python app.py` running and start the Vite dev server:

```bash
cd web && npm run dev
```

Vite proxies `/api` to port 8000. Use that dev URL, not the built page, while `npm run dev` is running.

An optional command-line demo scrambles a cube and runs only the experimental solver. It can take a long time:

```bash
cd cubealgorithm && python main.py
```

## Controls

### Scanner

The page asks for six faces. Hold the center color toward the camera:

| Step | Center | Neighbor |
| --- | --- | --- |
| 1 | green | white along the top |
| 2 | red | blue along the top |
| 3 | white | blue along the top |
| 4 | orange | blue along the top |
| 5 | yellow | blue along the top |
| 6 | blue | white along the bottom |

The server samples a centered square of the uploaded frame (guide mode). After several stable readings with the expected center color, that face is saved. You can correct a sticker before continuing. Solve on the finished layout posts `/api/solve` and shows the move list. That screen does not write to the Arduino.

### Cube Control

- Voice or the text box: face letters (`R`), `prime` for counterclockwise, `2` or `two` for a half turn, plus `scramble`, `solve`, and `reset`
- Scramble builds a random move list and applies it to the virtual cube
- Solve undoes the last scramble when one is stored. If there is no scramble, it asks Kociemba. It does not call the experimental solver
- Server USB uses pyserial from `app.py`. Browser USB uses the Web Serial API in Chrome
- Connect serial before scramble, solve, or a move. Reset does not require a port

## Tests

```bash
source .venv/bin/activate
python -m pytest
python -m compileall -q app.py cube_state.py cube_control scanner cubealgorithm tests
```

The tests cover color distance, face mapping, cubie conversion, and voice parsing. They do not measure camera accuracy, solver speed, or a physical solve.

## Repository structure

- `app.py` — local HTTP server
- `cube_state.py` — cubie engine used by the server
- `cubealgorithm/` — experimental two-phase solver and its cubie-engine copy
- `scanner/` — color classification, face detection, cubie conversion, Kociemba adapter
- `firmware/rubi_x/` — Arduino sketch for the six face motors
- `cube_control/` — virtual cube, voice parsing, serial output
- `web/src/` — React scanner and Cube Control UI
- `tests/` — pytest
- `templates/index.html` — earlier standalone scanner page; `app.py` does not serve it
- `cubealgorithm/heap_practice.py` — unused scratch script

`web/dist/` is a local Vite build and is not meant to be committed.

## Known limitations

- The experimental solver is not a replacement for Kociemba. No result in this repository shows it is faster or that it returns shorter solutions.
- A scan solve that misses Kociemba can sit until the 90-second subprocess limit.
- The sketch prints robot motion time on serial after each line. This app does not read or store that number, and it is not a solver benchmark.
- `/api/analyze` reads a `mode` field and defaults to `guide`. The React page sends `manual` and `focus` instead, so those fields are ignored. Hand landmarks from MediaPipe are drawn on the overlay; sticker colors still come from the centered guide.
- The scanner hook can switch to a fixed manual square and jump to a scan step, but the current screens do not expose those controls.
- The “one move per line” checkbox affects browser serial only. Server serial always sends one line.
- Color calibration is written to `data/calibration.json` on this machine and is gitignored. There is no published accuracy figure for the camera.
- The two `cube_state.py` files can drift if only one is edited.

## Credits and dependencies

- Cubie engine, experimental two-phase search, scanner, UI, serial glue, and the RUBI X sketch in this repository
- Mechanical models from [t33devv/rubik](https://github.com/t33devv/rubik). Not included here; that repository has no license file
- [Kociemba](https://github.com/muodov/kociemba) (`kociemba`) for fast facelet solutions. The algorithm is Herbert Kociemba’s two-phase method
- CIEDE2000 as described by Sharma, Wu, and Dalal (2005) for sticker distance
- The Lab color-matching approach used by webcam solvers such as [QBR](https://github.com/kkoomen/qbr)
- [OpenCV](https://opencv.org/), NumPy, and pyserial
- React, Vite, and Three.js
- MediaPipe Hand Landmarker, loaded in the browser from Google’s CDN, for the on-screen hand points
