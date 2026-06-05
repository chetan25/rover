import threading
import asyncio
import websockets
from config import DRIVE_SPEED, TURN_SPEED

MANUAL_WS_PORT = 8081


class ManualMode:
    def __init__(self, motors):
        self.motors = motors

    def _handle_command(self, cmd: str):
        dispatch = {
            "forward":  lambda: self.motors.forward(DRIVE_SPEED),
            "backward": lambda: self.motors.backward(DRIVE_SPEED),
            "left":     lambda: self.motors.turn_left(TURN_SPEED),
            "right":    lambda: self.motors.turn_right(TURN_SPEED),
            "stop":     self.motors.stop,
        }
        action = dispatch.get(cmd)
        if action:
            action()

    async def _handler(self, websocket):
        async for message in websocket:
            self._handle_command(message.strip())

    def start(self):
        async def _serve():
            async with websockets.serve(self._handler, "0.0.0.0", MANUAL_WS_PORT):
                await asyncio.Future()

        def _run():
            asyncio.run(_serve())

        t = threading.Thread(target=_run, daemon=True)
        t.start()
        print(f"[Manual] WebSocket on ws://rover.local:{MANUAL_WS_PORT}")
