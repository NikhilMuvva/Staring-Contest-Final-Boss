# Staring Contest Final Boss

Staring Contest Final Boss is a webcam-based blink detection game prototype. It uses a computer vision camera feed to detect when a player blinks and includes survival and rhythm game modes.

## Current Features

- Basic webcam test using OpenCV.
- Shared `BlinkInput` module used by both game modes.
- MediaPipe Face Mesh landmarks and an Eye Aspect Ratio-style openness score.
- Adaptive open-eye calibration, smoothing, a blink state machine, and cooldown.
- Safe pause/status behavior when no face is found.
- Survival mode with timer, pause when the face leaves the camera, and game over on blink.
- Rhythm mode where either a real blink or SPACE hits a note.
- Single exhibit launcher with a main menu, instructions, calibration before play, and return-to-menu flow.
- Username input for the current player.
- Local leaderboard saved in `leaderboard.json`.
- Survival and rhythm best scores saved locally.
- Software-only challenge effects in survival mode.
- Debug controls for blink detection testing.

## Planned Features

- Stare zones where players must avoid blinking.
- Arduino-connected exhibit effects.
- LED effects.
- Buzzer or simple sound feedback.
- Optional low-power fan breeze effect.
- Open Sauce exhibit setup with clearer instructions and show-ready controls.

## How It Works

The shared `blink_input.py` module opens the webcam and uses MediaPipe Face Landmarker/Face Mesh landmarks to track one face. It combines both eyes into an Eye Aspect Ratio-style openness score.

During calibration, the player keeps their eyes open for about three seconds. The detector learns their normal open-eye value and sets an adaptive threshold below it. During play, exponential smoothing, hysteresis, minimum/maximum closed-frame limits, and a cooldown state reject noise and ensure a full blink produces only one event. Losing face tracking never counts as a blink.

The detector design is inspired by MediaPipe Face Mesh and adaptive Eye Aspect Ratio blink detection approaches.

## Setup

Create and activate a virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install dependencies:

```powershell
pip install -r requirements.txt
```

If you are not using a virtual environment, you can install directly:

```powershell
pip install pygame opencv-python mediapipe numpy
```

## Run

Test the webcam:

```powershell
python camera_test.py
```

Run the standalone blink detector test:

```powershell
python blink_input.py
```

Run the full exhibit app:

```powershell
python main.py
```

Run survival mode:

```powershell
python survival_mode.py
```

Run rhythm mode:

```powershell
python rhythm_mode.py
```

Keep your eyes open during each calibration. Press `Q` to quit the standalone blink test. SPACE remains a backup blink/hit input in both game modes.

## Project Structure

- `camera_test.py` - Simple OpenCV webcam test.
- `main.py` - Simple exhibit launcher with mode select and instructions.
- `blink_input.py` - Shared webcam, calibration, and advanced blink-event input.
- `survival_mode.py` - Current playable survival game mode.
- `rhythm_mode.py` - Playable blink rhythm game mode.
- `leaderboard.json` - Local saved survival times and rhythm scores by username.
- `requirements.txt` - Python package dependencies.
- `face_landmarker.task` - MediaPipe model file. The code can download this if it is missing.

## Safety Note

Future fan or bright-light effects will be kept low-power, optional, and not aimed directly into players' eyes. Any physical exhibit effects should be tested carefully and designed so players can opt out.

## Status

This is an early prototype. Survival mode, rhythm mode, and shared blink input are working; physical exhibit effects remain future work.

## Team

Built by our team for an Open Sauce exhibit application.
