
#
# This is a simple maze-solving game
#
# Game was made with python 3.10 (haven't tested it with different versions)
#
# Requirement: Python 3.10
# Requirement: pip install pygame
# Requirement: At least FHD (1920 x 1080 px) resolution
#
# Be free to give me any ideas how to make the game better
#
# For time saving reasons there is Developer mode
# You can activate it by changing dev_mode variable to True
# It allows you to press F5 while in game and it will show you a guidance line to the end
#


import os, sys, pygame, random, time, threading
from pygame import mixer
from collections import deque

sys.setrecursionlimit(10000)

# Initialize Pygame
pygame.init()
SCREEN_WIDTH, SCREEN_HEIGHT = 1000, 1000
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Shadow Maze – Python game")
clock = pygame.time.Clock()

# Initialize Pygame Mixer and play background music if possible
if os.path.isfile("background_song.mp3"):
    print("BACKGROUND MUSIC FOUND - PLAYING")
    mixer.init()
    mixer.music.load("background_song.mp3")
    mixer.music.play()
    pygame.mixer.music.play(-1)
else:
    print("BACKGROUND MUSIC NOT FOUND")
    

# Colors and settings
COLOR_BG = (30, 30, 30)
COLOR_WALL = (70, 70, 70)
COLOR_PLAYER = (255, 100, 100)
COLOR_FINISH = (100, 255, 100)
COLOR_TEXT = (255, 255, 255)
COLOR_HIGHLIGHT = (255, 215, 0)
ORANGE = (255, 165, 0)
WALL_THICKNESS = 3

# Global flag for Dev mode
dev_mode = False

# Global flag for guidance mode (F5 toggle)
show_guidance = False

# UI Buttons
class Button:
    def __init__(self, rect, text, callback, font_size=30, bg_color=(70,70,70), text_color=(255,255,255)):
        self.rect = pygame.Rect(rect)
        self.text = text
        self.callback = callback
        self.bg_color = bg_color
        self.text_color = text_color
        self.font = pygame.font.SysFont(None, font_size)
        self.active = False
        self.update_render()

    def update_render(self):
        self.render_text = self.font.render(self.text, True, self.text_color)
        self.render_rect = self.render_text.get_rect(center=self.rect.center)

    def draw(self, surface):
        pygame.draw.rect(surface, self.bg_color, self.rect)
        if self.active:
            pygame.draw.rect(surface, COLOR_HIGHLIGHT, self.rect, 3)
        surface.blit(self.render_text, self.render_rect)

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            if self.rect.collidepoint(event.pos):
                self.callback()

# Helper function for drawing text
def draw_text(surface, text, pos, font_size=30, color=COLOR_TEXT):
    font = pygame.font.SysFont(None, font_size)
    render = font.render(text, True, color)
    surface.blit(render, pos)

# Collision detection
def check_collision(new_rect, collidable_rects):
    for rect in collidable_rects:
        if new_rect.colliderect(rect):
            return True
    return False

# Maze generation - Prim's alg
def generate_maze(width, height):
    maze = [[{'N': True, 'S': True, 'E': True, 'W': True} for _ in range(width)] for _ in range(height)]
    in_maze = [[False]*width for _ in range(height)]
    wall_list = []
    start_x, start_y = 0, 0
    in_maze[start_y][start_x] = True
    for direction, (dx, dy) in [('N',(0,-1)), ('S',(0,1)), ('E',(1,0)), ('W',(-1,0))]:
        nx, ny = start_x+dx, start_y+dy
        if 0 <= nx < width and 0 <= ny < height:
            wall_list.append((start_x, start_y, direction))
    while wall_list:
        idx = random.randrange(len(wall_list))
        x, y, direction = wall_list.pop(idx)
        dx, dy = 0, 0
        if direction == 'N': dx, dy = 0, -1
        elif direction == 'S': dx, dy = 0, 1
        elif direction == 'E': dx, dy = 1, 0
        elif direction == 'W': dx, dy = -1, 0
        nx, ny = x+dx, y+dy
        if 0 <= nx < width and 0 <= ny < height and not in_maze[ny][nx]:
            maze[y][x][direction] = False
            if direction == 'N':
                maze[ny][nx]['S'] = False
            elif direction == 'S':
                maze[ny][nx]['N'] = False
            elif direction == 'E':
                maze[ny][nx]['W'] = False
            elif direction == 'W':
                maze[ny][nx]['E'] = False
            in_maze[ny][nx] = True
            for d, (dx2, dy2) in [('N',(0,-1)), ('S',(0,1)), ('E',(1,0)), ('W',(-1,0))]:
                nx2, ny2 = nx+dx2, ny+dy2
                if 0 <= nx2 < width and 0 <= ny2 < height and not in_maze[ny2][nx2]:
                    wall_list.append((nx, ny, d))
    return maze

