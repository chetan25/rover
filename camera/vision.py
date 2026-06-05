import base64
import io
import threading
import time
import anthropic
from config import CLAUDE_API_KEY, CLAUDE_MODEL, VISION_INTERVAL_SEC


class ClaudeVision:
    """
    Captures a JPEG from the shared camera every VISION_INTERVAL_SEC seconds,
    sends it to Claude, and writes the description to the LCD display.

    Accepts an existing camera instance (and optional lock) so it can share
    the single Picamera2 instance with the FPV stream server.
    """

    def __init__(self, lcd, camera, camera_lock=None):
        self.lcd = lcd
        self.camera = camera
        self.camera_lock = camera_lock or threading.Lock()
        self.client = anthropic.Anthropic(api_key=CLAUDE_API_KEY)
        self.model = CLAUDE_MODEL
        self.running = False

    def _capture_jpeg(self) -> bytes:
        buf = io.BytesIO()
        with self.camera_lock:
            self.camera.capture_file(buf, format="jpeg")
        return buf.getvalue()

    def _describe(self, image_bytes: bytes) -> str:
        b64 = base64.standard_b64encode(image_bytes).decode("utf-8")
        response = self.client.messages.create(
            model=self.model,
            max_tokens=60,
            messages=[{
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/jpeg",
                            "data": b64,
                        },
                    },
                    {
                        "type": "text",
                        "text": (
                            "You are the eyes of a small robot rover exploring a home. "
                            "Describe what you see in ONE short sentence, max 12 words. "
                            "Be playful and curious. Start with 'I see' or 'I spot'."
                        ),
                    },
                ],
            }],
        )
        return response.content[0].text.strip()

    def run_loop(self):
        self.running = True
        while self.running:
            try:
                image_bytes = self._capture_jpeg()
                description = self._describe(image_bytes)
                words = description.split()
                line1 = " ".join(words[:8])[:16]
                line2 = " ".join(words[8:])[:16]
                self.lcd.write(line1, line2)
                print(f"[Claude Vision] {description}")
            except Exception as e:
                print(f"[Claude Vision] Error: {e}")
            time.sleep(VISION_INTERVAL_SEC)

    def start(self):
        t = threading.Thread(target=self.run_loop, daemon=True)
        t.start()

    def stop(self):
        self.running = False
