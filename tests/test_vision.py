import threading
from unittest.mock import MagicMock, patch
from camera.vision import ClaudeVision


def make_vision():
    lcd = MagicMock()
    camera = MagicMock()
    client = MagicMock()
    client.messages.create.return_value.content = [
        MagicMock(text="I see a cozy living room sofa.")
    ]
    vision = ClaudeVision(lcd=lcd, camera=camera)
    vision.client = client
    return vision, lcd, camera, client


def test_capture_jpeg_uses_provided_camera():
    vision, lcd, camera, client = make_vision()

    def fake_capture(stream, format):
        stream.write(b"FAKE_JPEG_DATA")

    camera.capture_file.side_effect = fake_capture
    result = vision._capture_jpeg()
    assert result == b"FAKE_JPEG_DATA"


def test_describe_calls_claude_with_base64_image():
    vision, lcd, camera, client = make_vision()
    vision._describe(b"FAKE_JPEG")
    assert client.messages.create.called
    call_kwargs = client.messages.create.call_args.kwargs
    assert call_kwargs["model"] == vision.model
    content = call_kwargs["messages"][0]["content"]
    image_block = content[0]
    assert image_block["type"] == "image"
    assert image_block["source"]["type"] == "base64"


def test_describe_returns_stripped_text():
    vision, lcd, camera, client = make_vision()
    client.messages.create.return_value.content = [
        MagicMock(text="  I see a red chair.  ")
    ]
    assert vision._describe(b"data") == "I see a red chair."


def test_run_loop_writes_description_to_lcd():
    vision, lcd, camera, client = make_vision()
    vision._capture_jpeg = MagicMock(return_value=b"img")
    vision._describe = MagicMock(return_value="I see a bright kitchen window")
    vision.running = True

    def stop_after_one(l1, l2=""):
        vision.running = False

    lcd.write.side_effect = stop_after_one

    with patch("time.sleep"):
        vision.run_loop()

    lcd.write.assert_called()


def test_run_loop_continues_on_error():
    vision, lcd, camera, client = make_vision()
    vision._capture_jpeg = MagicMock(side_effect=[Exception("camera fail"), b"img"])
    vision._describe = MagicMock(return_value="I see something")

    def stop_after_one(l1, l2=""):
        vision.running = False

    lcd.write.side_effect = stop_after_one
    vision.running = True

    with patch("time.sleep"):
        vision.run_loop()  # must not raise
