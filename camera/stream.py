import io
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from config import STREAM_PORT

_WEB_DIR = Path(__file__).parent.parent / "web"


class _StreamHandler(BaseHTTPRequestHandler):
    camera = None
    camera_lock = None

    def do_GET(self):
        if self.path == "/":
            self._serve_index()
        elif self.path == "/stream":
            self._serve_mjpeg()

    def _serve_index(self):
        html = (_WEB_DIR / "index.html").read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        self.wfile.write(html)

    def _serve_mjpeg(self):
        self.send_response(200)
        self.send_header("Content-Type", "multipart/x-mixed-replace; boundary=frame")
        self.end_headers()
        try:
            while True:
                buf = io.BytesIO()
                with _StreamHandler.camera_lock:
                    _StreamHandler.camera.capture_file(buf, format="jpeg")
                frame = buf.getvalue()
                self.wfile.write(b"--frame\r\n")
                self.wfile.write(b"Content-Type: image/jpeg\r\n\r\n")
                self.wfile.write(frame)
                self.wfile.write(b"\r\n")
        except Exception:
            pass

    def log_message(self, *args):
        pass


def start_stream(camera, camera_lock=None):
    _StreamHandler.camera = camera
    _StreamHandler.camera_lock = camera_lock or threading.Lock()
    server = HTTPServer(("0.0.0.0", STREAM_PORT), _StreamHandler)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    print(f"[Stream] FPV at http://rover.local:{STREAM_PORT}")
