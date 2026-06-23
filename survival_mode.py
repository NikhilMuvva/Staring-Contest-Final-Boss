import json
import random
import time

import cv2

from blink_detector import BlinkDetector

LEADERBOARD_PATH = "leaderboard.json"
CHALLENGE_TYPES = ["WIND_GUST", "LIGHT_FLASH", "FOCUS_ZONE", "FAKEOUT"]
FAKEOUT_MESSAGES = ["DON'T BLINK", "STAY LOCKED IN", "EYES OPEN"]


def load_leaderboard():
    """Load best times by username from disk."""
    try:
        with open(LEADERBOARD_PATH, "r") as file:
            return json.load(file)
    except FileNotFoundError:
        return {}


def save_leaderboard(leaderboard):
    """Save best times by username to disk."""
    with open(LEADERBOARD_PATH, "w") as file:
        json.dump(leaderboard, file, indent=2)


def update_best_time(leaderboard, username, final_time):
    """Keep only the player's best survival time."""
    previous_best = leaderboard.get(username, 0)

    if final_time > previous_best:
        leaderboard[username] = final_time
        save_leaderboard(leaderboard)


def top_scores(leaderboard, limit=5):
    """Return the highest scores first."""
    return sorted(leaderboard.items(), key=lambda item: item[1], reverse=True)[:limit]


def draw_center_text(frame, text, y, scale, color, thickness):
    """Draw centered text on the camera frame."""
    font = cv2.FONT_HERSHEY_SIMPLEX
    text_size, _ = cv2.getTextSize(text, font, scale, thickness)
    x = (frame.shape[1] - text_size[0]) // 2
    cv2.putText(frame, text, (x, y), font, scale, color, thickness)


def draw_right_text(frame, text, y, scale, color, thickness, margin=20):
    """Draw text aligned to the right edge of the camera frame."""
    font = cv2.FONT_HERSHEY_SIMPLEX
    text_size, _ = cv2.getTextSize(text, font, scale, thickness)
    x = frame.shape[1] - text_size[0] - margin
    cv2.putText(frame, text, (x, y), font, scale, color, thickness)


def format_debug_value(value):
    """Format detector debug values compactly."""
    if value is None:
        return "--"
    if isinstance(value, float):
        return f"{value:.3f}"
    return str(value)


def draw_debug_overlay(frame, debug):
    """Draw blink detector internals in the lower-left corner."""
    lines = [
        f"raw: {format_debug_value(debug['raw_openness'])}",
        f"smooth: {format_debug_value(debug['smoothed_openness'])}",
        f"threshold: {format_debug_value(debug['blink_threshold'])}",
        f"landmark_closed: {debug['landmark_closed']}",
        f"blink_score: {format_debug_value(debug['blink_blendshape_score'])}",
        f"blendshape_closed: {debug['blendshape_closed']}",
        f"final_closed: {debug['final_closed_signal']}",
        f"closed_frame_count: {debug['closed_frames']}",
    ]

    y = frame.shape[0] - 150

    for line in lines:
        cv2.putText(
            frame,
            line,
            (20, y),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.42,
            (0, 255, 0),
            1,
        )
        y += 18


def challenge_interval(elapsed_time):
    """Return the next challenge delay for the current difficulty level."""
    if elapsed_time < 20:
        return None
    if elapsed_time < 45:
        return random.uniform(12, 15)
    if elapsed_time < 60:
        return random.uniform(8, 12)
    return random.uniform(5, 8)


def challenge_duration(challenge_type):
    """Return how long each challenge stays active."""
    if challenge_type == "FOCUS_ZONE":
        return 5
    if challenge_type == "LIGHT_FLASH":
        return 2
    return 2


def start_challenge(game, now):
    """Start a random challenge. Later, Arduino commands can hook in here."""
    challenge_type = random.choice(CHALLENGE_TYPES)
    game["challenge"] = {
        "type": challenge_type,
        "started_at": now,
        "duration": challenge_duration(challenge_type),
        "message": random.choice(FAKEOUT_MESSAGES),
    }


def schedule_next_challenge(game):
    """Choose the next survival-time moment when a challenge should start."""
    delay = challenge_interval(game["elapsed_time"])

    if delay is None:
        game["next_challenge_time"] = 20 + random.uniform(12, 15)
    else:
        game["next_challenge_time"] = game["elapsed_time"] + delay


def update_challenge(game, now):
    """Start and stop challenges while the player is actively surviving."""
    if game["challenge"]:
        age = now - game["challenge"]["started_at"]

        if age >= game["challenge"]["duration"]:
            game["challenge"] = None
            schedule_next_challenge(game)

        return

    if game["elapsed_time"] >= game["next_challenge_time"]:
        start_challenge(game, now)


