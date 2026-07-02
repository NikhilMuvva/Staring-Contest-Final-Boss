"""Shared, calibrated webcam blink input for every game mode."""

from pathlib import Path
from time import monotonic
from urllib.request import urlretrieve

import cv2
import mediapipe as mp
import numpy as np
from mediapipe.tasks import python
from mediapipe.tasks.python import vision


# Detector tuning. Start here when adjusting the exhibit camera setup.
CALIBRATION_SECONDS = 3
SMOOTHING_ALPHA = 0.45
BLINK_THRESHOLD_RATIO = 0.65
MIN_CLOSED_FRAMES = 2
MAX_CLOSED_FRAMES = 15
COOLDOWN_FRAMES = 4

MODEL_PATH = Path(__file__).with_name("face_landmarker.task")
MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/face_landmarker/"
    "face_landmarker/float16/latest/face_landmarker.task"
)

# Face Mesh landmarks at the horizontal corners and eyelids of each eye.
LEFT_EYE = {
    "horizontal": (33, 133),
    "vertical": ((159, 145), (158, 153)),
}
RIGHT_EYE = {
    "horizontal": (362, 263),
    "vertical": ((386, 374), (385, 380)),
}


def _distance(first, second):
    """Return normalized 2D landmark distance."""
    return float(np.hypot(first.x - second.x, first.y - second.y))


def _eye_openness(landmarks, eye):
    """Calculate an Eye Aspect Ratio-style openness value for one eye."""
    corner_a, corner_b = eye["horizontal"]
    width = _distance(landmarks[corner_a], landmarks[corner_b])
    if width <= 1e-6:
        return 0.0

    heights = [
        _distance(landmarks[top], landmarks[bottom])
        for top, bottom in eye["vertical"]
    ]
    return float(np.mean(heights) / width)


