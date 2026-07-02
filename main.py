"""Polished exhibit launcher for Staring Contest Final Boss."""

import json
import math
import random
from pathlib import Path

import pygame

import rhythm_mode
import survival_mode


SCREEN_WIDTH = 960
SCREEN_HEIGHT = 640
FPS = 60
MAX_NAME_LENGTH = 12
PROFILE_PATH = Path("player_profile.json")
LEADERBOARD_PATH = Path("leaderboard.json")

BACKGROUND_TOP = (8, 10, 28)
BACKGROUND_BOTTOM = (21, 15, 45)
PANEL = (16, 20, 48)
PANEL_LIGHT = (30, 38, 82)
WHITE = (242, 246, 255)
YELLOW = (255, 235, 80)
CYAN = (80, 220, 255)
PINK = (255, 85, 150)
RED = (255, 70, 85)
MUTED = (142, 154, 188)
DARK = (5, 7, 20)

DEFAULT_PROFILE = {
    "player_name": "",
    "camera_index": 0,
    "fullscreen": False,
}


def ensure_json_file(path, default):
    if not path.exists():
        save_json(path, default)


def load_json(path, default):
    ensure_json_file(path, default)
    try:
        with path.open("r") as file:
            data = json.load(file)
    except (json.JSONDecodeError, OSError):
        data = default.copy() if isinstance(default, dict) else default
        save_json(path, data)
    return data


def save_json(path, data):
    with path.open("w") as file:
        json.dump(data, file, indent=2)


def load_profile():
    profile = load_json(PROFILE_PATH, DEFAULT_PROFILE)
    changed = False
    for key, value in DEFAULT_PROFILE.items():
        if key not in profile:
            profile[key] = value
            changed = True
    if changed:
        save_profile(profile)
    return profile


def save_profile(profile):
    profile["player_name"] = profile.get("player_name", "")[:MAX_NAME_LENGTH]
    profile["camera_index"] = int(profile.get("camera_index", 0))
    profile["fullscreen"] = bool(profile.get("fullscreen", False))
    save_json(PROFILE_PATH, profile)


def load_leaderboard():
    return load_json(LEADERBOARD_PATH, {})


def save_leaderboard(leaderboard):
    save_json(LEADERBOARD_PATH, leaderboard)


def reset_leaderboard():
    save_leaderboard({})


def survival_best_for(username):
    leaderboard = load_leaderboard()
    return float(leaderboard.get(username, 0))


def rhythm_best_for(username):
    leaderboard = load_leaderboard()
    return int(leaderboard.get(f"rhythm:{username}", 0))


def top_survival_scores(limit=5):
    leaderboard = load_leaderboard()
    scores = [
        (name, float(score))
        for name, score in leaderboard.items()
        if not name.startswith("rhythm:")
    ]
    return sorted(scores, key=lambda item: item[1], reverse=True)[:limit]


def top_rhythm_scores(limit=5):
    leaderboard = load_leaderboard()
    scores = [
        (name.removeprefix("rhythm:"), int(score))
        for name, score in leaderboard.items()
        if name.startswith("rhythm:")
    ]
    return sorted(scores, key=lambda item: item[1], reverse=True)[:limit]


def draw_text(surface, font, text, position, color=WHITE, anchor="topleft", shadow=True):
    if shadow:
        shadow_image = font.render(text, True, (0, 0, 0))
        shadow_rect = shadow_image.get_rect()
        setattr(shadow_rect, anchor, (position[0] + 3, position[1] + 3))
        surface.blit(shadow_image, shadow_rect)

    image = font.render(text, True, color)
    rect = image.get_rect()
    setattr(rect, anchor, position)
    surface.blit(image, rect)
    return rect


def draw_gradient(surface):
    for y in range(SCREEN_HEIGHT):
        amount = y / SCREEN_HEIGHT
        color = tuple(
            int(top + (bottom - top) * amount)
            for top, bottom in zip(BACKGROUND_TOP, BACKGROUND_BOTTOM)
        )
        pygame.draw.line(surface, color, (0, y), (SCREEN_WIDTH, y))


