"""One-lane blink rhythm game with keyboard fallback."""

import json
import math
import random

import cv2
import pygame

from blink_input import BlinkInput


# Gameplay tuning
SCREEN_WIDTH = 720
SCREEN_HEIGHT = 640
FPS = 60
NOTE_SPEED_START = 260
NOTE_SPEED_MAX = 540
SPEED_INCREASE_PER_SECOND = 4.25
NOTE_RADIUS = 22
TARGET_Y = SCREEN_HEIGHT - 105
PERFECT_WINDOW = 18
GOOD_WINDOW = 48
INPUT_BUFFER_MS = 160
RANDOM_GAP_MIN_MS = 650
RANDOM_GAP_MAX_MS = 1750
LONG_PAUSE_MIN_MS = 2200
LONG_PAUSE_MAX_MS = 3200
LONG_PAUSE_CHANCE = 0.20
HOLD_DURATION_MIN_MS = 550
HOLD_DURATION_MAX_MS = 950
PATTERN_INTRO_SECONDS = 10
PATTERN_RAMP_SECONDS = 50
ADVANCED_PATTERN_MAX_CHANCE = 0.38
MAX_MISSES = 10
GAME_DURATION_SECONDS = 60
COUNTDOWN_SECONDS = 3.7
SHOW_DEBUG = False
RECALIBRATE_RECT = pygame.Rect(18, 50, 132, 28)
LEADERBOARD_PATH = "leaderboard.json"

# Colors
BACKGROUND_TOP = (8, 10, 28)
BACKGROUND_BOTTOM = (21, 15, 45)
# Survival mode uses bold white text with yellow prompts and red failure states.
ACCENT_YELLOW = (255, 245, 45)
GOLD = (255, 220, 85)
RED = (255, 70, 85)
WHITE = (240, 245, 255)
MUTED = (130, 145, 180)


def load_leaderboard():
    """Load the shared local leaderboard file."""
    try:
        with open(LEADERBOARD_PATH, "r") as file:
            return json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save_leaderboard(leaderboard):
    """Save leaderboard data without changing its simple JSON format."""
    with open(LEADERBOARD_PATH, "w") as file:
        json.dump(leaderboard, file, indent=2)


def rhythm_key(username):
    """Namespace rhythm scores so survival times stay clean."""
    return f"rhythm:{username}"


def rhythm_best_score(username):
    leaderboard = load_leaderboard()
    return int(leaderboard.get(rhythm_key(username), 0))


def update_rhythm_best(username, score):
    leaderboard = load_leaderboard()
    key = rhythm_key(username)
    if score > int(leaderboard.get(key, 0)):
        leaderboard[key] = int(score)
        save_leaderboard(leaderboard)
        return int(score)
    return int(leaderboard.get(key, 0))


