from urllib.request import urlretrieve

import cv2
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision


MODEL_PATH = "face_landmarker.task"
MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/face_landmarker/"
    "face_landmarker/float16/latest/face_landmarker.task"
)


# Face Mesh landmark ids around each eye.
LEFT_EYE = {
    "horizontal": (33, 133),
    "vertical": [(159, 145), (158, 153)],
}

RIGHT_EYE = {
    "horizontal": (362, 263),
    "vertical": [(386, 374), (385, 380)],
}


def distance(a, b):
    """Return the 2D distance between two normalized MediaPipe landmarks."""
    dx = a.x - b.x
    dy = a.y - b.y
    return (dx * dx + dy * dy) ** 0.5


def eye_openness(landmarks, eye):
    """Estimate eye openness as vertical eye distance divided by eye width."""
    horizontal_a, horizontal_b = eye["horizontal"]
    width = distance(landmarks[horizontal_a], landmarks[horizontal_b])

    vertical_distances = []
    for top, bottom in eye["vertical"]:
        vertical_distances.append(distance(landmarks[top], landmarks[bottom]))

    if width == 0:
        return 0

    return sum(vertical_distances) / len(vertical_distances) / width


def download_model_if_needed():
    """Download the Face Landmarker model once, if it is not already present."""
    try:
        open(MODEL_PATH, "rb").close()
    except FileNotFoundError:
        print("Downloading MediaPipe face model...")
        urlretrieve(MODEL_URL, MODEL_PATH)


def calculate_blink_threshold(samples):
    """Calculate a player's blink threshold from open-eye calibration samples."""
    if not samples:
        return 0.20

    average_open = sum(samples) / len(samples)
    threshold = average_open * 0.65
    return min(max(threshold, 0.10), 0.28)