class AnimatedBackground:
    def __init__(self):
        self.particles = [
            {
                "x": random.randrange(SCREEN_WIDTH),
                "y": random.randrange(SCREEN_HEIGHT),
                "speed": random.uniform(12, 42),
                "size": random.choice((1, 1, 2, 3)),
                "phase": random.random() * math.tau,
            }
            for _ in range(72)
        ]

    def update(self, dt):
        for particle in self.particles:
            particle["y"] += particle["speed"] * dt
            particle["x"] += math.sin(particle["phase"] + pygame.time.get_ticks() * 0.001) * dt * 10
            if particle["y"] > SCREEN_HEIGHT + 8:
                particle["y"] = -8
                particle["x"] = random.randrange(SCREEN_WIDTH)

    def draw(self, surface, now_ms):
        draw_gradient(surface)

        grid_offset = int(now_ms * 0.025) % 44
        for y in range(grid_offset, SCREEN_HEIGHT, 44):
            pygame.draw.line(surface, (24, 27, 58), (0, y), (SCREEN_WIDTH, y), 1)
        for x in range(0, SCREEN_WIDTH, 80):
            wave = int(math.sin(now_ms * 0.001 + x * 0.02) * 6)
            pygame.draw.line(surface, (19, 24, 52), (x + wave, 0), (x - wave, SCREEN_HEIGHT), 1)

        for particle in self.particles:
            glow = int(90 + 60 * math.sin(now_ms * 0.002 + particle["phase"]))
            color = (glow // 2, min(255, glow + 60), min(255, glow + 90))
            pygame.draw.circle(
                surface,
                color,
                (int(particle["x"]), int(particle["y"])),
                particle["size"],
            )

        scan = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        for y in range(0, SCREEN_HEIGHT, 6):
            scan_alpha = 12 + int(6 * math.sin(now_ms * 0.004 + y * 0.06))
            pygame.draw.line(scan, (255, 255, 255, scan_alpha), (0, y), (SCREEN_WIDTH, y))
        surface.blit(scan, (0, 0))


class Button:
    def __init__(self, label, rect, action):
        self.label = label
        self.rect = pygame.Rect(rect)
        self.action = action
        self.hover = 0.0
        self.press = 0.0

    def update(self, dt, selected, mouse_pos):
        target = 1.0 if selected or self.rect.collidepoint(mouse_pos) else 0.0
        self.hover += (target - self.hover) * min(1.0, dt * 12)
        self.press = max(0.0, self.press - dt * 6)

    def click(self):
        self.press = 1.0

    def draw(self, surface, font, selected=False):
        hover = self.hover
        lift = int(4 * hover - 2 * self.press)
        rect = self.rect.move(0, -lift)
        glow_rect = rect.inflate(int(18 * hover), int(14 * hover))

        if hover > 0.04:
            glow = pygame.Surface(glow_rect.size, pygame.SRCALPHA)
            glow.fill((*CYAN, int(38 * hover)))
            surface.blit(glow, glow_rect)

        base = (
            int(24 + 35 * hover),
            int(30 + 38 * hover),
            int(72 + 58 * hover),
        )
        border = YELLOW if selected else (62, 83, 132)
        pygame.draw.rect(surface, DARK, rect.move(4, 5), border_radius=18)
        pygame.draw.rect(surface, base, rect, border_radius=18)
        pygame.draw.rect(surface, border, rect, 2, border_radius=18)

        text_color = YELLOW if selected else WHITE
        draw_text(surface, font, self.label, rect.center, text_color, "center")


def draw_card(surface, rect, title, value, subtitle, fonts):
    _title_font, _button_font, font, small_font, _tiny_font = fonts
    rect = pygame.Rect(rect)
    pygame.draw.rect(surface, (9, 13, 35), rect.move(4, 6), border_radius=18)
    pygame.draw.rect(surface, PANEL, rect, border_radius=18)
    pygame.draw.rect(surface, (52, 70, 118), rect, 2, border_radius=18)
    draw_text(surface, small_font, title.upper(), (rect.centerx, rect.y + 24), MUTED, "center")
    draw_text(surface, font, value, (rect.centerx, rect.y + 60), YELLOW, "center")
    draw_text(surface, small_font, subtitle, (rect.centerx, rect.y + 92), WHITE, "center")


def draw_leaderboard_panel(surface, rect, title, rows, score_suffix, fonts):
    _title_font, _button_font, font, small_font, tiny_font = fonts
    rect = pygame.Rect(rect)
    panel = pygame.Surface(rect.size, pygame.SRCALPHA)
    panel.fill((14, 18, 44, 218))
    surface.blit(panel, rect)
    pygame.draw.rect(surface, (53, 66, 116), rect, 2, border_radius=16)
    draw_text(surface, small_font, title, (rect.centerx, rect.y + 24), YELLOW, "center")

    if not rows:
        draw_text(surface, tiny_font, "No scores yet", rect.center, MUTED, "center")
        return

    for index, (name, score) in enumerate(rows, start=1):
        y = rect.y + 58 + (index - 1) * 30
        rank_color = YELLOW if index == 1 else WHITE
        draw_text(surface, tiny_font, f"{index}.", (rect.x + 28, y), rank_color, "midleft")
        draw_text(surface, tiny_font, name[:MAX_NAME_LENGTH].upper(), (rect.x + 66, y), WHITE, "midleft")
        if score_suffix == "s":
            value = f"{score:.1f}s"
        else:
            value = f"{int(score)}"
        draw_text(surface, tiny_font, value, (rect.right - 26, y), CYAN, "midright")


def make_fonts():
    return (
        pygame.font.Font(None, 68),
        pygame.font.Font(None, 38),
        pygame.font.Font(None, 31),
        pygame.font.Font(None, 24),
        pygame.font.Font(None, 21),
    )


def open_window(fullscreen=False):
    pygame.init()
    pygame.display.set_caption("Staring Contest Final Boss")
    flags = pygame.FULLSCREEN if fullscreen else 0
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), flags)
    return screen, pygame.time.Clock(), make_fonts()


