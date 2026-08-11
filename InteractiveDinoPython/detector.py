from dataclasses import dataclass

import numpy as np
from ultralytics import YOLO


@dataclass
class Detection:
    label: str
    confidence: float
    box: tuple[int, int, int, int]


class ObjectDetector:
    def __init__(
        self,
        model_path: str = "models/yolo11s.pt",
        confidence_threshold: float = 0.45,
    ) -> None:
        print(f"Loading {model_path}...")

        self.model = YOLO(model_path)
        self.confidence_threshold = confidence_threshold

    def detect(self, frame: np.ndarray) -> list[Detection]:
        results = self.model.predict(
            source=frame,
            conf=self.confidence_threshold,
            imgsz=640,
            device="mps",
            verbose=False,
        )

        result = results[0]
        detections: list[Detection] = []

        if result.boxes is None:
            return detections

        for box in result.boxes:
            class_id = int(box.cls.item())
            label = str(result.names[class_id])
            confidence = float(box.conf.item())

            x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())

            detections.append(
                Detection(
                    label=label,
                    confidence=confidence,
                    box=(x1, y1, x2, y2),
                )
            )

        return detections