def calculate_calibrated_values(open_samples, blink_samples):
    """Calculate open average, closed average, and blink threshold."""
    if not open_samples or not blink_samples:
        return None, None, 0.20

    open_avg = sum(open_samples) / len(open_samples)
    sorted_blinks = sorted(blink_samples)
    low_count = max(1, len(sorted_blinks) // 5)
    lowest_values = sorted_blinks[:low_count]
    closed_avg = sum(lowest_values) / len(lowest_values)

    if closed_avg >= open_avg:
        return open_avg, closed_avg, 0.20

    threshold = closed_avg + (open_avg - closed_avg) * 0.45
    threshold = min(max(threshold, 0.10), 0.28)
    return open_avg, closed_avg, threshold


def get_blendshape_blink_score(results):
    """Return average eye blink blendshape score, if MediaPipe provides it."""
    face_blendshapes = getattr(results, "face_blendshapes", None)

    if not face_blendshapes:
        return None

    blink_scores = []

    for category in face_blendshapes[0]:
        if category.category_name in ("eyeBlinkLeft", "eyeBlinkRight"):
            blink_scores.append(category.score)

    if not blink_scores:
        return None

    return sum(blink_scores) / len(blink_scores)


def get_blink_signals(results, landmarks):
    """Return landmark and blendshape blink signals for one detected face."""
    left_open = eye_openness(landmarks, LEFT_EYE)
    right_open = eye_openness(landmarks, RIGHT_EYE)
    raw_openness = (left_open + right_open) / 2

    blink_blendshape_score = get_blendshape_blink_score(results)
    landmark_closed = raw_openness < 0.20
    blendshape_closed = False

    if blink_blendshape_score is not None:
        blendshape_closed = blink_blendshape_score > 0.45

    return {
        "raw_openness": raw_openness,
        "smoothed_openness": raw_openness,
        "landmark_closed": landmark_closed,
        "blink_blendshape_score": blink_blendshape_score,
        "blendshape_closed": blendshape_closed,
        "final_closed_signal": landmark_closed or blendshape_closed,
    }


class BlinkDetector:
    """Reusable blink detector for all game modes."""

    def __init__(self):
        download_model_if_needed()

        base_options = python.BaseOptions(model_asset_path=MODEL_PATH)
        options = vision.FaceLandmarkerOptions(
            base_options=base_options,
            running_mode=vision.RunningMode.VIDEO,
            num_faces=1,
            output_face_blendshapes=True,
        )

        self.landmarker = vision.FaceLandmarker.create_from_options(options)
        self.frame_time_ms = 0
        self.open_samples = []
        self.blink_samples = []
        self.open_avg = None
        self.closed_avg = None
        self.blink_threshold = 0.20
        self.calibration_phase = "WAITING"
        self.phase_started_at = 0
        self.blink_test_count = 0
        self.blink_test_below = False
        self.calibration_complete = False
        self.openness_history = []
        self.closed_frames = 0
        self.blink_state = "OPEN"
        self.blink_reported = False
        self.last_signals = None

    def close(self):
        """Release MediaPipe resources."""
        self.landmarker.close()

    def process_frame(self, frame):
        """Track one face and return raw eye openness for this frame."""
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
        results = self.landmarker.detect_for_video(mp_image, self.frame_time_ms)
        self.frame_time_ms += 1

        if not results.face_landmarks:
            self.last_signals = None
            return {
                "face_found": False,
                "raw_openness": None,
                "signals": None,
            }

        landmarks = results.face_landmarks[0]
        signals = get_blink_signals(results, landmarks)
        self.last_signals = signals

        return {
            "face_found": True,
            "raw_openness": signals["raw_openness"],
            "signals": signals,
        }

    def start_calibration(self, now):
        """Begin the multi-step calibration flow."""
        self.open_samples = []
        self.blink_samples = []
        self.open_avg = None
        self.closed_avg = None
        self.blink_threshold = 0.20
        self.calibration_phase = "OPEN_EYES"
        self.phase_started_at = now
        self.blink_test_count = 0
        self.blink_test_below = False
        self.calibration_complete = False
        self.reset_blink_state()

    def reset_calibration(self):
        """Return calibration to the initial waiting state."""
        self.open_samples = []
        self.blink_samples = []
        self.open_avg = None
        self.closed_avg = None
        self.blink_threshold = 0.20
        self.calibration_phase = "WAITING"
        self.phase_started_at = 0
        self.blink_test_count = 0
        self.blink_test_below = False
        self.calibration_complete = False
        self.reset_blink_state()

    def update_calibration(self, raw_openness, now):
        """Advance calibration and return text/status for the game screen."""
        if self.calibration_phase == "OPEN_EYES":
            if raw_openness is not None:
                self.open_samples.append(raw_openness)

            if now - self.phase_started_at >= 2:
                if self.open_samples:
                    self.open_avg = sum(self.open_samples) / len(self.open_samples)

                self.calibration_phase = "BLINK_TEST"
                self.phase_started_at = now

        elif self.calibration_phase == "BLINK_TEST":
            if raw_openness is not None:
                self.blink_samples.append(raw_openness)

                test_threshold = 0.20
                if self.open_avg is not None:
                    test_threshold = min(max(self.open_avg * 0.65, 0.10), 0.28)

                if raw_openness < test_threshold and not self.blink_test_below:
                    self.blink_test_count += 1
                    self.blink_test_below = True
                elif raw_openness > test_threshold * 1.15:
                    self.blink_test_below = False

            if self.blink_test_count >= 3 and not self.blink_test_below:
                self.finish_calibration(now)

        elif self.calibration_phase == "READY":
            if now - self.phase_started_at >= 2:
                self.calibration_complete = True

        return self.calibration_status()

    def finish_calibration(self, now=None):
        """Lock in the blink threshold for this run."""
        self.open_avg, self.closed_avg, self.blink_threshold = calculate_calibrated_values(
            self.open_samples,
            self.blink_samples,
        )
        self.calibration_phase = "READY"
        self.phase_started_at = now if now is not None else self.phase_started_at
        self.reset_blink_state()
        return self.blink_threshold

    def calibration_status(self):
        """Return current calibration values for display."""
        return {
            "phase": self.calibration_phase,
            "complete": self.calibration_complete,
            "blink_count": self.blink_test_count,
            "open_avg": self.open_avg,
            "closed_avg": self.closed_avg,
            "blink_threshold": self.blink_threshold,
        }

    def reset_blink_state(self):
        """Clear smoothing and closed-frame counters."""
        self.openness_history = []
        self.closed_frames = 0
        self.blink_state = "OPEN"
        self.blink_reported = False

    def update(self, blink_input):
        """Return blink status using smoothing, hysteresis, and a state machine."""
        if isinstance(blink_input, dict):
            signals = blink_input.copy()
            raw_openness = signals["raw_openness"]
        else:
            raw_openness = blink_input
            signals = {
                "raw_openness": raw_openness,
                "smoothed_openness": raw_openness,
                "landmark_closed": False,
                "blink_blendshape_score": None,
                "blendshape_closed": False,
                "final_closed_signal": False,
            }

        if raw_openness is None:
            self.blink_state = "BAD_TRACKING"
            self.closed_frames = 0
            return {
                "blink_detected": False,
                "raw_openness": None,
                "smoothed_openness": None,
                "landmark_closed": False,
                "blink_blendshape_score": None,
                "blendshape_closed": False,
                "final_closed_signal": False,
                "blink_threshold": self.blink_threshold,
                "open_avg": self.open_avg,
                "closed_avg": self.closed_avg,
                "close_threshold": self.blink_threshold,
                "open_threshold": self.blink_threshold * 1.15,
                "blink_state": self.blink_state,
                "closed_frames": self.closed_frames,
            }

        self.openness_history.append(raw_openness)
        self.openness_history = self.openness_history[-5:]

        smoothed = sum(self.openness_history) / len(self.openness_history)
        close_threshold = self.blink_threshold
        open_threshold = self.blink_threshold * 1.15
        landmark_closed = smoothed < close_threshold
        landmark_open = smoothed > open_threshold
        blendshape_score = signals["blink_blendshape_score"]
        blendshape_closed = blendshape_score is not None and blendshape_score > 0.45
        blendshape_open = blendshape_score is None or blendshape_score < 0.35
        final_closed_signal = landmark_closed or blendshape_closed
        final_open_signal = landmark_open and blendshape_open
        blink_detected = False
        signals["smoothed_openness"] = smoothed
        signals["landmark_closed"] = landmark_closed
        signals["blendshape_closed"] = blendshape_closed
        signals["final_closed_signal"] = final_closed_signal
        self.last_signals = signals

        if self.blink_state == "BAD_TRACKING":
            self.blink_state = "OPEN"

        if self.blink_state == "OPEN":
            if final_closed_signal:
                self.blink_state = "POSSIBLY_CLOSED"
                self.closed_frames = 1
            else:
                self.closed_frames = 0
                self.blink_reported = False

        elif self.blink_state == "POSSIBLY_CLOSED":
            if final_closed_signal:
                self.closed_frames += 1

                if self.closed_frames >= 2:
                    self.blink_state = "CLOSED"
                    blink_detected = not self.blink_reported
                    self.blink_reported = True
            elif final_open_signal:
                self.blink_state = "OPEN"
                self.closed_frames = 0

        elif self.blink_state == "CLOSED":
            if final_closed_signal:
                self.closed_frames += 1
            elif final_open_signal:
                self.blink_state = "REOPENING"

        elif self.blink_state == "REOPENING":
            if final_open_signal:
                self.blink_state = "OPEN"
                self.closed_frames = 0
                self.blink_reported = False
            elif final_closed_signal:
                self.blink_state = "CLOSED"

        if self.blink_state not in ("POSSIBLY_CLOSED", "CLOSED"):
            self.closed_frames = 0

        return {
            "blink_detected": blink_detected,
            "raw_openness": signals["raw_openness"],
            "smoothed_openness": signals["smoothed_openness"],
            "landmark_closed": signals["landmark_closed"],
            "blink_blendshape_score": signals["blink_blendshape_score"],
            "blendshape_closed": signals["blendshape_closed"],
            "final_closed_signal": signals["final_closed_signal"],
            "blink_threshold": self.blink_threshold,
            "open_avg": self.open_avg,
            "closed_avg": self.closed_avg,
            "close_threshold": close_threshold,
            "open_threshold": open_threshold,
            "blink_state": self.blink_state,
            "closed_frames": self.closed_frames,
        }

    def simulate_blink(self):
        """Return a blink result for keyboard testing."""
        self.blink_state = "CLOSED"
        self.closed_frames = 2
        return {
            "blink_detected": True,
            "raw_openness": None,
            "smoothed_openness": None,
            "landmark_closed": True,
            "blink_blendshape_score": None,
            "blendshape_closed": False,
            "final_closed_signal": True,
            "blink_threshold": self.blink_threshold,
            "open_avg": self.open_avg,
            "closed_avg": self.closed_avg,
            "close_threshold": self.blink_threshold,
            "open_threshold": self.blink_threshold * 1.15,
            "blink_state": self.blink_state,
            "closed_frames": self.closed_frames,
        }

    def debug_status(self, raw_openness=None):
        """Return current detector values without changing blink state."""
        smoothed = None

        if self.openness_history:
            smoothed = sum(self.openness_history) / len(self.openness_history)

        blendshape_score = None
        blendshape_closed = False

        if self.last_signals:
            blendshape_score = self.last_signals["blink_blendshape_score"]
            blendshape_closed = self.last_signals["blendshape_closed"]

        return {
            "raw_openness": raw_openness,
            "smoothed_openness": smoothed,
            "landmark_closed": smoothed is not None and smoothed < self.blink_threshold,
            "blink_blendshape_score": blendshape_score,
            "blendshape_closed": blendshape_closed,
            "final_closed_signal": self.blink_state in ("POSSIBLY_CLOSED", "CLOSED"),
            "open_avg": self.open_avg,
            "closed_avg": self.closed_avg,
            "blink_threshold": self.blink_threshold,
            "close_threshold": self.blink_threshold,
            "open_threshold": self.blink_threshold * 1.15,
            "blink_state": self.blink_state,
            "closed_frames": self.closed_frames,
        }


def main():
    cap = cv2.VideoCapture(0)

    if not cap.isOpened():
        print("Could not open webcam.")
        return

    detector = BlinkDetector()

    try:
        while True:
            ret, frame = cap.read()

            if not ret:
                print("Could not read frame from webcam.")
                break

            face = detector.process_frame(frame)
            blink = detector.update(face["signals"])

            if blink["blink_detected"]:
                print("BLINK")

            if blink["raw_openness"] is not None:
                cv2.putText(
                    frame,
                    f"Eye: {blink['raw_openness']:.2f}  T: {blink['blink_threshold']:.2f}",
                    (20, 40),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.8,
                    (0, 255, 0),
                    2,
                )

            cv2.imshow("Blink Detector", frame)

            if cv2.waitKey(1) & 0xFF == ord("q"):
                break
    finally:
        detector.close()
        cap.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