def clamp_name(text):
    cleaned = "".join(char for char in text if char.isalnum() or char in ("_", "-"))
    return cleaned[:MAX_NAME_LENGTH]


def draw_name_entry(screen, bg, fonts, typed_name, now_ms, prompt="ENTER YOUR NAME"):
    title_font, button_font, font, small_font, _tiny_font = fonts
    bg.draw(screen, now_ms)

    panel = pygame.Rect(240, 145, 480, 330)
    pygame.draw.rect(screen, (10, 14, 36), panel.move(5, 7), border_radius=22)
    pygame.draw.rect(screen, PANEL, panel, border_radius=22)
    pygame.draw.rect(screen, (62, 78, 140), panel, 2, border_radius=22)

    draw_text(screen, button_font, prompt, (panel.centerx, panel.y + 55), YELLOW, "center")
    draw_text(screen, small_font, "12 characters max. Letters, numbers, _ and -.", (panel.centerx, panel.y + 95), MUTED, "center")

    input_rect = pygame.Rect(panel.x + 70, panel.y + 135, panel.width - 140, 62)
    pygame.draw.rect(screen, DARK, input_rect, border_radius=14)
    pygame.draw.rect(screen, CYAN, input_rect, 2, border_radius=14)
    cursor = "_" if (now_ms // 420) % 2 == 0 else ""
    shown = typed_name.upper() + cursor
    draw_text(screen, title_font, shown or cursor, input_rect.center, WHITE, "center")

    draw_text(screen, font, "ENTER  confirm", (panel.centerx, panel.y + 235), YELLOW, "center")
    draw_text(screen, small_font, "BACKSPACE  delete     ESC  cancel", (panel.centerx, panel.y + 276), MUTED, "center")


def draw_title(screen, fonts, now_ms):
    title_font, button_font, _font, small_font, _tiny_font = fonts
    pulse = 1 + 0.04 * math.sin(now_ms * 0.003)
    pygame.draw.circle(screen, (44, 58, 110), (SCREEN_WIDTH // 2, 58), int(24 * pulse))
    pygame.draw.circle(screen, YELLOW, (SCREEN_WIDTH // 2, 58), 13, 3)
    pygame.draw.circle(screen, CYAN, (SCREEN_WIDTH // 2, 58), 4)
    draw_text(screen, title_font, "STARING CONTEST", (SCREEN_WIDTH // 2, 105), WHITE, "center")
    draw_text(screen, button_font, "Final Boss", (SCREEN_WIDTH // 2, 156), YELLOW, "center")
    draw_text(screen, small_font, "Blink. Don't Blink. Repeat.", (SCREEN_WIDTH // 2, 190), MUTED, "center")


def draw_menu(screen, bg, fonts, buttons, selected, profile, now_ms):
    bg.draw(screen, now_ms)
    username = profile["player_name"]
    draw_title(screen, fonts, now_ms)

    _title_font, _button_font, font, small_font, tiny_font = fonts
    draw_text(screen, small_font, f"Now playing as {username.upper()}", (SCREEN_WIDTH // 2, 222), CYAN, "center")

    best_survival = survival_best_for(username)
    best_rhythm = rhythm_best_for(username)
    draw_card(screen, (95, 250, 185, 125), "Best Survival", f"{best_survival:.1f}", "seconds", fonts)
    draw_card(screen, (95, 397, 185, 125), "Best Rhythm", f"{best_rhythm}", "points", fonts)

    mouse_pos = pygame.mouse.get_pos()
    for index, button in enumerate(buttons):
        button.draw(screen, font, selected == index)

    draw_leaderboard_panel(
        screen,
        (665, 250, 220, 160),
        "TOP SURVIVAL",
        top_survival_scores(),
        "s",
        fonts,
    )
    draw_leaderboard_panel(
        screen,
        (665, 430, 220, 160),
        "TOP RHYTHM",
        top_rhythm_scores(),
        "pts",
        fonts,
    )
    draw_text(screen, tiny_font, "Arrow/W/S + Enter, or click.  ESC quits.", (SCREEN_WIDTH // 2, 612), MUTED, "center")


def draw_instructions(screen, bg, fonts, mode, now_ms):
    _title_font, button_font, font, small_font, _tiny_font = fonts
    bg.draw(screen, now_ms)
    panel = pygame.Rect(165, 105, 630, 440)
    pygame.draw.rect(screen, (7, 10, 30), panel.move(5, 7), border_radius=22)
    pygame.draw.rect(screen, PANEL, panel, border_radius=22)
    pygame.draw.rect(screen, (58, 72, 130), panel, 2, border_radius=22)

    title = "SURVIVAL MODE" if mode == "survival" else "RHYTHM MODE"
    draw_text(screen, button_font, title, (panel.centerx, panel.y + 54), YELLOW, "center")

    if mode == "survival":
        lines = [
            "Keep your eyes open as long as possible.",
            "A real blink ends the round.",
            "Leaving the camera pauses instead of instantly losing.",
            "SPACE still acts as a backup fake blink.",
            "After game-over: R restart, M menu, ESC quit.",
        ]
    else:
        lines = [
            "Blink when the falling note reaches the target ring.",
            "Hold notes mean keep your eyes closed briefly.",
            "SPACE works as the backup blink / hold input.",
            "C recalibrates. D toggles debug.",
            "After game-over: R restart, M menu, ESC quit.",
        ]

    for index, line in enumerate(lines):
        draw_text(screen, font, line, (panel.centerx, panel.y + 122 + index * 43), WHITE, "center")

    draw_text(screen, small_font, "Calibration starts next. Keep your eyes open.", (panel.centerx, panel.y + 355), MUTED, "center")
    draw_text(screen, font, "ENTER  START     M  MENU     ESC  QUIT", (panel.centerx, panel.y + 395), YELLOW, "center")


def draw_settings(screen, bg, fonts, buttons, selected, profile, status_message, now_ms):
    _title_font, button_font, font, small_font, tiny_font = fonts
    bg.draw(screen, now_ms)
    draw_text(screen, button_font, "SETTINGS", (SCREEN_WIDTH // 2, 92), YELLOW, "center")
    draw_text(screen, small_font, "Simple exhibit controls. Keep it boring; keep it reliable.", (SCREEN_WIDTH // 2, 130), MUTED, "center")

    info = pygame.Rect(105, 178, 285, 300)
    pygame.draw.rect(screen, (8, 12, 34), info.move(4, 6), border_radius=18)
    pygame.draw.rect(screen, PANEL, info, border_radius=18)
    pygame.draw.rect(screen, (55, 70, 125), info, 2, border_radius=18)
    draw_text(screen, small_font, "CURRENT PROFILE", (info.centerx, info.y + 38), YELLOW, "center")
    draw_text(screen, font, profile["player_name"].upper(), (info.centerx, info.y + 92), WHITE, "center")
    draw_text(screen, small_font, f"Camera index: {profile['camera_index']}", (info.centerx, info.y + 142), CYAN, "center")
    fullscreen = "ON" if profile["fullscreen"] else "OFF"
    draw_text(screen, small_font, f"Fullscreen: {fullscreen}", (info.centerx, info.y + 178), CYAN, "center")
    draw_text(screen, tiny_font, "Leaderboard reset only clears scores.", (info.centerx, info.y + 235), MUTED, "center")
    draw_text(screen, tiny_font, "It does not change your player name.", (info.centerx, info.y + 258), MUTED, "center")

    for button in buttons:
        button.draw(screen, font, buttons.index(button) == selected)

    if status_message:
        draw_text(screen, small_font, status_message, (SCREEN_WIDTH // 2, 550), YELLOW, "center")
    draw_text(screen, tiny_font, "Arrow/W/S + Enter, or click.  ESC/M returns to menu.", (SCREEN_WIDTH // 2, 612), MUTED, "center")


def build_menu_buttons():
    x = 360
    y = 252
    w = 250
    h = 58
    gap = 18
    return [
        Button("▶  Survival Mode", (x, y, w, h), "survival"),
        Button("♫  Rhythm Mode", (x, y + (h + gap), w, h), "rhythm"),
        Button("⚙  Settings", (x, y + (h + gap) * 2, w, h), "settings"),
        Button("✕  Quit", (x, y + (h + gap) * 3, w, h), "quit"),
    ]


def build_settings_buttons(profile):
    x = 450
    y = 185
    w = 315
    h = 54
    gap = 16
    fullscreen = "ON" if profile["fullscreen"] else "OFF"
    return [
        Button("Change Player Name", (x, y, w, h), "change_name"),
        Button(f"Camera Selection: {profile['camera_index']}", (x, y + (h + gap), w, h), "camera"),
        Button(f"Toggle Fullscreen: {fullscreen}", (x, y + (h + gap) * 2, w, h), "fullscreen"),
        Button("Reset Leaderboard", (x, y + (h + gap) * 3, w, h), "reset_leaderboard"),
        Button("Back", (x, y + (h + gap) * 4, w, h), "back"),
    ]


def update_buttons(buttons, selected, dt):
    mouse_pos = pygame.mouse.get_pos()
    for index, button in enumerate(buttons):
        button.update(dt, selected == index, mouse_pos)


def select_from_mouse(buttons, pos):
    for index, button in enumerate(buttons):
        if button.rect.collidepoint(pos):
            button.click()
            return index, button.action
    return None, None


def run_mode(mode, profile):
    pygame.quit()
    username = profile["player_name"]
    camera_index = profile["camera_index"]
    if mode == "survival":
        return survival_mode.main(username=username, launch_from_app=True, camera_index=camera_index)
    return rhythm_mode.main(username=username, launch_from_app=True, camera_index=camera_index)


def handle_name_typing(event, current_text):
    if event.key == pygame.K_BACKSPACE:
        return current_text[:-1]
    if event.unicode:
        return clamp_name(current_text + event.unicode)
    return current_text


def main():
    ensure_json_file(LEADERBOARD_PATH, {})
    profile = load_profile()
    first_launch = not profile["player_name"]
    screen, clock, fonts = open_window(profile["fullscreen"])
    background = AnimatedBackground()

    app_screen = "name_entry" if first_launch else "menu"
    previous_screen = "menu"
    typed_name = profile["player_name"]
    selected = 0
    menu_buttons = build_menu_buttons()
    settings_buttons = build_settings_buttons(profile)
    status_message = ""
    running = True

    while running:
        dt = min(clock.tick(FPS) / 1000, 0.05)
        now_ms = pygame.time.get_ticks()
        background.update(dt)

        active_buttons = menu_buttons if app_screen == "menu" else settings_buttons
        if app_screen in ("menu", "settings"):
            update_buttons(active_buttons, selected, dt)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.MOUSEMOTION and app_screen in ("menu", "settings"):
                for index, button in enumerate(active_buttons):
                    if button.rect.collidepoint(event.pos):
                        selected = index

            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and app_screen in ("menu", "settings"):
                index, action = select_from_mouse(active_buttons, event.pos)
                if index is not None:
                    selected = index
                    if app_screen == "menu":
                        if action in ("survival", "rhythm"):
                            app_screen = f"{action}_instructions"
                        elif action == "settings":
                            app_screen = "settings"
                            selected = 0
                        elif action == "quit":
                            running = False
                    else:
                        if action == "change_name":
                            previous_screen = "settings"
                            typed_name = profile["player_name"]
                            app_screen = "name_entry"
                        elif action == "camera":
                            profile["camera_index"] = (profile["camera_index"] + 1) % 4
                            save_profile(profile)
                            settings_buttons = build_settings_buttons(profile)
                            status_message = f"Camera set to {profile['camera_index']}"
                        elif action == "fullscreen":
                            profile["fullscreen"] = not profile["fullscreen"]
                            save_profile(profile)
                            screen, clock, fonts = open_window(profile["fullscreen"])
                            settings_buttons = build_settings_buttons(profile)
                            status_message = "Fullscreen toggled"
                        elif action == "reset_leaderboard":
                            reset_leaderboard()
                            status_message = "Leaderboard reset"
                        elif action == "back":
                            app_screen = "menu"
                            selected = 0

            elif event.type == pygame.KEYDOWN:
                if app_screen == "name_entry":
                    if event.key == pygame.K_ESCAPE and profile["player_name"]:
                        typed_name = profile["player_name"]
                        app_screen = previous_screen
                    elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                        if typed_name:
                            profile["player_name"] = typed_name
                            save_profile(profile)
                            settings_buttons = build_settings_buttons(profile)
                            app_screen = previous_screen if not first_launch else "menu"
                            first_launch = False
                    else:
                        typed_name = handle_name_typing(event, typed_name)
                    continue

                if event.key == pygame.K_ESCAPE:
                    if app_screen in ("survival_instructions", "rhythm_instructions", "settings"):
                        app_screen = "menu"
                        selected = 0
                    else:
                        running = False
                elif app_screen in ("survival_instructions", "rhythm_instructions"):
                    if event.key == pygame.K_m:
                        app_screen = "menu"
                    elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                        mode = "survival" if app_screen.startswith("survival") else "rhythm"
                        result = run_mode(mode, profile)
                        if result == "quit":
                            running = False
                            break
                        screen, clock, fonts = open_window(profile["fullscreen"])
                        background = AnimatedBackground()
                        app_screen = "menu"
                        selected = 0
                        menu_buttons = build_menu_buttons()
                        settings_buttons = build_settings_buttons(profile)
                elif app_screen in ("menu", "settings"):
                    buttons = menu_buttons if app_screen == "menu" else settings_buttons
                    if event.key in (pygame.K_DOWN, pygame.K_s):
                        selected = (selected + 1) % len(buttons)
                    elif event.key in (pygame.K_UP, pygame.K_w):
                        selected = (selected - 1) % len(buttons)
                    elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                        action = buttons[selected].action
                        buttons[selected].click()
                        if app_screen == "menu":
                            if action in ("survival", "rhythm"):
                                app_screen = f"{action}_instructions"
                            elif action == "settings":
                                app_screen = "settings"
                                selected = 0
                            elif action == "quit":
                                running = False
                        else:
                            if action == "change_name":
                                previous_screen = "settings"
                                typed_name = profile["player_name"]
                                app_screen = "name_entry"
                            elif action == "camera":
                                profile["camera_index"] = (profile["camera_index"] + 1) % 4
                                save_profile(profile)
                                settings_buttons = build_settings_buttons(profile)
                                status_message = f"Camera set to {profile['camera_index']}"
                            elif action == "fullscreen":
                                profile["fullscreen"] = not profile["fullscreen"]
                                save_profile(profile)
                                screen, clock, fonts = open_window(profile["fullscreen"])
                                settings_buttons = build_settings_buttons(profile)
                                status_message = "Fullscreen toggled"
                            elif action == "reset_leaderboard":
                                reset_leaderboard()
                                status_message = "Leaderboard reset"
                            elif action == "back":
                                app_screen = "menu"
                                selected = 0
                    elif app_screen == "settings" and event.key == pygame.K_m:
                        app_screen = "menu"
                        selected = 0

        if not running:
            break

        if app_screen == "name_entry":
            draw_name_entry(screen, background, fonts, typed_name, now_ms)
        elif app_screen == "menu":
            draw_menu(screen, background, fonts, menu_buttons, selected, profile, now_ms)
        elif app_screen == "settings":
            draw_settings(screen, background, fonts, settings_buttons, selected, profile, status_message, now_ms)
        elif app_screen == "survival_instructions":
            draw_instructions(screen, background, fonts, "survival", now_ms)
        elif app_screen == "rhythm_instructions":
            draw_instructions(screen, background, fonts, "rhythm", now_ms)

        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()