# Build fixed walls
def build_fixed_walls(maze, maze_width, maze_height, cell_size):
    walls = []
    for y in range(maze_height):
        for x in range(maze_width):
            cell_x = x * cell_size
            cell_y = y * cell_size
            cell = maze[y][x]
            if cell['N']:
                wall = {}
                wall['id'] = f"{x}_{y}_N"
                wall['start'] = (cell_x, cell_y)
                wall['end'] = (cell_x + cell_size, cell_y)
                wall['rect'] = pygame.Rect(cell_x, cell_y, cell_size, WALL_THICKNESS)
                walls.append(wall)
            if cell['W']:
                wall = {}
                wall['id'] = f"{x}_{y}_W"
                wall['start'] = (cell_x, cell_y)
                wall['end'] = (cell_x, cell_y + cell_size)
                wall['rect'] = pygame.Rect(cell_x, cell_y, WALL_THICKNESS, cell_size)
                walls.append(wall)
            if cell['E']:
                wall = {}
                wall['id'] = f"{x}_{y}_E"
                wall['start'] = (cell_x + cell_size, cell_y)
                wall['end'] = (cell_x + cell_size, cell_y + cell_size)
                wall['rect'] = pygame.Rect(cell_x + cell_size - WALL_THICKNESS, cell_y, WALL_THICKNESS, cell_size)
                walls.append(wall)
            if cell['S']:
                wall = {}
                wall['id'] = f"{x}_{y}_S"
                wall['start'] = (cell_x, cell_y + cell_size)
                wall['end'] = (cell_x + cell_size, cell_y + cell_size)
                wall['rect'] = pygame.Rect(cell_x, cell_y + cell_size - WALL_THICKNESS, cell_size, WALL_THICKNESS)
                walls.append(wall)
    return walls

# Fixed walls variables
fixed_walls = []
wall_visual_state = {}
wall_lock = threading.Lock()

# Wall visuals
def update_wall_visual_states():
    while True:
        time.sleep(1)
        with wall_lock:
            for wall in fixed_walls:
                wall_id = wall['id']
                if wall_visual_state.get(wall_id, True):
                    if random.random() < 0.5:
                        wall_visual_state[wall_id] = False
                        if dev_mode:
                            print(f"{time.strftime('%H:%M:%S')} - Wall {wall_id} set to invisible")
                        threading.Timer(5.0, set_wall_visible, args=(wall_id,)).start()

def set_wall_visible(wall_id):
    with wall_lock:
        wall_visual_state[wall_id] = True
    if dev_mode:
        print(f"{time.strftime('%H:%M:%S')} - Wall {wall_id} set to visible")

# Threadning
wall_update_thread = threading.Thread(target=update_wall_visual_states, daemon=True)
wall_update_thread.start()

# Maze-solving alg...
def find_path(start, goal, maze):
    q = deque()
    q.append(start)
    came_from = {}
    came_from[start] = None
    while q:
        current = q.popleft()
        if current == goal:
            break
        x, y = current
        directions = [('N', (0, -1)), ('S', (0, 1)), ('E', (1, 0)), ('W', (-1, 0))]
        for d, (dx, dy) in directions:
            if maze[y][x][d] == False:
                neighbor = (x+dx, y+dy)
                if neighbor not in came_from and 0 <= neighbor[0] < len(maze[0]) and 0 <= neighbor[1] < len(maze):
                    q.append(neighbor)
                    came_from[neighbor] = current
    if goal not in came_from:
        return None
    path = []
    cur = goal
    while cur is not None:
        path.append(cur)
        cur = came_from[cur]
    path.reverse()
    return path

# Global game settings
DIFFICULTIES = {
    "Easy": (20, 20),
    "Medium": (34, 34),
    "Hard": (50, 50)
}
TIME_LIMITS = {
    "None": None,
    "5 Minutes": 300,
    "10 Minutes": 600,
    "15 Minutes": 900,
    "20 Minutes": 1200,
    "1 Hour": 3600
}

selected_difficulty = "Hard"
selected_time_limit = "None"
game_state = "main_menu"   # main_menu, settings, playing, paused, game_over
result_message = ""

maze = None
maze_width = None
maze_height = None
finish_cell = None
cell_size = None
player_x = None
player_y = None
player_speed = 2
player_size = None
game_start_time = None
paused_time_accumulated = 0
pause_start_time = None
time_limit_seconds = None

# UI Buttons
menu_buttons = []
settings_buttons = []
pause_buttons = []
end_buttons = []

