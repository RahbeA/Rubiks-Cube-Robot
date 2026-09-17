import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from cube_state import CubeState


HOST = "127.0.0.1"
PORT = 8000
INDEX_PATH = Path(__file__).parent / "templates" / "index.html"
current_state = CubeState.solved()


def state_payload(state):
    return {
        "corner_permutation": state.corner_permutation,
        "corner_orientation": state.corner_orientation,
        "edge_permutation": state.edge_permutation,
        "edge_orientation": state.edge_orientation,
        "solved": state.is_solved(),
        "valid": state.is_valid(),
    }


class CubeRequestHandler(BaseHTTPRequestHandler):
    def send_json(self, payload, status=200):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/api/state":
            self.send_json(state_payload(current_state))
            return
        if self.path == "/":
            body = INDEX_PATH.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        self.send_error(404)

    def do_POST(self):
        global current_state
        if self.path == "/api/reset":
            current_state = CubeState.solved()
            self.send_json(state_payload(current_state))
            return
        if self.path != "/api/move":
            self.send_error(404)
            return

        try:
            content_length = int(self.headers.get("Content-Length", "0"))
            data = json.loads(self.rfile.read(content_length) or b"{}")
            move = data.get("move", "")
            current_state = current_state.apply_move(move)
        except (json.JSONDecodeError, KeyError, ValueError, IndexError, AttributeError):
            self.send_json({"error": "Invalid move"}, status=400)
            return
        self.send_json(state_payload(current_state))

    def log_message(self, format, *args):
        return


if __name__ == "__main__":
    print(f"Cube visualizer running at http://{HOST}:{PORT}")
    ThreadingHTTPServer((HOST, PORT), CubeRequestHandler).serve_forever()
