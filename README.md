# Staring Contest Final Boss

Staring Contest Final Boss is a webcam-based blink detection game prototype. It uses a computer vision camera feed to detect when a player blinks and currently includes a simple survival mode where the goal is to keep your eyes open as long as possible.

## Current Features

- Basic webcam test using OpenCV.
- Reusable blink detection module using OpenCV and MediaPipe Face Landmarker.
- Eye openness detection from face landmarks.
- Optional MediaPipe blendshape blink signals when available.
- Calibration flow before survival mode starts.
- Survival mode with timer, pause when the face leaves the camera, and game over on blink.
- Username input for the current player.
- Local leaderboard saved in `leaderboard.json`.
- In-game menu with start, leaderboard, and quit options.
- Software-only challenge effects in survival mode.
- Debug controls for blink detection testing.

## Planned Features

- Rhythm mode where players blink on beat.
- Stare zones where players must avoid blinking.
- Arduino-connected exhibit effects.
- LED effects.
- Buzzer or simple sound feedback.
- Optional low-power fan breeze effect.
- Open Sauce exhibit setup with clearer instructions and show-ready controls.

## How It Works

The game opens a webcam feed with OpenCV. MediaPipe Face Landmarker tracks one face and estimates eye openness from face landmarks. The blink detector can also use MediaPipe face blendshape scores, such as `eyeBlinkLeft` and `eyeBlinkRight`, when they are available.

During calibration, the player keeps their eyes open and then blinks slowly a few times. The program uses those values to choose a blink threshold. During the game, the detector smooths recent eye readings and counts a blink when the closed-eye signal is strong enough for multiple frames.

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
pip install opencv-python mediapipe
```

## Run

Test the webcam:

```powershell
python camera_test.py
```

Run the standalone blink detector test:

```powershell
python blink_detector.py
```

Run survival mode:

```powershell
python survival_mode.py
```

## Project Structure

- `camera_test.py` - Simple OpenCV webcam test.
- `blink_detector.py` - Reusable blink detection and calibration code.
- `survival_mode.py` - Current playable survival game mode.
- `leaderboard.json` - Local saved best times by username.
- `requirements.txt` - Python package dependencies.
- `face_landmarker.task` - MediaPipe model file. The code can download this if it is missing.

## Safety Note

Future fan or bright-light effects will be kept low-power, optional, and not aimed directly into players' eyes. Any physical exhibit effects should be tested carefully and designed so players can opt out.

## Status

This is an early prototype. Survival mode and blink detection are working, but rhythm mode and Arduino effects are planned features, not finished parts of the project yet.

## Team

Built by our team for an Open Sauce exhibit application.
