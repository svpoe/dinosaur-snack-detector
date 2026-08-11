from dataclasses import dataclass
import math

import cv2
import mediapipe as mp
import numpy as np


@dataclass
class HandResult:
    landmarks: list[tuple[int, int]]
    palm_center: tuple[int, int]
    palm_radius: int
    is_open: bool


class HandTracker:
    def __init__(
        self,
        model_path: str = "models/hand_landmarker.task",
        num_hands: int = 1,
        detection_confidence: float = 0.55,
        tracking_confidence: float = 0.55,
    ) -> None:
        base_options = mp.tasks.BaseOptions(model_asset_path=model_path)

        options = mp.tasks.vision.HandLandmarkerOptions(
            base_options=base_options,
            running_mode=mp.tasks.vision.RunningMode.VIDEO,
            num_hands=num_hands,
            min_hand_detection_confidence=detection_confidence,
            min_hand_presence_confidence=detection_confidence,
            min_tracking_confidence=tracking_confidence,
        )

        self.landmarker = mp.tasks.vision.HandLandmarker.create_from_options(options)

        self.frame_timestamp_ms = 0

    def process(
        self,
        frame: np.ndarray,
    ) -> list[HandResult]:
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        rgb_frame = np.ascontiguousarray(rgb_frame)

        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)

        # VIDEO mode requires monotonically increasing timestamps.
        self.frame_timestamp_ms += 33

        result = self.landmarker.detect_for_video(mp_image, self.frame_timestamp_ms)

        frame_height, frame_width = frame.shape[:2]
        hand_results: list[HandResult] = []

        for normalized_landmarks in result.hand_landmarks:
            pixel_landmarks: list[tuple[int, int]] = []

            for landmark in normalized_landmarks:
                x = int(landmark.x * frame_width)
                y = int(landmark.y * frame_height)

                pixel_landmarks.append((x, y))

            palm_center = self._calculate_palm_center(pixel_landmarks)
            palm_radius = self._calculate_palm_radius(pixel_landmarks, palm_center)

            hand_results.append(
                HandResult(
                    landmarks=pixel_landmarks,
                    palm_center=palm_center,
                    palm_radius=palm_radius,
                    is_open=self._is_open_palm(pixel_landmarks),
                )
            )

        return hand_results

    @staticmethod
    def _distance(
        point_a: tuple[int, int],
        point_b: tuple[int, int],
    ) -> float:
        return math.hypot(point_a[0] - point_b[0], point_a[1] - point_b[1])

    def _calculate_palm_center(
        self,
        landmarks: list[tuple[int, int]],
    ) -> tuple[int, int]:
        # Wrist and the four finger-base landmarks.
        palm_indices = [0, 5, 9, 13, 17]

        center_x = int(sum(landmarks[index][0] for index in palm_indices) / len(palm_indices))
        center_y = int(sum(landmarks[index][1] for index in palm_indices) / len(palm_indices))

        return center_x, center_y

    def _calculate_palm_radius(
        self,
        landmarks: list[tuple[int, int]],
        palm_center: tuple[int, int],
    ) -> int:
        palm_indices = [0, 5, 9, 13, 17]

        distances = [
            self._distance(palm_center, landmarks[index])
            for index in palm_indices
        ]

        # Make the region slightly larger than the anatomical palm.
        return max(30, int(max(distances) * 1.5))

    def _is_open_palm(
        self,
        landmarks: list[tuple[int, int]],
    ) -> bool:
        wrist = landmarks[0]

        # Fingertip and middle-joint indices.
        finger_pairs = [
            (8, 6),    # Index
            (12, 10),  # Middle
            (16, 14),  # Ring
            (20, 18),  # Little
        ]

        extended_fingers = 0

        for tip_index, joint_index in finger_pairs:
            tip_distance = self._distance(wrist, landmarks[tip_index])
            joint_distance = self._distance(wrist, landmarks[joint_index])

            if tip_distance > joint_distance * 1.12:
                extended_fingers += 1

        return extended_fingers >= 3

    def close(self) -> None:
        self.landmarker.close()