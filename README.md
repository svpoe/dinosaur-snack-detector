# ECaurus

Feed the dinosaur objects in an open palm and it will walk towards you. It will find the direction you are on the screen and move accordingly. 

Works via  python computer vision pipeline that detects objects and hand gestures, then sends the result to Unity over UDP. 

![Dinosaur Snack Detector demo](demo/dino-demo.gif)

When the palm is open, detection is activated. When the palm is closed, the dinosaur knows it is not being fed.
#![Dinosaur Snack Detector demo](demo/open-closed-palm.png)
<img src="demo/open-closed-palm.png" width="600">

## How it works

1. **Python** captures webcam frames and runs two models in parallel:
   - **YOLO11s** — detects objects in the frame
   - **MediaPipe Hand Landmarker** — tracks hand pose and detects open palms
2. When an object is near an open palm for 5 consecutive frames, it is considered "presented"
3. The label and horizontal offset (turn degrees) are sent as a JSON UDP packet to Unity
4. **Unity** receives the packet, and the dinosaur turns toward the object and reacts

## Project structure

```
InteractiveDinoPython/   # Python vision pipeline
  main.py                # Entry point — webcam loop, drawing, selection logic
  detector.py            # YOLO object detection wrapper
  hand_tracker.py        # MediaPipe hand tracking wrapper
  udp_sender.py          # Sends JSON over UDP to Unity
  models/                # Model files (not committed — see below)

Assets/Scripts/          # Unity C# scripts
  DetectionReceiver.cs   # Listens on UDP port 5052, dispatches messages
  DinosaurReaction.cs    # Animates the dinosaur's turn and reaction
```

## Setup

### Python

Requires Python 3.11 and a webcam. Runs on Apple Silicon (uses MPS device).

```bash
cd InteractiveDinoPython
conda create -n dino-env python=3.11
conda activate dino-env
pip install -r requirements.txt
```

Download the model files and place them in `InteractiveDinoPython/models/`:
- `yolo11s.pt` — [Ultralytics YOLO11s](https://docs.ultralytics.com/models/yolo11/)
- `hand_landmarker.task` — [MediaPipe Hand Landmarker](https://ai.google.dev/edge/mediapipe/solutions/vision/hand_landmarker#models)

### Unity

Open the project in Unity (6000.x or later). The `DetectionReceiver` component listens on UDP port `5052` on localhost. Hit Play while the Python script is running.

## Running

```bash
cd InteractiveDinoPython
python main.py
```

Press **Q** to quit. A 3-second cooldown prevents repeated triggers.

## UDP message format

```json
{ "label": "cup", "turnDegrees": -24.5 }
```

`turnDegrees` is clamped to ±60° and represents the horizontal offset of the detected object from screen center.