class Note:
    """A falling note in the single blink lane."""

    def __init__(self, kind="TAP", hold_duration_ms=0):
        self.y = -NOTE_RADIUS - 8
        self.pulse_offset = random.random() * math.tau
        self.kind = kind
        self.hold_duration_ms = hold_duration_ms
        self.locked = False
        self.hold_progress = 0.0

    def update(self, dt, speed):
        if not self.locked:
            self.y += speed * dt

    def draw(self, surface, now_ms):
        distance = abs(self.y - TARGET_Y)
        closeness = max(0.0, 1.0 - distance / 260)
        pulse = math.sin(now_ms * 0.012 + self.pulse_offset) * 2 * closeness
        radius = int(NOTE_RADIUS + pulse)
        x = SCREEN_WIDTH // 2
        y = int(self.y)

        if self.kind == "HOLD":
            tail_length = int(70 + self.hold_duration_ms * 0.07)
            pygame.draw.line(
                surface,
                (105, 105, 125),
                (x, y - NOTE_RADIUS),
                (x, y - tail_length),
                9,
            )
            pygame.draw.line(
                surface,
                ACCENT_YELLOW,
                (x, y - NOTE_RADIUS),
                (x, y - tail_length),
                3,
            )

        # A short fading trail makes speed easy to read.
        for index in range(1, 5):
            trail_radius = max(3, radius - index * 4)
            trail_color = (25 + index * 8, 70 + index * 8, 95 + index * 12)
            pygame.draw.circle(surface, trail_color, (x, y - index * 15), trail_radius)

        # The approach ring shrinks onto the note as it nears the target.
        approach_radius = radius + min(52, int(distance * 0.12))
        pygame.draw.circle(surface, (60, 130, 165), (x, y), approach_radius, 2)

        for glow_radius, color in (
            (radius + 12, (18, 80, 110)),
            (radius + 7, (25, 130, 155)),
            (radius + 2, ACCENT_YELLOW),
        ):
            pygame.draw.circle(surface, color, (x, y), glow_radius)

        diamond = [
            (x, y - radius),
            (x + radius, y),
            (x, y + radius),
            (x - radius, y),
        ]
        pygame.draw.polygon(surface, WHITE, diamond)
        center_color = RED if self.kind == "HOLD" else WHITE
        pygame.draw.circle(surface, center_color, (x, y), max(5, radius // 3))

        if self.kind == "HOLD":
            pygame.draw.circle(surface, ACCENT_YELLOW, (x, y), radius + 15, 3)
            if self.locked:
                end_angle = -math.pi / 2 + math.tau * self.hold_progress
                pygame.draw.arc(
                    surface,
                    WHITE,
                    pygame.Rect(x - radius - 20, y - radius - 20, (radius + 20) * 2, (radius + 20) * 2),
                    -math.pi / 2,
                    end_angle,
                    5,
                )


class Particle:
    """Small hit or miss spark."""

    def __init__(self, x, y, color, energetic=False):
        angle = random.uniform(0, math.tau)
        speed = random.uniform(85, 210 if energetic else 150)
        self.x = float(x)
        self.y = float(y)
        self.vx = math.cos(angle) * speed
        self.vy = math.sin(angle) * speed
        self.life = random.uniform(0.35, 0.7)
        self.max_life = self.life
        self.color = color
        self.size = random.randint(2, 5)

    def update(self, dt):
        self.life -= dt
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.vy += 90 * dt

    def draw(self, surface):
        if self.life <= 0:
            return
        alpha = int(255 * self.life / self.max_life)
        color = (*self.color, alpha)
        pygame.draw.circle(surface, color, (int(self.x), int(self.y)), self.size)


class FloatingText:
    """Short-lived judgment text near the target."""

    def __init__(self, text, color):
        self.text = text
        self.color = color
        self.y = TARGET_Y - 72
        self.life = 0.8
        self.max_life = self.life

    def update(self, dt):
        self.life -= dt
        self.y -= 22 * dt

    def draw(self, surface, font):
        if self.life <= 0:
            return
        alpha = int(255 * self.life / self.max_life)
        image = font.render(self.text, True, self.color)
        image.set_alpha(alpha)
        surface.blit(image, image.get_rect(center=(SCREEN_WIDTH // 2, int(self.y))))


def create_gradient():
    """Pre-render the dark vertical gradient."""
    surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
    for y in range(SCREEN_HEIGHT):
        amount = y / SCREEN_HEIGHT
        color = tuple(
            int(top + (bottom - top) * amount)
            for top, bottom in zip(BACKGROUND_TOP, BACKGROUND_BOTTOM)
        )
        pygame.draw.line(surface, color, (0, y), (SCREEN_WIDTH, y))
    return surface


def create_stars(count=48):
    return [
        {
            "x": random.randrange(SCREEN_WIDTH),
            "y": random.randrange(SCREEN_HEIGHT),
            "speed": random.uniform(8, 28),
            "size": random.choice((1, 1, 1, 2)),
        }
        for _ in range(count)
    ]


def setup_blink_input(camera_index=0):
    """Start optional webcam input; keyboard play remains available on failure."""
    try:
        blink_input = BlinkInput(camera_index=camera_index)
    except Exception:
        return None, "Blink: unavailable"

    if not blink_input.is_opened:
        blink_input.release()
        return None, "Blink: unavailable"

    if not blink_input.calibrate(show_window=True):
        blink_input.release()
        cv2.destroyAllWindows()
        return None, "Blink: calibration failed"

    cv2.destroyAllWindows()
    return blink_input, "Blink: ready"


def recalibrate_blink_input(blink_input, camera_index=0):
    """Retry or refresh camera calibration from the in-game button."""
    if blink_input is None:
        return setup_blink_input(camera_index)

    calibrated = blink_input.calibrate(show_window=True)
    cv2.destroyAllWindows()
    if calibrated:
        return blink_input, "Blink: recalibrated"
    return blink_input, "Blink: recalibration failed"


def read_blink_input(blink_input):
    """Return blink/release input, closed-eye state, debug text, and camera frame."""
    if blink_input is None:
        return False, False, "Blink: off (SPACE works)", None

    frame, blink_event, status = blink_input.update()
    if not status["face_found"]:
        return False, False, "Blink: face not found", frame

    eye = status["smoothed_eye_openness"]
    # Use openness directly so long holds remain down after the blink state
    # machine has moved into cooldown.
    eyes_closed = eye is not None and eye < status["threshold"] * 1.08
    debug = f"Blink: on  eye={eye:.3f}  threshold={status['threshold']:.3f}"
    return blink_event, eyes_closed, debug, frame


def new_game(now_ms, best_score=0):
    """Create a fresh countdown/game state."""
    return {
        "state": "COUNTDOWN",
        "state_started_ms": now_ms,
        "play_started_ms": None,
        "next_spawn_ms": None,
        "pattern_queue": [],
        "pattern_name": "",
        "pattern_text_until_ms": 0,
        "notes": [],
        "score": 0,
        "best_score": best_score,
        "combo": 0,
        "best_combo": 0,
        "misses": 0,
        "final_time": 0.0,
        "score_saved": False,
        "buffer_until_ms": 0,
        "active_hold": None,
        "hold_started_ms": 0,
        "suppress_next_blink": False,
        "particles": [],
        "texts": [],
        "target_flash": 0.0,
        "miss_flash": 0.0,
        "shake_time": 0.0,
        "shake_strength": 0,
    }


def burst(game, color, count=18, energetic=False):
    game["particles"].extend(
        Particle(SCREEN_WIDTH // 2, TARGET_Y, color, energetic)
        for _ in range(count)
    )


def register_hit(game, note, judgment):
    """Apply score/combo feedback and remove the judged note."""
    if judgment == "HOLD!":
        game["score"] += 150
        color = ACCENT_YELLOW
        game["shake_time"] = 0.12
        game["shake_strength"] = 3
        burst(game, color, 26, energetic=True)
    elif judgment == "PERFECT":
        game["score"] += 100
        color = GOLD
        game["shake_time"] = 0.12
        game["shake_strength"] = 3
        burst(game, color, 22, energetic=True)
    else:
        game["score"] += 50
        color = WHITE
        burst(game, color, 14)

    game["combo"] += 1
    game["best_combo"] = max(game["best_combo"], game["combo"])
    if note in game["notes"]:
        game["notes"].remove(note)
    if game["active_hold"] is note:
        game["active_hold"] = None
    game["texts"].append(FloatingText(judgment, color))
    game["target_flash"] = 0.22

    if game["combo"] % 10 == 0:
        burst(game, ACCENT_YELLOW, 32, energetic=True)
        game["texts"].append(FloatingText(f"{game['combo']} COMBO!", ACCENT_YELLOW))


def register_miss(game):
    """Apply one miss and its restrained red feedback."""
    game["misses"] += 1
    game["combo"] = 0
    game["texts"].append(FloatingText("MISS", RED))
    game["miss_flash"] = 0.16
    game["shake_time"] = 0.1
    game["shake_strength"] = 2
    burst(game, RED, 9)


def closest_note(game):
    if not game["notes"]:
        return None
    return min(game["notes"], key=lambda note: abs(note.y - TARGET_Y))


def queue_input(game, now_ms):
    """Give both blink and SPACE the same forgiving input buffer."""
    if game["state"] == "PLAYING":
        game["buffer_until_ms"] = now_ms + INPUT_BUFFER_MS


def current_note_speed(game, now_ms):
    """Increase fall speed smoothly over the course of a run."""
    if game["play_started_ms"] is None:
        return NOTE_SPEED_START
    elapsed = max(0, now_ms - game["play_started_ms"]) / 1000
    return min(NOTE_SPEED_MAX, NOTE_SPEED_START + elapsed * SPEED_INCREASE_PER_SECOND)


def random_gap_ms():
    """Mix common irregular gaps with occasional deliberate long rests."""
    if random.random() < LONG_PAUSE_CHANCE:
        return random.randint(LONG_PAUSE_MIN_MS, LONG_PAUSE_MAX_MS)
    return random.randint(RANDOM_GAP_MIN_MS, RANDOM_GAP_MAX_MS)


def choose_pattern(elapsed_seconds=0):
    """Choose mostly singles, introducing advanced patterns over time."""
    ramp = max(
        0.0,
        min(1.0, (elapsed_seconds - PATTERN_INTRO_SECONDS) / PATTERN_RAMP_SECONDS),
    )
    advanced_chance = ADVANCED_PATTERN_MAX_CHANCE * ramp

    if random.random() >= advanced_chance:
        name = "SINGLE"
    else:
        name = random.choices(
            ("DOUBLE", "QUICK TRIPLE", "HOLD", "TAP • HOLD • TAP"),
            weights=(50, 22, 20, 8),
            k=1,
        )[0]
    patterns = {
        "SINGLE": [(0, "TAP")],
        "DOUBLE": [(0, "TAP"), (460, "TAP")],
        "QUICK TRIPLE": [(0, "TAP"), (320, "TAP"), (320, "TAP")],
        "HOLD": [(0, "HOLD")],
        "TAP • HOLD • TAP": [(0, "TAP"), (720, "HOLD"), (620, "TAP")],
    }
    return name, patterns[name]


def spawn_scheduled_note(game, now_ms):
    """Spawn one entry and arrange either the rest of its pattern or a new gap."""
    if not game["pattern_queue"]:
        elapsed = max(0, now_ms - game["play_started_ms"]) / 1000
        game["pattern_name"], game["pattern_queue"] = choose_pattern(elapsed)
        game["pattern_text_until_ms"] = now_ms + 900

    _delay, kind = game["pattern_queue"].pop(0)
    hold_duration = 0
    if kind == "HOLD":
        hold_duration = random.randint(HOLD_DURATION_MIN_MS, HOLD_DURATION_MAX_MS)
    game["notes"].append(Note(kind, hold_duration))

    if game["pattern_queue"]:
        game["next_spawn_ms"] = now_ms + game["pattern_queue"][0][0]
    else:
        game["next_spawn_ms"] = now_ms + random_gap_ms()


def start_hold(game, note, now_ms):
    note.locked = True
    note.y = TARGET_Y
    note.hold_progress = 0.0
    game["active_hold"] = note
    game["hold_started_ms"] = now_ms
    game["suppress_next_blink"] = True
    game["buffer_until_ms"] = 0


def update_hold(game, input_down, now_ms):
    """Advance an engaged hold note; releasing early counts as a miss."""
    note = game["active_hold"]
    if note is None:
        return

    if not input_down:
        if note in game["notes"]:
            game["notes"].remove(note)
        game["active_hold"] = None
        register_miss(game)
        return

    held_ms = now_ms - game["hold_started_ms"]
    note.hold_progress = min(1.0, held_ms / note.hold_duration_ms)
    if held_ms >= note.hold_duration_ms:
        register_hit(game, note, "HOLD!")


def update_game(game, dt, now_ms, input_down=False):
    """Advance countdown, notes, judgments, and end conditions."""
    if game["state"] == "COUNTDOWN":
        if (now_ms - game["state_started_ms"]) / 1000 >= COUNTDOWN_SECONDS:
            game["state"] = "PLAYING"
            game["play_started_ms"] = now_ms
            game["next_spawn_ms"] = now_ms
        return

    if game["state"] != "PLAYING":
        return

    if now_ms >= game["next_spawn_ms"]:
        spawn_scheduled_note(game, now_ms)

    speed = current_note_speed(game, now_ms)
    for note in game["notes"]:
        note.update(dt, speed)

    # Closing eyes or holding SPACE engages a hold as it reaches the target.
    if game["active_hold"] is None and input_down:
        note = closest_note(game)
        if (
            note is not None
            and note.kind == "HOLD"
            and abs(note.y - TARGET_Y) <= GOOD_WINDOW
        ):
            start_hold(game, note, now_ms)

    update_hold(game, input_down, now_ms)

    # A buffered input waits briefly for the closest note to enter the window.
    if game["buffer_until_ms"] and game["active_hold"] is None:
        note = closest_note(game)
        if note is not None:
            distance = abs(note.y - TARGET_Y)
            if note.kind == "HOLD" and distance <= GOOD_WINDOW and input_down:
                start_hold(game, note, now_ms)
            elif note.kind == "TAP" and distance <= PERFECT_WINDOW:
                register_hit(game, note, "PERFECT")
                game["buffer_until_ms"] = 0
            elif note.kind == "TAP" and distance <= GOOD_WINDOW:
                register_hit(game, note, "GOOD")
                game["buffer_until_ms"] = 0

        if game["buffer_until_ms"] and now_ms > game["buffer_until_ms"]:
            register_miss(game)
            game["buffer_until_ms"] = 0

    passed_notes = [
        note
        for note in game["notes"]
        if not note.locked and note.y > TARGET_Y + GOOD_WINDOW
    ]
    for note in passed_notes:
        game["notes"].remove(note)
        register_miss(game)

    elapsed = (now_ms - game["play_started_ms"]) / 1000
    if game["misses"] >= MAX_MISSES or elapsed >= GAME_DURATION_SECONDS:
        game["state"] = "GAME_OVER"
        game["state_started_ms"] = now_ms
        game["final_time"] = min(GAME_DURATION_SECONDS, elapsed)
        game["buffer_until_ms"] = 0
        game["active_hold"] = None


def update_effects(game, stars, dt):
    for star in stars:
        star["y"] += star["speed"] * dt
        if star["y"] >= SCREEN_HEIGHT:
            star["y"] = 0
            star["x"] = random.randrange(SCREEN_WIDTH)

    for particle in game["particles"]:
        particle.update(dt)
    game["particles"] = [particle for particle in game["particles"] if particle.life > 0]

    for text in game["texts"]:
        text.update(dt)
    game["texts"] = [text for text in game["texts"] if text.life > 0]

    game["target_flash"] = max(0.0, game["target_flash"] - dt)
    game["miss_flash"] = max(0.0, game["miss_flash"] - dt)
    game["shake_time"] = max(0.0, game["shake_time"] - dt)


def draw_text(surface, font, text, position, color=WHITE, anchor="topleft"):
    image = font.render(text, True, color)
    rect = image.get_rect()
    setattr(rect, anchor, position)
    surface.blit(image, rect)


def camera_frame_to_surface(frame):
    """Crop and convert the OpenCV frame for Pygame's RGB display."""
    if frame is None:
        return None

    height, width = frame.shape[:2]
    target_ratio = SCREEN_WIDTH / SCREEN_HEIGHT
    source_ratio = width / height
    if source_ratio > target_ratio:
        crop_width = int(height * target_ratio)
        left = (width - crop_width) // 2
        frame = frame[:, left : left + crop_width]
    else:
        crop_height = int(width / target_ratio)
        top = (height - crop_height) // 2
        frame = frame[top : top + crop_height, :]

    frame = cv2.resize(frame, (SCREEN_WIDTH, SCREEN_HEIGHT))
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    return pygame.image.frombuffer(
        rgb_frame.tobytes(),
        (SCREEN_WIDTH, SCREEN_HEIGHT),
        "RGB",
    ).convert()


def draw_background(surface, gradient, stars, now_ms, camera_surface=None):
    if camera_surface is not None:
        surface.blit(camera_surface, (0, 0))
        # Dim the feed in place so notes remain readable without per-frame allocations.
        surface.fill((72, 72, 88), special_flags=pygame.BLEND_RGB_MULT)
    else:
        surface.blit(gradient, (0, 0))

    for star in stars:
        brightness = int(80 + 45 * math.sin(now_ms * 0.002 + star["x"]))
        pygame.draw.circle(
            surface,
            (brightness, brightness, min(220, brightness + 50)),
            (int(star["x"]), int(star["y"])),
            star["size"],
        )

    grid_offset = int(now_ms * 0.025) % 48
    for y in range(grid_offset, SCREEN_HEIGHT, 48):
        pygame.draw.line(surface, (25, 25, 58), (0, y), (SCREEN_WIDTH, y), 1)

    lane = pygame.Rect(SCREEN_WIDTH // 2 - 95, 0, 190, SCREEN_HEIGHT)
    pygame.draw.rect(surface, (14, 18, 42), lane)
    pygame.draw.line(surface, (35, 55, 90), lane.topleft, lane.bottomleft, 2)
    pygame.draw.line(surface, (35, 55, 90), lane.topright, lane.bottomright, 2)


def draw_target(surface, game, now_ms):
    x = SCREEN_WIDTH // 2
    pulse = int(3 * math.sin(now_ms * 0.008))
    flash = game["target_flash"] > 0
    color = WHITE if flash else ACCENT_YELLOW
    pygame.draw.line(surface, (30, 90, 110), (110, TARGET_Y), (SCREEN_WIDTH - 110, TARGET_Y), 2)
    pygame.draw.circle(surface, (20, 70, 90), (x, TARGET_Y), NOTE_RADIUS + 17 + pulse, 5)
    pygame.draw.circle(surface, color, (x, TARGET_Y), NOTE_RADIUS + 9 + pulse, 3)
    pygame.draw.circle(surface, (15, 20, 43), (x, TARGET_Y), NOTE_RADIUS)


def draw_countdown(surface, game, huge_font, now_ms):
    elapsed = (now_ms - game["state_started_ms"]) / 1000
    if elapsed < 1:
        text = "3"
    elif elapsed < 2:
        text = "2"
    elif elapsed < 3:
        text = "1"
    else:
        text = "GO!"
    draw_text(surface, huge_font, text, (SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2), GOLD, "center")


def draw_ui(surface, game, fonts, blink_status, show_debug, now_ms):
    font, small_font, big_font, huge_font = fonts
    draw_text(
        surface,
        small_font,
        "STARING CONTEST FINAL BOSS  •  RHYTHM",
        (SCREEN_WIDTH // 2, 7),
        WHITE,
        "midtop",
    )
    draw_text(surface, font, f"SCORE  {game['score']:06}", (18, 16))
    draw_text(surface, font, f"{game['combo']}x", (SCREEN_WIDTH // 2, 27), ACCENT_YELLOW, "midtop")
    draw_text(surface, font, f"MISS  {game['misses']}/{MAX_MISSES}", (SCREEN_WIDTH - 18, 16), RED, "topright")

    mouse_over = RECALIBRATE_RECT.collidepoint(pygame.mouse.get_pos())
    button_color = (43, 72, 108) if mouse_over else (28, 43, 72)
    pygame.draw.rect(surface, button_color, RECALIBRATE_RECT, border_radius=7)
    pygame.draw.rect(surface, ACCENT_YELLOW, RECALIBRATE_RECT, 1, border_radius=7)
    draw_text(surface, small_font, "C  RECALIBRATE", RECALIBRATE_RECT.center, WHITE, "center")

    if game["state"] == "PLAYING":
        remaining = max(
            0,
            GAME_DURATION_SECONDS - (now_ms - game["play_started_ms"]) / 1000,
        )
        draw_text(surface, small_font, f"{remaining:04.1f}s", (SCREEN_WIDTH - 18, 51), MUTED, "topright")
        speed_multiplier = current_note_speed(game, now_ms) / NOTE_SPEED_START
        draw_text(
            surface,
            small_font,
            f"SPEED {speed_multiplier:.1f}x",
            (SCREEN_WIDTH - 18, 69),
            MUTED,
            "topright",
        )

        if now_ms < game["pattern_text_until_ms"]:
            cue = game["pattern_name"]
            cue_color = RED if "HOLD" in cue else ACCENT_YELLOW
            draw_text(surface, small_font, cue, (SCREEN_WIDTH // 2, 70), cue_color, "midtop")

        nearby_hold = next(
            (
                note
                for note in game["notes"]
                if note.kind == "HOLD" and abs(note.y - TARGET_Y) < 190
            ),
            None,
        )
        if game["active_hold"] is not None:
            hold_prompt = "KEEP EYES CLOSED / HOLD SPACE"
        elif nearby_hold is not None:
            hold_prompt = "HOLD NOTE"
        else:
            hold_prompt = None
        if hold_prompt:
            draw_text(
                surface,
                small_font,
                hold_prompt,
                (SCREEN_WIDTH // 2, TARGET_Y + 54),
                ACCENT_YELLOW,
                "midtop",
            )

    for text in game["texts"]:
        text.draw(surface, big_font)

    if game["state"] == "COUNTDOWN":
        draw_countdown(surface, game, huge_font, now_ms)
    elif game["state"] == "GAME_OVER":
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((4, 5, 18, 210))
        surface.blit(overlay, (0, 0))
        draw_text(surface, huge_font, "RHYTHM COMPLETE", (SCREEN_WIDTH // 2, 220), ACCENT_YELLOW, "center")
        draw_text(
            surface,
            big_font,
            f"Score  {game['score']}    Best  {game['best_score']}",
            (SCREEN_WIDTH // 2, 290),
            WHITE,
            "center",
        )
        draw_text(
            surface,
            font,
            f"Time  {game['final_time']:.1f}s   |   Best combo  {game['best_combo']}x   |   Misses  {game['misses']}",
            (SCREEN_WIDTH // 2, 335),
            MUTED,
            "center",
        )
        draw_text(surface, font, "R  RESTART     M  MENU     ESC  QUIT", (SCREEN_WIDTH // 2, 405), ACCENT_YELLOW, "center")

    if show_debug:
        draw_text(surface, small_font, blink_status, (12, SCREEN_HEIGHT - 48), MUTED)

    draw_text(
        surface,
        small_font,
        "SPACE / BLINK   •   R RESTART   •   C CALIBRATE   •   D DEBUG   •   ESC QUIT",
        (SCREEN_WIDTH // 2, SCREEN_HEIGHT - 18),
        MUTED,
        "midbottom",
    )


def main(username="Player", launch_from_app=False, camera_index=0):
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("Staring Contest Final Boss - Rhythm")
    clock = pygame.time.Clock()
    canvas = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
    effects_layer = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
    gradient = create_gradient()
    stars = create_stars()
    fonts = (
        pygame.font.Font(None, 30),
        pygame.font.Font(None, 20),
        pygame.font.Font(None, 48),
        pygame.font.Font(None, 72),
    )

    best_score = rhythm_best_score(username)
    blink_input, blink_status = setup_blink_input(camera_index)
    game = new_game(pygame.time.get_ticks(), best_score)
    show_debug = SHOW_DEBUG
    camera_surface = None
    running = True

    try:
        while running:
            dt = min(clock.tick(FPS) / 1000, 0.05)
            now_ms = pygame.time.get_ticks()
            input_triggered = False
            recalibrate_requested = False

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        if launch_from_app:
                            return "quit"
                        running = False
                    elif event.key == pygame.K_r:
                        recalibrate_requested = True
                    elif event.key == pygame.K_m and game["state"] == "GAME_OVER":
                        if launch_from_app:
                            return "menu"
                    elif event.key == pygame.K_c:
                        recalibrate_requested = True
                    elif event.key == pygame.K_d:
                        show_debug = not show_debug
                    elif event.key == pygame.K_SPACE:
                        input_triggered = True
                elif (
                    event.type == pygame.MOUSEBUTTONDOWN
                    and event.button == 1
                    and RECALIBRATE_RECT.collidepoint(event.pos)
                ):
                    recalibrate_requested = True

            if recalibrate_requested:
                blink_input, blink_status = recalibrate_blink_input(blink_input, camera_index)
                now_ms = pygame.time.get_ticks()
                best_score = rhythm_best_score(username)
                game = new_game(now_ms, best_score)

            blink_event, eyes_closed, blink_status, camera_frame = read_blink_input(blink_input)
            if camera_frame is not None:
                camera_surface = camera_frame_to_surface(camera_frame)

            # A hold's eventual reopening is not also counted as a tap.
            if game["suppress_next_blink"] and not eyes_closed:
                game["suppress_next_blink"] = False
                blink_event = False
            if blink_event:
                input_triggered = True
            if input_triggered:
                queue_input(game, now_ms)

            space_down = pygame.key.get_pressed()[pygame.K_SPACE]
            update_game(game, dt, now_ms, input_down=eyes_closed or space_down)
            if game["state"] == "GAME_OVER" and not game["score_saved"]:
                best_score = update_rhythm_best(username, game["score"])
                game["best_score"] = best_score
                game["score_saved"] = True
            update_effects(game, stars, dt)

            draw_background(canvas, gradient, stars, now_ms, camera_surface)
            draw_target(canvas, game, now_ms)
            for note in game["notes"]:
                note.draw(canvas, now_ms)

            effects_layer.fill((0, 0, 0, 0))
            for particle in game["particles"]:
                particle.draw(effects_layer)
            canvas.blit(effects_layer, (0, 0))

            if game["miss_flash"] > 0:
                flash = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
                flash.fill((150, 10, 30, int(75 * game["miss_flash"] / 0.16)))
                canvas.blit(flash, (0, 0))

            draw_ui(canvas, game, fonts, blink_status, show_debug, now_ms)

            offset = (0, 0)
            if game["shake_time"] > 0:
                strength = game["shake_strength"]
                offset = (random.randint(-strength, strength), random.randint(-strength, strength))
            screen.fill(BACKGROUND_TOP)
            screen.blit(canvas, offset)
            pygame.display.flip()
    finally:
        if blink_input is not None:
            blink_input.release()
        cv2.destroyAllWindows()
        pygame.quit()


if __name__ == "__main__":
    main()
