<div align="center">

# 👁️ Staring Contest Final Boss

### A webcam-powered blink game where your eyes become the controller.

![Status](https://img.shields.io/badge/status-prototype-ffcc00)
![Python](https://img.shields.io/badge/python-3.x-3776AB?logo=python&logoColor=white)
![OpenCV](https://img.shields.io/badge/OpenCV-webcam-5C3EE8?logo=opencv&logoColor=white)
![MediaPipe](https://img.shields.io/badge/MediaPipe-face%20mesh-00A6FF)
![Pygame](https://img.shields.io/badge/Pygame-arcade%20UI-2ea44f)
![License](https://img.shields.io/badge/license-not%20added-lightgrey)

</div>

---

## 🎮 Overview

**Staring Contest Final Boss** is a webcam-based blink game built for an **Open Sauce exhibit**. Instead of a controller, keyboard, or mouse, the player uses their eyes: blinking becomes the input.

The project currently includes a survival-style staring contest and a one-lane rhythm game. Both modes use a shared blink input module powered by OpenCV, MediaPipe Face Landmarker / Face Mesh landmarks, and an Eye Aspect Ratio-style eye openness score.

The goal is to make a weird, memorable exhibit game that feels instantly understandable: step up to the camera, calibrate, stare, blink, panic, repeat.

> Current state: playable prototype. The software game modes work, but hardware effects and polish are still in progress.

---

## ✅ Current Features

| Status | Feature |
| --- | --- |
| ✅ | Webcam input with OpenCV |
| ✅ | MediaPipe Face Landmarker / Face Mesh tracking |
| ✅ | Shared `BlinkInput` module |
| ✅ | Eye openness / EAR-style blink detection |
| ✅ | Adaptive calibration before play |
| ✅ | Blink smoothing, state machine, and cooldown |
| ✅ | SPACE keyboard backup input |
| ✅ | Survival mode |
| ✅ | Rhythm mode |
| ✅ | Main menu / exhibit launcher |
| ✅ | Instructions before each mode |
| ✅ | Player profile saved locally |
| ✅ | Local leaderboard saved in JSON |
| ✅ | Settings menu with name, camera, fullscreen, and leaderboard reset |
| ✅ | Standalone blink detector test mode |

---

## 🖼️ Screenshots

Screenshots are not committed yet. These paths are reserved for future GitHub preview images:

| Screen | Placeholder |
| --- | --- |
| Main menu | `docs/images/menu.png` |
| Survival mode | `docs/images/survival.png` |
| Rhythm mode | `docs/images/rhythm.png` |
| Calibration | `docs/images/calibration.png` |

TODO: Add real screenshots from the exhibit computer once the visual layout is final.

---

## 🕹️ Game Modes

### 👁️ Survival Mode

Survival mode is the staring contest.

The player calibrates with eyes open, then tries to keep staring as long as possible. A detected blink ends the round. If the face leaves the camera view, the game pauses instead of instantly counting a loss.

```text
Calibrate → Countdown → Keep eyes open → Blink = Game Over
```

Survival mode also includes simple software-only challenge effects, such as fakeout messages and visual flashes. Hardware effects are not implemented yet.

### ♫ Rhythm Mode

Rhythm mode is a one-lane blink rhythm game.

Notes fall toward a target zone. A blink acts like pressing SPACE. Regular notes require a blink near the hit zone, while hold notes require the player to keep their eyes closed briefly.

```text
Falling note
     ↓
Target ring  ← blink here
```

The rhythm game includes timing judgments, combo, misses, a countdown, speed ramping, random blink timing, and occasional hold-note patterns.

---

## 🧠 How It Works

The core input system lives in [`blink_input.py`](blink_input.py).

1. **Webcam capture**  
   OpenCV opens the selected camera and provides frames.

2. **Face tracking**  
   MediaPipe Face Landmarker tracks one face and returns Face Mesh landmarks.

3. **Eye openness score**  
   The detector measures both eyes using Face Mesh landmark distances. This produces an Eye Aspect Ratio-style openness value.

4. **Calibration**  
   Before play, the player keeps their eyes open for a few seconds. The game learns the player's normal open-eye value and sets an adaptive blink threshold.

5. **Smoothing and state machine**  
   A smoothed eye openness score feeds a blink state machine. The cooldown/debounce logic prevents one blink from counting multiple times.

6. **Fallback input**  
   SPACE remains a backup blink input for testing, demos, and webcam troubleshooting.

The MediaPipe model file is expected as `face_landmarker.task`. If it is missing, `blink_input.py` attempts to download it automatically.

---

## 📁 Project Structure

Current repository layout:

```text
SCFB/
├── .gitignore
├── README.md
├── blink_detector.py
├── blink_input.py
├── camera_test.py
├── face_landmarker.task
├── leaderboard.json
├── main.py
├── player_profile.json
├── requirements.txt
├── rhythm_mode.py
└── survival_mode.py
```

Additional documentation folders:

```text
SCFB/
├── docs/
│   └── images/
├── assets/
└── .github/
    ├── ISSUE_TEMPLATE.md
    └── PULL_REQUEST_TEMPLATE.md
```

---

## 🚀 Installation

### 1. Clone the repository

```bash
git clone <your-repo-url>
cd SCFB
```

### 2. Create a virtual environment

```bash
python -m venv .venv
```

### 3. Activate the virtual environment

Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

macOS / Linux:

```bash
source .venv/bin/activate
```

### 4. Install dependencies

```bash
pip install -r requirements.txt
```

### 5. Run the full exhibit app

```bash
python main.py
```

---

## 🧪 Other Run Commands

| Command | Purpose |
| --- | --- |
| `python main.py` | Full menu-driven exhibit app |
| `python blink_input.py` | Standalone blink detector test |
| `python camera_test.py` | Simple webcam test |
| `python survival_mode.py` | Run survival mode directly |
| `python rhythm_mode.py` | Run rhythm mode directly |
| `python blink_detector.py` | Compatibility launcher for blink input |

---

## 📦 Dependencies

| Package | Purpose |
| --- | --- |
| `opencv-python` | Webcam capture, camera windows, image processing |
| `mediapipe` | Face Landmarker / Face Mesh tracking |
| `pygame` | Main menu, rhythm mode, UI rendering |
| `numpy` | Eye openness math and smoothing support |

Standard library modules are also used for JSON files, paths, timing, randomness, math, and downloading the MediaPipe model when needed.

---

## 🎛️ Controls

### Main Menu

| Input | Action |
| --- | --- |
| Mouse | Click menu buttons |
| `↑` / `↓` | Move selection |
| `W` / `S` | Move selection |
| `Enter` | Confirm selection |
| `ESC` | Quit |

### Player Name Entry

| Input | Action |
| --- | --- |
| Keyboard typing | Enter player name |
| `Backspace` | Delete character |
| `Enter` | Confirm name |
| `ESC` | Cancel if a name already exists |

Names are limited to 12 characters and saved to `player_profile.json`.

### Settings

| Menu Item | Action |
| --- | --- |
| Change Player Name | Opens the name entry screen |
| Camera Selection | Cycles camera index `0` through `3` |
| Toggle Fullscreen | Switches window/fullscreen mode |
| Reset Leaderboard | Clears saved scores |
| Back | Returns to main menu |

### Survival Mode

| Input | Action |
| --- | --- |
| Keep eyes open | Continue surviving |
| Blink | End the round |
| SPACE | Backup/fake blink |
| `C` | Recalibrate |
| `D` | Toggle debug overlay |
| `R` / SPACE after game over | Restart |
| `M` after game over | Return to menu when launched from `main.py` |
| `ESC` / `Q` | Quit survival |

### Rhythm Mode

| Input | Action |
| --- | --- |
| Blink | Hit note |
| Hold eyes closed | Complete hold note |
| SPACE | Backup blink / hold input |
| `C` | Recalibrate |
| `D` | Toggle debug text |
| `R` | Restart and recalibrate |
| `M` after game over | Return to menu when launched from `main.py` |
| `ESC` | Quit rhythm |

---

## 💾 Save Files

| File | Purpose |
| --- | --- |
| `player_profile.json` | Saved player name, camera index, fullscreen setting |
| `leaderboard.json` | Local survival times and rhythm scores |

Survival scores are saved by player name:

```json
{
  "NIK": 82.3
}
```

Rhythm scores use a prefix so they do not mix with survival times:

```json
{
  "rhythm:NIK": 15400
}
```

Both files are local only. There is no online leaderboard.

---

## 🎯 Calibration Tips

Calibration works best when the player:

- faces the webcam directly;
- keeps both eyes open during calibration;
- avoids turning their head too far;
- has even lighting on their face;
- avoids strong backlighting;
- sits roughly arm's length from the camera;
- keeps glasses glare as low as possible.

If blinks feel too sensitive or not sensitive enough, tune constants near the top of [`blink_input.py`](blink_input.py), especially:

| Constant | What it affects |
| --- | --- |
| `BLINK_THRESHOLD_RATIO` | Lower values make blink detection less sensitive |
| `SMOOTHING_ALPHA` | Higher values react faster; lower values smooth more |
| `MIN_CLOSED_FRAMES` | More frames require a stronger/longer blink |
| `MAX_CLOSED_FRAMES` | Maximum closed-eye duration counted as a blink |
| `COOLDOWN_FRAMES` | Debounce time after a blink |

---

## ⚙️ Performance Notes

Recommended setup for the current prototype:

- a normal built-in or USB webcam;
- stable indoor lighting;
- the camera positioned near eye level;
- a laptop/desktop capable of running MediaPipe Face Landmarker in real time;
- only one player visible in the camera frame.

If camera tracking is unstable, test with:

```bash
python camera_test.py
```

Then test blink detection directly with:

```bash
python blink_input.py
```

---

## 🗺️ Roadmap

### Current Prototype

- [x] Webcam blink input
- [x] Survival mode
- [x] Rhythm mode
- [x] Shared blink detector
- [x] Main menu / exhibit flow
- [x] Local player profile
- [x] Local leaderboard

### Planned

- [ ] Real screenshots and demo GIFs
- [ ] More polished exhibit instructions
- [ ] More visual feedback and effects
- [ ] Better settings persistence/testing
- [ ] More robust camera selection UI
- [ ] Cleaner separation of menu/UI modules

### Stretch Goals

- [ ] Boss mode variants
- [ ] Tournament / two-player exhibit flow
- [ ] Achievement system
- [ ] Online leaderboard
- [ ] Arduino hardware integration
- [ ] LED effects
- [ ] Optional fan challenge
- [ ] Sound effects and music

Hardware, fan, LED, and Arduino features are planned/stretch goals only. They are not implemented in the current code.

---

## 🐛 Known Issues

- Webcam behavior depends heavily on lighting, camera quality, and face angle.
- Camera selection currently cycles numeric indexes instead of showing camera names.
- `player_profile.json` and `leaderboard.json` are local development/demo save files.
- The README screenshot section still needs real captured images.
- The project does not currently include automated tests.
- No license file has been added yet.

---

## 🤝 Contributing

Contributions are welcome while the project is still a prototype.

Good first areas:

- README screenshots;
- UI polish;
- calibration reliability;
- rhythm chart tuning;
- menu/settings cleanup;
- bug reports from different webcam setups.

Before opening a pull request:

1. Keep gameplay changes focused and easy to test.
2. Do not add hardware behavior unless it is explicitly part of the task.
3. Verify the project still runs with `python main.py`.
4. Test SPACE fallback input if webcam behavior changes.
5. Update documentation when behavior changes.

See [`CONTRIBUTING.md`](CONTRIBUTING.md) for more details.

---

## 📜 License

No license file has been added to this repository yet.

TODO: Add a license before encouraging reuse or redistribution. If this is intended to be open source, choose and commit a license such as MIT, Apache-2.0, or GPL.

---

## 🙏 Acknowledgements

This prototype uses and appreciates:

- [OpenCV](https://opencv.org/) for webcam capture and image display;
- [MediaPipe](https://developers.google.com/mediapipe) for face landmark tracking;
- [Pygame](https://www.pygame.org/) for game windows and UI rendering;
- [NumPy](https://numpy.org/) for numerical calculations;
- Open Sauce as the exhibit inspiration and target event.

---

<div align="center">

Built for blinking, staring, and discovering that your eyelids have terrible timing.

</div>