def draw_challenge(frame, game, now):
    """Draw the current challenge effect on top of the camera frame."""
    challenge = game["challenge"]

    if not challenge:
        return

    challenge_type = challenge["type"]
    age = now - challenge["started_at"]

    if challenge_type == "WIND_GUST":
        draw_center_text(frame, "WIND GUST INCOMING", 160, 1.3, (0, 255, 255), 3)

    elif challenge_type == "LIGHT_FLASH":
        # Strobe: flash white for about 0.3 seconds, then briefly clear.
        if age % 0.6 < 0.3:
            white = frame.copy()
            white[:] = (255, 255, 255)
            cv2.addWeighted(white, 0.8, frame, 0.2, 0, frame)

    elif challenge_type == "FOCUS_ZONE":
        draw_center_text(frame, "FOCUS ZONE", 160, 1.4, (0, 255, 255), 3)

    elif challenge_type == "FAKEOUT":
        draw_center_text(frame, challenge["message"], 160, 1.4, (0, 255, 255), 3)


def reset_game(now):
    """Return fresh state for a new survival run."""
    return {
        "countdown_started": False,
        "countdown_start_time": 0,
        "game_started": False,
        "game_over": False,
        "elapsed_time": 0,
        "final_time": 0,
        "last_time": now,
        "challenge": None,
        "next_challenge_time": 20 + random.uniform(12, 15),
    }


