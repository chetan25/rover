import time
from http.client import HTTPConnection
from unittest.mock import MagicMock, patch
from camera.stream import start_stream


def test_stream_server_starts_and_serves_root():
    camera = MagicMock()

    def fake_capture(buf, format):
        buf.write(b"\xff\xd8\xff\xe0" + b"\x00" * 10)

    camera.capture_file.side_effect = fake_capture

    with patch("camera.stream.STREAM_PORT", 18080):
        start_stream(camera)

    time.sleep(0.1)

    conn = HTTPConnection("127.0.0.1", 18080, timeout=2)
    conn.request("GET", "/")
    resp = conn.getresponse()
    assert resp.status == 200
    body = resp.read()
    assert b"<img" in body
    conn.close()