class BlinkInput:
    """Own the webcam and emit one event for each complete, valid blink."""

    def __init__(self, camera_index=0):
        self.camera_index = camera_index
        self.cap = cv2.VideoCapture(camera_index)

        if not MODEL_PATH.exists():
            print("Downloading MediaPipe face model...")
            urlretrieve(MODEL_URL, MODEL_PATH)

        try:
            options = vision.FaceLandmarkerOptions(
                base_options=python.BaseOptions(model_asset_path=str(MODEL_PATH)),
                running_mode=vision.RunningMode.VIDEO,
                num_faces=1,
                output_face_blendshapes=False,
            )
            self.landmarker = vision.FaceLandmarker.create_from_options(options)
        except Exception:
            self.cap.release()
            raise
        self._last_timestamp_ms = -1

        self.normal_open_openness = None
        self.threshold = 0.20
        self.calibrated = False
        self.smoothed_openness = None
        self.state = "OPEN"
        self.closed_frames = 0
        self.cooldown_frames = 0
        self.blink_count = 0
        self.last_status = self._status(False, None, "Waiting for camera")

    @property
    def is_opened(self):
        """Return whether the camera opened successfully."""
        return self.cap.isOpened()

    def _timestamp_ms(self):
        """Return a strictly increasing timestamp required by MediaPipe VIDEO mode."""
        timestamp = int(monotonic() * 1000)
        timestamp = max(timestamp, self._last_timestamp_ms + 1)
        self._last_timestamp_ms = timestamp
        return timestamp

    def _measure_openness(self, frame):
        """Return the two-eye openness score, or None when no face is tracked."""
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
        result = self.landmarker.detect_for_video(image, self._timestamp_ms())

        if not result.face_landmarks:
            return None

        landmarks = result.face_landmarks[0]
        left = _eye_openness(landmarks, LEFT_EYE)
        right = _eye_openness(landmarks, RIGHT_EYE)
        return (left + right) / 2.0

    def _status(self, face_found, openness, debug_text):
        return {
            "face_found": face_found,
            "eye_openness": openness,
            "smoothed_eye_openness": self.smoothed_openness,
            "threshold": self.threshold,
            "blink_count": self.blink_count,
            "state": self.state,
            "calibrated": self.calibrated,
            "debug_text": debug_text,
        }

    def calibrate(self, seconds=CALIBRATION_SECONDS, show_window=False):
        """Learn normal open-eye openness from several seconds of camera frames."""
        if not self.is_opened:
            self.last_status = self._status(False, None, "Camera unavailable")
            return False

        samples = []
        started_at = monotonic()
        self.reset_state()

        while monotonic() - started_at < seconds:
            ok, frame = self.cap.read()
            if not ok:
                continue

            openness = self._measure_openness(frame)
            if openness is not None:
                samples.append(openness)

            if show_window:
                remaining = max(0.0, seconds - (monotonic() - started_at))
                cv2.putText(
                    frame,
                    f"Keep eyes open - calibrating {remaining:.1f}s",
                    (20, 40),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    (0, 255, 255),
                    2,
                )
                cv2.imshow("Blink Input Test", frame)
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    return False

        if not samples:
            self.last_status = self._status(False, None, "Calibration failed: face not found")
            return False

        # The upper 60% rejects accidental blinks and low tracking outliers.
        cutoff = float(np.percentile(samples, 40))
        open_samples = [sample for sample in samples if sample >= cutoff]
        self.normal_open_openness = float(np.median(open_samples))
        self.threshold = self.normal_open_openness * BLINK_THRESHOLD_RATIO
        self.calibrated = True
        self.reset_state()
        self.last_status = self._status(
            True,
            self.normal_open_openness,
            f"Calibrated: open={self.normal_open_openness:.3f}",
        )
        return True

    def reset_state(self):
        """Clear transient smoothing and state-machine values."""
        self.smoothed_openness = None
        self.state = "OPEN"
        self.closed_frames = 0
        self.cooldown_frames = 0

    def _advance_state(self, closed, reopened):
        """Advance blink state and return True once for a valid blink."""
        blink_event = False

        if self.state == "OPEN":
            if closed:
                self.state = "CLOSING"
                self.closed_frames = 1

        elif self.state == "CLOSING":
            if closed:
                self.closed_frames += 1
                if self.closed_frames >= MIN_CLOSED_FRAMES:
                    self.state = "CLOSED"
            elif reopened:
                self.state = "OPEN"
                self.closed_frames = 0

        elif self.state == "CLOSED":
            if closed:
                self.closed_frames += 1
                if self.closed_frames > MAX_CLOSED_FRAMES:
                    self.state = "COOLDOWN"
                    self.cooldown_frames = COOLDOWN_FRAMES
            elif reopened:
                if self.closed_frames <= MAX_CLOSED_FRAMES:
                    blink_event = True
                    self.blink_count += 1
                self.state = "COOLDOWN"
                self.cooldown_frames = COOLDOWN_FRAMES

        elif self.state == "COOLDOWN":
            if reopened:
                self.cooldown_frames -= 1
                if self.cooldown_frames <= 0:
                    self.state = "OPEN"
                    self.closed_frames = 0
            else:
                self.cooldown_frames = COOLDOWN_FRAMES

        return blink_event

    def update(self):
        """Read one frame and return ``(frame, blink_event, status)``."""
        if not self.is_opened:
            status = self._status(False, None, "Camera unavailable")
            self.last_status = status
            return None, False, status

        ok, frame = self.cap.read()
        if not ok:
            status = self._status(False, None, "Camera frame unavailable")
            self.last_status = status
            return None, False, status

        openness = self._measure_openness(frame)
        if openness is None:
            # Face loss is not a blink. Reset partial events so re-entry is safe.
            self.reset_state()
            status = self._status(False, None, "Face not found")
            self.last_status = status
            return frame, False, status

        if self.smoothed_openness is None:
            self.smoothed_openness = openness
        else:
            self.smoothed_openness = (
                SMOOTHING_ALPHA * openness
                + (1.0 - SMOOTHING_ALPHA) * self.smoothed_openness
            )

        close_threshold = self.threshold
        open_threshold = self.threshold * 1.12  # Hysteresis prevents edge chatter.
        closed = self.smoothed_openness < close_threshold
        reopened = self.smoothed_openness > open_threshold
        blink_event = self._advance_state(closed, reopened)
        debug_text = (
            f"Face: yes  Eye: {openness:.3f}  Smooth: "
            f"{self.smoothed_openness:.3f}  T: {self.threshold:.3f}  {self.state}"
        )
        status = self._status(True, openness, debug_text)
        self.last_status = status
        return frame, blink_event, status

    def release(self):
        """Release camera and MediaPipe resources."""
        if self.landmarker is not None:
            self.landmarker.close()
            self.landmarker = None
        if self.cap is not None:
            self.cap.release()


def main():
    """Run a standalone camera/calibration/debug test."""
    blink_input = BlinkInput(camera_index=0)
    if not blink_input.is_opened:
        print("Could not open webcam.")
        blink_input.release()
        return

    try:
        if not blink_input.calibrate(show_window=True):
            print(blink_input.last_status["debug_text"])
            return

        while True:
            frame, blink_event, status = blink_input.update()
            if frame is None:
                print(status["debug_text"])
                break

            if blink_event:
                print("BLINK")

            eye = status["eye_openness"]
            eye_text = "--" if eye is None else f"{eye:.3f}"
            lines = [
                f"Face found: {status['face_found']}",
                f"Eye openness: {eye_text}",
                f"Threshold: {status['threshold']:.3f}",
                f"Blinks: {status['blink_count']}",
                status["debug_text"],
            ]
            for index, line in enumerate(lines):
                cv2.putText(
                    frame,
                    line,
                    (20, 35 + index * 28),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.65,
                    (0, 255, 0),
                    2,
                )

            cv2.imshow("Blink Input Test", frame)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break
    finally:
        blink_input.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