# Game starts
def start_game():
    global maze, maze_width, maze_height, finish_cell, cell_size, player_x, player_y, player_size, fixed_walls, wall_visual_state, game_start_time, paused_time_accumulated, time_limit_seconds, game_state
    maze_width, maze_height = DIFFICULTIES[selected_difficulty]
    cell_size = SCREEN_WIDTH // maze_width
    maze = generate_maze(maze_width, maze_height)
    finish_cell = (maze_width - 1, maze_height - 1)
    player_x = cell_size // 2
    player_y = cell_size // 2
    player_size = int(cell_size * 0.5)
    game_start_time = pygame.time.get_ticks()
    paused_time_accumulated = 0
    time_limit_seconds = TIME_LIMITS[selected_time_limit]
    fixed_walls[:] = build_fixed_walls(maze, maze_width, maze_height, cell_size)
    with wall_lock:
        for wall in fixed_walls:
            wall_visual_state[wall['id']] = True
    change_state("playing")

def restart_game():
    start_game()

def return_to_main_menu():
    change_state("main_menu")

def resume_game():
    global paused_time_accumulated, pause_start_time
    if pause_start_time is not None:
        paused_time_accumulated += pygame.time.get_ticks() - pause_start_time
    change_state("playing")

def pause_game():
    global pause_start_time
    pause_start_time = pygame.time.get_ticks()
    change_state("paused")

def change_state(new_state):
    global game_state, pause_start_time
    game_state = new_state
    if new_state != "paused":
        pause_start_time = None

# GUIs / Menus
def build_main_menu():
    global menu_buttons
    menu_buttons = []
    play_button = Button(rect=(400, 300, 200, 50), text="Play", callback=lambda: change_state("settings"))
    exit_button = Button(rect=(400, 400, 200, 50), text="Exit Game", callback=lambda: sys.exit())
    menu_buttons = [play_button, exit_button]

def build_settings_menu():
    global settings_buttons, selected_difficulty, selected_time_limit
    settings_buttons = []
    diff_y = 150
    for diff in DIFFICULTIES.keys():
        btn = Button(rect=(150, diff_y, 200, 40), text=f"Difficulty: {diff}", callback=lambda d=diff: set_difficulty(d))
        btn.active = (diff == selected_difficulty)
        settings_buttons.append(btn)
        diff_y += 50
    time_y = 150
    for tl in TIME_LIMITS.keys():
        btn = Button(rect=(600, time_y, 250, 40), text=f"Time Limit: {tl}", callback=lambda t=tl: set_time_limit(t))
        btn.active = (tl == selected_time_limit)
        settings_buttons.append(btn)
        time_y += 50
    start_btn = Button(rect=(400, 500, 200, 50), text="Start Game", callback=start_game)
    settings_buttons.append(start_btn)

def set_difficulty(diff):
    global selected_difficulty
    selected_difficulty = diff
    build_settings_menu()

def set_time_limit(tl):
    global selected_time_limit
    selected_time_limit = tl
    build_settings_menu()

def build_pause_menu():
    global pause_buttons
    pause_buttons = []
    resume_btn = Button(rect=(400, 300, 200, 50), text="Resume", callback=resume_game)
    restart_btn = Button(rect=(400, 370, 200, 50), text="Restart", callback=restart_game)
    main_menu_btn = Button(rect=(400, 440, 200, 50), text="Main Menu", callback=return_to_main_menu)
    pause_buttons = [resume_btn, restart_btn, main_menu_btn]

def build_end_menu():
    global end_buttons
    end_buttons = []
    restart_btn = Button(rect=(400, 400, 200, 50), text="Restart", callback=restart_game)
    main_menu_btn = Button(rect=(400, 470, 200, 50), text="Main Menu", callback=return_to_main_menu)
    end_buttons = [restart_btn, main_menu_btn]

# Main menu
def draw_main_menu():
    screen.fill(COLOR_BG)
    draw_text(screen, "Shadow Maze", (400, 100), font_size=60)
    for btn in menu_buttons:
        btn.draw(screen)
    pygame.display.flip()

# Settings menu
def draw_settings_menu():
    screen.fill(COLOR_BG)
    draw_text(screen, "Settings", (450, 50), font_size=50)
    for btn in settings_buttons:
        btn.draw(screen)
    pygame.display.flip()

# Pause menu
def draw_pause_menu():
    overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
    overlay.set_alpha(200)
    overlay.fill((0,0,0))
    screen.blit(overlay, (0,0))
    draw_text(screen, "Paused", (450, 200), font_size=50)
    for btn in pause_buttons:
        btn.draw(screen)
    pygame.display.flip()

# End menu
def draw_end_menu(message):
    screen.fill(COLOR_BG)
    draw_text(screen, message, (420, 150), font_size=50)
    for btn in end_buttons:
        btn.draw(screen)
    pygame.display.flip()