def main():
    username = input("Enter username: ").strip()

    if not username:
        username = "Player"

    leaderboard = load_leaderboard()

    cap = cv2.VideoCapture(0)

    if not cap.isOpened():
        print("Could not open webcam.")
        return

    detector = BlinkDetector()

    try:
        countdown_seconds = 3
        screen = "menu"
        game = reset_game(time.time())
        debug_overlay = False

        while True:
            now = time.time()
            ret, frame = cap.read()

            if not ret:
                print("Could not read frame from webcam.")
                break

            face = detector.process_frame(frame)
            face_found = face["face_found"]
            raw_openness = face["raw_openness"]

            best_time = leaderboard.get(username, 0)
            cv2.putText(
                frame,
                f"Player: {username}   Best: {best_time:.2f}",
                (20, 32),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.65,
                (255, 255, 255),
                2,
            )

            if screen == "menu":
                draw_center_text(frame, "STARING CONTEST FINAL BOSS", 130, 1.2, (255, 255, 255), 2)
                draw_center_text(frame, "Survival", 170, 1, (255, 255, 255), 2)
                draw_center_text(frame, "S = start game", 260, 0.9, (0, 255, 255), 2)
                draw_center_text(frame, "L = leaderboard", 305, 0.9, (0, 255, 255), 2)
                draw_center_text(frame, "Q = quit", 350, 0.9, (0, 255, 255), 2)

            elif screen == "leaderboard":
                draw_center_text(frame, "LEADERBOARD", 90, 1.4, (255, 255, 255), 3)
                scores = top_scores(leaderboard)

                if scores:
                    for index, (name, score) in enumerate(scores, start=1):
                        draw_center_text(
                            frame,
                            f"{index}. {name}: {score:.2f}s",
                            140 + index * 40,
                            0.8,
                            (0, 255, 255),
                            2,
                        )
                else:
                    draw_center_text(frame, "No scores yet", 220, 0.9, (0, 255, 255), 2)

                draw_center_text(frame, "M = menu    Q = quit", 380, 0.8, (255, 255, 255), 2)

            elif screen == "game":
                if (
                    not game["game_over"]
                    and not game["game_started"]
                    and face_found
                    and not game["countdown_started"]
                    and detector.calibration_phase == "WAITING"
                ):
                    detector.start_calibration(now)

                if (
                    not game["game_over"]
                    and detector.calibration_phase != "WAITING"
                    and not game["game_started"]
                    and not game["countdown_started"]
                    and not face_found
                ):
                    detector.calibration_phase = "WAITING"

                if (
                    not game["game_over"]
                    and detector.calibration_phase != "WAITING"
                    and not detector.calibration_complete
                    and not game["game_started"]
                ):
                    calibration = detector.update_calibration(raw_openness, now)

                    if calibration["phase"] == "OPEN_EYES":
                        draw_center_text(frame, "CALIBRATION", 160, 1, (255, 255, 255), 2)
                        draw_center_text(frame, "Keep eyes open", 230, 1, (0, 255, 255), 2)
                    elif calibration["phase"] == "BLINK_TEST":
                        draw_center_text(frame, "Blink slowly 3 times", 220, 1, (0, 255, 255), 2)
                        draw_center_text(
                            frame,
                            f"Blinks: {calibration['blink_count']} / 3",
                            275,
                            0.9,
                            (255, 255, 255),
                            2,
                        )
                    elif calibration["phase"] == "READY":
                        draw_center_text(frame, "READY", 210, 1.5, (0, 255, 255), 3)
                        draw_center_text(
                            frame,
                            f"Threshold: {calibration['blink_threshold']:.2f}",
                            275,
                            0.9,
                            (255, 255, 255),
                            2,
                        )

                if (
                    not game["game_over"]
                    and detector.calibration_complete
                    and not game["countdown_started"]
                    and not game["game_started"]
                ):
                    game["countdown_started"] = True
                    game["countdown_start_time"] = now

                if not game["game_over"] and game["countdown_started"] and not game["game_started"]:
                    countdown_left = countdown_seconds - int(now - game["countdown_start_time"])

                    if countdown_left > 0:
                        draw_center_text(frame, str(countdown_left), 260, 3, (0, 255, 255), 5)
                    else:
                        game["game_started"] = True
                        game["countdown_started"] = False
                        game["elapsed_time"] = 0
                        game["last_time"] = now
                        detector.reset_blink_state()

                if game["game_started"] and not game["game_over"] and face_found:
                    blink = detector.update(face["signals"])
                    game["elapsed_time"] += now - game["last_time"]
                    update_challenge(game, now)

                    if blink["blink_detected"]:
                        game["game_over"] = True
                        game["final_time"] = game["elapsed_time"]
                        update_best_time(leaderboard, username, game["final_time"])

                elif not game["game_over"]:
                    detector.reset_blink_state()

                if game["game_started"] and not game["game_over"] and face_found:
                    draw_challenge(frame, game, now)

                if not game["game_started"] and not game["countdown_started"]:
                    if detector.calibration_phase == "WAITING":
                        draw_center_text(frame, "Step into frame to calibrate", 240, 1, (0, 255, 255), 2)
                elif game["game_started"] and not game["game_over"] and not face_found:
                    draw_center_text(frame, "PAUSED", 220, 2, (0, 255, 255), 4)
                    draw_center_text(
                        frame,
                        "Please re-enter the camera view",
                        280,
                        0.9,
                        (255, 255, 255),
                        2,
                    )

                if game["game_over"]:
                    elapsed = game["final_time"]
                    draw_center_text(frame, "GAME OVER", 220, 2, (0, 0, 255), 4)
                    draw_center_text(
                        frame,
                        f"Survived: {elapsed:.2f} seconds",
                        280,
                        1,
                        (255, 255, 255),
                        2,
                    )
                    draw_center_text(
                        frame,
                        "SPACE = restart    M = menu    Q = quit",
                        330,
                        0.75,
                        (255, 255, 255),
                        2,
                    )
                else:
                    timer_scale = 0.85
                    timer_thickness = 2
                    timer_y = 32

                    if game["challenge"] and game["challenge"]["type"] == "FOCUS_ZONE":
                        timer_scale = 1.35
                        timer_thickness = 3
                        timer_y = 46

                    draw_right_text(
                        frame,
                        f"Time: {game['elapsed_time']:.2f}",
                        timer_y,
                        timer_scale,
                        (255, 255, 255),
                        timer_thickness,
                    )

                game["last_time"] = now

                if debug_overlay:
                    draw_debug_overlay(frame, detector.debug_status(raw_openness))

            cv2.imshow("Blink Survival", frame)

            key = cv2.waitKey(1) & 0xFF

            if key == ord("q"):
                break

            if screen == "menu":
                if key == ord("s"):
                    game = reset_game(now)
                    detector.reset_calibration()
                    screen = "game"
                elif key == ord("l"):
                    leaderboard = load_leaderboard()
                    screen = "leaderboard"

            elif screen == "leaderboard":
                if key == ord("m"):
                    screen = "menu"

            elif screen == "game":
                if key == ord("d"):
                    debug_overlay = not debug_overlay

                if key == ord("c"):
                    game = reset_game(now)
                    detector.start_calibration(now)

                if key == ord("b") and game["game_started"] and not game["game_over"]:
                    blink = detector.simulate_blink()
                    game["game_over"] = True
                    game["final_time"] = game["elapsed_time"]
                    update_best_time(leaderboard, username, game["final_time"])

                if key == ord("m") and game["game_over"]:
                    game = reset_game(now)
                    detector.reset_calibration()
                    screen = "menu"

                if key == ord(" ") and game["game_over"]:
                    game = reset_game(now)
                    detector.reset_calibration()

    finally:
        detector.close()
    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
