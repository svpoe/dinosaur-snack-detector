import json
import socket


class UnitySender:
    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 5052,
    ) -> None:
        self.address = (host, port)
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        print(f"UDP sender targeting {host}:{port}")

    def send_object(
        self,
        label: str,
        turn_degrees: float,
    ) -> None:
        message = {
            "label": label,
            "turnDegrees": turn_degrees,
        }
        data = json.dumps(message).encode("utf-8")
        self.socket.sendto(data, self.address)
        print(f"Sent UDP JSON: {data.decode('utf-8')}")

    def close(self) -> None:
        self.socket.close()