# InGame HUD
def draw_in_game_hud(remaining_time):
    if remaining_time is not None:
        minutes = int(remaining_time) // 60
        seconds = int(remaining_time) % 60
        timer_text = f"Time Left: {minutes:02}:{seconds:02}"
        draw_text(screen, timer_text, (20, 20), font_size=30)
    pause_rect = pygame.Rect(900, 20, 80, 40)
    pygame.draw.rect(screen, (100,100,100), pause_rect)
    draw_text(screen, "Pause", (910, 25), font_size=30)
    return pause_rect

# Game loop
def playing_loop():
    global player_x, player_y, game_state, result_message, player_speed, show_guidance
    running = True
    while running and game_state == "playing":
        dt = clock.tick(60)
        current_time = pygame.time.get_ticks()
        effective_time = current_time - game_start_time - paused_time_accumulated
        if time_limit_seconds is not None:
            remaining = time_limit_seconds - effective_time/1000.0
            if remaining <= 0:
                result_message = "Time Over!"
                change_state("game_over")
                break
        else:
            remaining = None

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if pause_button.collidepoint(event.pos):
                    pause_game()
                    return
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_F5 and dev_mode:
                    show_guidance = not show_guidance
                    print(f"{time.strftime('%H:%M:%S')} - Guidance toggled to {show_guidance}")

        # Movement keys
        keys = pygame.key.get_pressed()
        dx = dy = 0
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            dx -= player_speed
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            dx += player_speed
        if keys[pygame.K_UP] or keys[pygame.K_w]:
            dy -= player_speed
        if keys[pygame.K_DOWN] or keys[pygame.K_s]:
            dy += player_speed

        collidable_rects = [wall['rect'] for wall in fixed_walls]
        p_size = player_size
        player_rect = pygame.Rect(int(player_x - p_size//2), int(player_y - p_size//2), p_size, p_size)
        new_rect = player_rect.move(dx, 0)
        if not check_collision(new_rect, collidable_rects):
            player_x += dx
        new_rect = player_rect.move(0, dy)
        if not check_collision(new_rect, collidable_rects):
            player_y += dy

        current_cell = (int(player_x // cell_size), int(player_y // cell_size))
        if current_cell == finish_cell:
            elapsed_time = (current_time - game_start_time - paused_time_accumulated)/1000.0
            result_message = f"Victory! Time: {elapsed_time:.2f} seconds"
            print(f"{time.strftime('%H:%M:%S')} - Game won in {elapsed_time:.2f} seconds")
            change_state("game_over")
            break

        screen.fill(COLOR_BG)
        with wall_lock:
            for wall in fixed_walls:
                if wall_visual_state.get(wall['id'], True):
                    pygame.draw.line(screen, COLOR_WALL, wall['start'], wall['end'], WALL_THICKNESS)
        finish_rect = pygame.Rect(finish_cell[0]*cell_size + cell_size//4,
                                  finish_cell[1]*cell_size + cell_size//4,
                                  cell_size//2, cell_size//2)
        pygame.draw.rect(screen, COLOR_FINISH, finish_rect)
        pygame.draw.rect(screen, COLOR_PLAYER, pygame.Rect(int(player_x - p_size//2), int(player_y - p_size//2), p_size, p_size))
        
        if show_guidance:
            path = find_path(current_cell, finish_cell, maze)
            if path is not None and len(path) > 1:
                path_points = [(x * cell_size + cell_size//2, y * cell_size + cell_size//2) for (x,y) in path]
                pygame.draw.lines(screen, ORANGE, False, path_points, 5)

        shadow = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        shadow.fill((0,0,0,255))
        pygame.draw.circle(shadow, (0,0,0,0), (int(player_x), int(player_y)), 40)
        screen.blit(shadow, (0,0))
        pause_button = draw_in_game_hud(remaining)
        pygame.display.flip()

# Main loop
def main_loop():
    global game_state
    build_main_menu()
    build_settings_menu()
    build_pause_menu()
    build_end_menu()
    while True:
        if game_state == "main_menu":
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit(); sys.exit()
                for btn in menu_buttons:
                    btn.handle_event(event)
            draw_main_menu()
        elif game_state == "settings":
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit(); sys.exit()
                for btn in settings_buttons:
                    btn.handle_event(event)
            draw_settings_menu()
        elif game_state == "playing":
            playing_loop()
        elif game_state == "paused":
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit(); sys.exit()
                for btn in pause_buttons:
                    btn.handle_event(event)
            draw_pause_menu()
        elif game_state == "game_over":
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit(); sys.exit()
                for btn in end_buttons:
                    btn.handle_event(event)
            draw_end_menu(result_message)
        clock.tick(60)

main_loop()

