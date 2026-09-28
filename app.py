import base64
import json
import mimetypes
import sys
import threading
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import cv2
import numpy as np

from cube_state import corner_dictionary, edge_dictionary
from scanner.colors import COLOR_TO_FACE, DISPLAY_HEX, FACE_ORDER, FACE_TO_COLOR, ColorClassifier
from scanner.detect import (
    STATUS_ALIGN,
    STATUS_HOLD,
    STABILITY_FRAMES,
    DetectionState,
    draw_debug_overlay,
    get_cube_roi,
    read_cube,
)
from scanner.cubie_convert import colored_faces_to_cube_state
from scanner.mapper import SCAN_GUIDE, SCAN_STEPS, facelet_string, layout_report
from scanner.solve_service import run_two_phase_solver, warm_solver_worker

HOST = "127.0.0.1"
PORT = 8000
ROOT = Path(__file__).parent
WEB_DIST = ROOT / "web" / "dist"
CALIBRATION_PATH = ROOT / "data" / "calibration.json"

classifier = ColorClassifier.from_path(CALIBRATION_PATH)
faces: dict[str, list[str]] = {}
tracker = DetectionState()
scan_mode = "guide"
DEBUG_DIR = ROOT / "data" / "debug"
_solve_lock = threading.Lock()


def decode_image(data_url: str) -> np.ndarray:
    if "," in data_url:
        data_url = data_url.split(",", 1)[1]
    raw = base64.b64decode(data_url)
    array = np.frombuffer(raw, dtype=np.uint8)
    image = cv2.imdecode(array, cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError("Could not decode image")
    return image


def save_debug_capture(frame: np.ndarray, mode: str) -> dict:
    """Write the guide, outline, warped face, and sample boxes for one capture."""
    DEBUG_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    reading = read_cube(frame, classifier, mode=mode, state=DetectionState(), debug=True)
    roi, origin = get_cube_roi(frame)
    selected = None
    overlay = draw_debug_overlay(frame, (*origin, origin[2]), selected, [], origin[:2])
    cv2.rectangle(
        overlay,
        (origin[0], origin[1]),
        (origin[0] + origin[2], origin[1] + origin[2]),
        (230, 230, 230),
        2,
    )
    paths = {
        "frame": DEBUG_DIR / f"{stamp}-frame.jpg",
        "roi": DEBUG_DIR / f"{stamp}-roi.jpg",
        "overlay": DEBUG_DIR / f"{stamp}-overlay.jpg",
    }
    cv2.imwrite(str(paths["frame"]), frame)
    cv2.imwrite(str(paths["roi"]), roi)
    cv2.imwrite(str(paths["overlay"]), overlay)
    warped_path = ""
    if reading.get("warped"):
        encoded = reading["warped"].split(",", 1)[1]
        warped_path = DEBUG_DIR / f"{stamp}-warped.jpg"
        warped_path.write_bytes(base64.b64decode(encoded))
    print(f"Captured {mode} face {stamp}")
    for index, sticker in enumerate(reading.get("stickers") or []):
        print(
            f"  {index} {sticker['color']} bgr={sticker['bgr']} lab={sticker['lab']} dE={sticker['delta_e']}"
        )
    return {
        "files": [str(path.relative_to(ROOT)) for path in paths.values() if path.exists()],
        "warped": str(warped_path.relative_to(ROOT)) if warped_path else "",
        "stickers": reading.get("stickers") or [],
    }


def serialize_faces() -> dict:
    report = layout_report(faces)
    payload = {
        "faces": faces,
        "guide": SCAN_GUIDE,
        "steps": SCAN_STEPS,
        "colors": FACE_TO_COLOR,
        "display": DISPLAY_HEX,
        "order": list(FACE_ORDER),
        "report": report,
        "state": None,
        "facelets": None,
        "cubies": None,
    }
    if report["complete"]:
        try:
            state = colored_faces_to_cube_state(faces)
        except ValueError as error:
            # Keep the captured faces so one face can be rescanned. Do not
            # attach a CubeState, and do not hand this layout to a solver.
            payload["report"]["issues"] = payload["report"]["issues"] + [str(error)]
            payload["report"]["valid_layout"] = False
        else:
            payload["facelets"] = facelet_string(faces)
            payload["state"] = {
                "corner_permutation": state.corner_permutation,
                "corner_orientation": state.corner_orientation,
                "edge_permutation": state.edge_permutation,
                "edge_orientation": state.edge_orientation,
                "solved": state.is_solved(),
                "valid": state.is_valid(),
            }
            payload["cubies"] = {
                "corners": [
                    {
                        "slot": corner_dictionary[i],
                        "piece": corner_dictionary[state.corner_permutation[i]],
                        "orientation": state.corner_orientation[i],
                    }
                    for i in range(8)
                ],
                "edges": [
                    {
                        "slot": edge_dictionary[i],
                        "piece": edge_dictionary[state.edge_permutation[i]],
                        "orientation": state.edge_orientation[i],
                    }
                    for i in range(12)
                ],
            }
    return payload


class Handler(BaseHTTPRequestHandler):
    def send_json(self, payload, status=200):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def read_json(self):
        length = int(self.headers.get("Content-Length", "0"))
        return json.loads(self.rfile.read(length) or b"{}")

    def send_bytes(self, body: bytes, content_type: str, cache: str):
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", cache)
        self.end_headers()
        self.wfile.write(body)

    def serve_web(self, path: str):
        root = WEB_DIST.resolve()
        if not root.is_dir():
            message = b"UI build is missing. In the web folder, run npm install and npm run build, then restart this server."
            self.send_bytes(message, "text/plain; charset=utf-8", "no-store")
            return
        relative = "index.html" if path == "/" else path.lstrip("/")
        target = (root / relative).resolve()
        if not target.is_relative_to(root) or not target.is_file():
            self.send_error(404)
            return
        content_type = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
        cache = "no-store" if target.suffix == ".html" else "public, max-age=31536000"
        self.send_bytes(target.read_bytes(), content_type, cache)

    def do_GET(self):
        path = self.path.split("?", 1)[0]
        if path == "/api/layout":
            self.send_json(serialize_faces())
            return
        if path.startswith("/api/"):
            self.send_error(404)
            return
        self.serve_web(path)

    def do_POST(self):
        global faces, classifier, scan_mode
        try:
            data = self.read_json()
        except json.JSONDecodeError:
            self.send_json({"error": "Invalid JSON"}, status=400)
            return

        if self.path == "/api/reset":
            faces = {}
            tracker.reset()
            scan_mode = "guide"
            self.send_json(serialize_faces())
            return

        if self.path == "/api/analyze":
            try:
                image = decode_image(data["image"])
                mode = data.get("mode", "guide")
                if mode not in ("guide", "auto"):
                    mode = "guide"
                if mode != scan_mode:
                    tracker.reset()
                    scan_mode = mode
                result = read_cube(
                    image,
                    classifier,
                    mode=mode,
                    state=tracker,
                    debug=bool(data.get("debug")),
                )
            except (KeyError, ValueError) as error:
                self.send_json({"error": str(error)}, status=400)
                return
            self.send_json(result)
            return

        if self.path == "/api/capture":
            if tracker.count < STABILITY_FRAMES:
                self.send_json(
                    {
                        "ok": False,
                        "warning": "Hold the cube steady inside the guide before capturing.",
                        "status": STATUS_ALIGN if tracker.count == 0 else STATUS_HOLD,
                    },
                    status=409,
                )
                return
            try:
                image = decode_image(data["image"])
            except (KeyError, ValueError) as error:
                self.send_json({"error": str(error)}, status=400)
                return
            bundle = save_debug_capture(image, scan_mode)
            self.send_json({"ok": True, "status": "Cube stable — press Space to capture", **bundle})
            return

        if self.path == "/api/clear":
            face = data.get("face")
            if face in faces:
                del faces[face]
            self.send_json(serialize_faces())
            return

        if self.path == "/api/commit":
            face = data.get("face")
            stickers = data.get("stickers")
            if face not in FACE_ORDER or not isinstance(stickers, list) or len(stickers) != 9:
                self.send_json({"error": "Need a face and 9 stickers"}, status=400)
                return
            colors = []
            for sticker in stickers:
                if sticker in COLOR_TO_FACE:
                    colors.append(sticker)
                elif sticker in FACE_TO_COLOR:
                    colors.append(FACE_TO_COLOR[sticker])
                else:
                    self.send_json({"error": f"Unknown color {sticker}"}, status=400)
                    return
            faces[face] = colors
            center = colors[4]
            labs = data.get("labs")
            if isinstance(labs, list) and len(labs) == 9:
                classifier.learn(center, np.array(labs[4], dtype=np.float64))
                classifier.save(CALIBRATION_PATH)
            self.send_json(serialize_faces())
            return

        if self.path == "/api/solve":
            state = data.get("state") or serialize_faces().get("state")
            if not state:
                self.send_json({"error": "Scan a valid cube before solving."}, status=400)
                return
            layout_faces = data.get("faces") or faces
            try:
                with _solve_lock:
                    result = run_two_phase_solver(state, faces=layout_faces or None)
            except ValueError as error:
                self.send_json({"error": str(error)}, status=400)
                return
            self.send_json(result)
            return

        if self.path == "/api/correct":
            face = data.get("face")
            index = data.get("index")
            color = data.get("color")
            if face not in faces or not isinstance(index, int) or not (0 <= index < 9):
                self.send_json({"error": "Unknown sticker"}, status=400)
                return
            if color in COLOR_TO_FACE:
                faces[face][index] = color
            elif color in FACE_TO_COLOR:
                faces[face][index] = FACE_TO_COLOR[color]
            else:
                self.send_json({"error": f"Unknown color {color}"}, status=400)
                return
            self.send_json(serialize_faces())
            return

        self.send_error(404)

    def log_message(self, format, *args):
        return


if __name__ == "__main__":
    print(f"Cube scanner running at http://{HOST}:{PORT}")
    try:
        print("Loading two-phase solver (first time may take a few seconds)...")
        warm_solver_worker()
        print("Solver ready.")
    except Exception as error:
        print(f"Warning: solver worker failed to start: {error}", file=sys.stderr)
    ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()
