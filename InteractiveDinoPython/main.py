import time

import cv2

from detector import Detection, ObjectDetector
from hand_tracker import HandResult, HandTracker
from udp_sender import UnitySender


HAND_CONNECTIONS = [
    (0, 1),
    (1, 2),
    (2, 3),
    (3, 4),
    (0, 5),
    (5, 6),
    (6, 7),
    (7, 8),
    (5, 9),
    (9, 10),
    (10, 11),
    (11, 12),
    (9, 13),
    (13, 14),
    (14, 15),
    (15, 16),
    (13, 17),
    (17, 18),
    (18, 19),
    (19, 20),
    (0, 17),
]

#methods for bounding box and hand drawing, distance calculation, and object selection based on hand position

def draw_detection(
    frame,
    detection: Detection,
    is_presented: bool = False,
) -> None:
    x1, y1, x2, y2 = detection.box

    color = (0, 255, 255) if is_presented else (0, 255, 0)

    thickness = 4 if is_presented else 2

    cv2.rectangle(frame, (x1, y1), (x2, y2), color, thickness)

    text = f"{detection.label}: {detection.confidence:.2f}"
    cv2.putText(frame, text, (x1, max(y1 - 10, 25)), cv2.FONT_HERSHEY_SIMPLEX, 0.65, color, 2)


def draw_hand(
    frame,
    hand: HandResult,
) -> None:
    line_color = (0, 255, 0) if hand.is_open else (0, 165, 255)

    for start_index, end_index in HAND_CONNECTIONS:
        cv2.line(frame, hand.landmarks[start_index], hand.landmarks[end_index], line_color, 2)

    for landmark in hand.landmarks:
        cv2.circle(frame, landmark, 4, (255, 0, 255), -1)

    # cv2.circle(frame, hand.palm_center, hand.palm_radius, line_color, 2)
    # cv2.circle(frame, hand.palm_center, 7, (255, 255, 0), -1)

    status = "OPEN PALM" if hand.is_open else "HAND CLOSED"
    text_pos = (hand.palm_center[0] - 70, hand.palm_center[1] - hand.palm_radius - 15)
    cv2.putText(frame, status, text_pos, cv2.FONT_HERSHEY_SIMPLEX, 0.7, line_color, 2)


def point_inside_box(
    point: tuple[int, int],
    box: tuple[int, int, int, int],
) -> bool:
    point_x, point_y = point
    x1, y1, x2, y2 = box

    return x1 <= point_x <= x2 and y1 <= point_y <= y2


def box_center(
    box: tuple[int, int, int, int],
) -> tuple[int, int]:
    x1, y1, x2, y2 = box
    return int((x1 + x2) / 2), int((y1 + y2) / 2)


def squared_distance(
    point_a: tuple[int, int],
    point_b: tuple[int, int],
) -> float:
    return (point_a[0] - point_b[0]) ** 2 + (point_a[1] - point_b[1]) ** 2


def calculate_turn_degrees(
    detection: Detection,
    frame_width: int,
) -> float:
    object_center_x, _ = box_center(detection.box)
    screen_center_x = frame_width / 2
    offset_x = object_center_x - screen_center_x

    if frame_width <= 0:
        return 0.0

    max_turn_degrees = 60.0
    normalized_offset = offset_x / (frame_width / 2)

    return max(-max_turn_degrees, min(max_turn_degrees, normalized_offset * max_turn_degrees))


#check if the detected object is near the palm of the hand
def object_is_near_palm(
    detection: Detection,
    hand: HandResult,
) -> bool:
    object_center = box_center(detection.box)
    distance_squared = squared_distance(object_center, hand.palm_center)

    expanded_radius = hand.palm_radius * 2.2
    center_is_near = distance_squared <= expanded_radius**2
    palm_center_inside_object = point_inside_box(hand.palm_center, detection.box)
    return center_is_near or palm_center_inside_object


def select_presented_object(
    detections: list[Detection],
    hands: list[HandResult],
) -> tuple[Detection, HandResult, float] | None:
    candidates: list[tuple[float, Detection, HandResult, float]] = []

    for hand in hands:
        if not hand.is_open:
            continue

        for detection in detections:
            if detection.label == "person":
                continue

            if not object_is_near_palm(detection, hand):
                continue

            center_distance = squared_distance(box_center(detection.box), hand.palm_center)

            score = detection.confidence * 100_000 - center_distance
            candidates.append((score, detection, hand, 0.0))

    if not candidates:
        return None

    _, best_detection, best_hand, best_turn_degrees = max(
        candidates,
        key=lambda item: item[0],
    )

    return best_detection, best_hand, best_turn_degrees


def main() -> None:
    detector = ObjectDetector(model_path="models/yolo11s.pt", confidence_threshold=0.40)
    hand_tracker = HandTracker(model_path="models/hand_landmarker.task")

    sender = UnitySender()

    camera = cv2.VideoCapture(0)

    if not camera.isOpened():
        hand_tracker.close()
        sender.close()
        raise RuntimeError("Could not open the webcam.")

    candidate_label: str | None = None
    candidate_frames = 0

    required_frames = 5
    cooldown_seconds = 3.0
    last_trigger_time = 0.0

    print("YOLO11s + MediaPipe started.")
    print("Present an object near an open palm.")
    print("Press Q to quit.")

    try:
        while True:
            success, frame = camera.read()

            if not success:
                print("Could not read webcam frame.")
                break

            frame = cv2.flip(frame, 1)
            _, frame_width = frame.shape[:2]

            detections = detector.detect(frame)
            hands = hand_tracker.process(frame)

            presented_selection = select_presented_object(detections, hands)

            presented_object = None
            presented_hand = None
            presented_turn_degrees = 0.0

            if presented_selection is not None:
                presented_object, presented_hand, presented_turn_degrees = presented_selection
                presented_turn_degrees = -1*calculate_turn_degrees(
                    presented_object,
                    frame_width,
                )

            if presented_object is not None:
                draw_detection(frame, presented_object, is_presented=True)

            for hand in hands:
                draw_hand(frame, hand)

            if presented_object is None:
                candidate_label = None
                candidate_frames = 0

            elif presented_object.label == candidate_label:
                candidate_frames += 1

            else:
                candidate_label = presented_object.label
                candidate_frames = 1

            if presented_object is not None:
                cv2.putText(
                    frame,
                    f"PRESENTED: {presented_object.label}",
                    (20, 40),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.9,
                    (0, 255, 255),
                    3,
                )

                cv2.putText(
                    frame,
                    f"Stable frames: {candidate_frames}/{required_frames}",
                    (20, 75),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    (0, 255, 255),
                    2,
                )

            else:
                cv2.putText(
                    frame,
                    "Show an object on an open palm",
                    (20, 40),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.8,
                    (0, 165, 255),
                    2,
                )

            now = time.time()

            stable_object = presented_object is not None and candidate_frames >= required_frames
            cooldown_finished = now - last_trigger_time >= cooldown_seconds

            if stable_object and cooldown_finished:
                label = presented_object.label

                print(
                    "Recognized presented object: "
                    f"{label} "
                    f"({presented_object.confidence:.2f})"
                )

                turn_degrees = presented_turn_degrees

                sender.send_object(label, turn_degrees)

                last_trigger_time = now
                candidate_frames = 0

            cv2.imshow("Interactive Dinosaur Vision", frame)

            key = cv2.waitKey(1) & 0xFF

            if key == ord("q"):
                break

    finally:
        camera.release()
        hand_tracker.close()
        sender.close()
        cv2.destroyAllWindows()

    required_frames = 5
if __name__ == "__main__":
    main()