import os
import glfw
from OpenGL.GL import *
from PIL import Image, ImageEnhance
import sys
import random
import time
import pygame

# ==================== Sound ====================
pygame.mixer.init()
jump_sound = pygame.mixer.Sound(
    r"Sounds/Jump.wav"
)
jump_sound.set_volume(0.3)  

game_play_sound = pygame.mixer.Sound(
    r"Sounds/GamePlay.wav"
)
game_play_sound.set_volume(0.2)  

game_over_sound = pygame.mixer.Sound(
    r"Sounds/GameOver.wav"
)
game_over_sound.set_volume(0.5)


game_over_texture = None
game_over_w = 0
game_over_h = 0


# ==================== Window Settings ====================
WINDOW_WIDTH = 600
WINDOW_HEIGHT = 800

# ==================== Character Variables ====================
x_pos = 300
y_pos = 0   # will initialize after game starts
speed = 3
flip = False

is_jumping = False
y_velocity = 0
jump_speed = 15
gravity = -0.6
ground_y = 0
char_width = 50
char_height = 50

current_texture = None

# ==================== Game State ====================
game_started = False
fall_detected = False
successful_jumps = 0
camera_speed_base = 1.5
camera_speed = camera_speed_base
score = 0  # new: player's score

# ==================== Bounce Effect Variables ====================
bounce_effect = False
bounce_timer = 0
bounce_direction = 0  # 1 for right, -1 for left
bounce_speed = 8

# ==================== Platform Variables ====================
platforms = []

# ==================== Camera ====================
camera_y = 0.0  # how much world is shifted up (player moves up, camera follows)

# ==================== Texture Variables ====================
background_texture = None
wall_texture = None
bar_left_texture = None
bar_middle_texture = None
bar_right_texture = None
ground_texture = None

bar_left_w = bar_middle_w = bar_right_w = 0

# Character textures
idle_texture = None
walk_texture = None
jump_texture = None

# ==================== Safe texture loader ====================
def load_texture(path, brightness=1.0):
    try:
        img = Image.open(path)
    except Exception as e:
        print(f"Failed to open texture: {path}\n   {e}")
        return 0, 0, 0

    img = img.transpose(Image.FLIP_TOP_BOTTOM)
    if brightness != 1.0:
        img = ImageEnhance.Brightness(img).enhance(brightness)

    img_data = img.convert("RGBA").tobytes()
    tex_id = glGenTextures(1)
    glBindTexture(GL_TEXTURE_2D, tex_id)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_REPEAT)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_REPEAT)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, img.width, img.height, 0,
                 GL_RGBA, GL_UNSIGNED_BYTE, img_data)
    glBindTexture(GL_TEXTURE_2D, 0)
    return tex_id, img.width, img.height

# ==================== Draw Character Sprite ====================
def draw_sprite(x, y, texture_id, scale=50, flip_x=False):
    if texture_id == 0:
        glColor3f(1.0, 0.0, 1.0)
        w = scale; h = scale
        glBegin(GL_QUADS)
        glVertex2f(x - w/2, y - h/2)
        glVertex2f(x + w/2, y - h/2)
        glVertex2f(x + w/2, y + h/2)
        glVertex2f(x - w/2, y + h/2)
        glEnd()
        return

    glEnable(GL_TEXTURE_2D)
    glBindTexture(GL_TEXTURE_2D, texture_id)
    w = scale
    h = scale
    glColor3f(1,1,1)
    glBegin(GL_QUADS)
    if flip_x:
        glTexCoord2f(1, 0); glVertex2f(x - w/2, y - h/2)
        glTexCoord2f(0, 0); glVertex2f(x + w/2, y - h/2)
        glTexCoord2f(0, 1); glVertex2f(x + w/2, y + h/2)
        glTexCoord2f(1, 1); glVertex2f(x - w/2, y + h/2)
    else:
        glTexCoord2f(0, 0); glVertex2f(x - w/2, y - h/2)
        glTexCoord2f(1, 0); glVertex2f(x + w/2, y - h/2)
        glTexCoord2f(1, 1); glVertex2f(x + w/2, y + h/2)
        glTexCoord2f(0, 1); glVertex2f(x - w/2, y + h/2)
    glEnd()
    glBindTexture(GL_TEXTURE_2D, 0)
    glDisable(GL_TEXTURE_2D)

# ==================== Platform Class ====================
class Platform:
    def __init__(self, x, y, width, height, is_ground=False):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.is_ground = is_ground

    def draw(self):
        tex_l = bar_left_texture
        tex_m = bar_middle_texture
        tex_r = bar_right_texture
        w_l = bar_left_w
        w_m = bar_middle_w
        w_r = bar_right_w

        if self.is_ground:
            tex_l = tex_m = tex_r = ground_texture
            w_l = w_m = w_r = self.width

        self.draw_part(self.x, self.y, tex_l, w_l, self.height)
        if not self.is_ground:
            middle_total_width = max(0, self.width - (bar_left_w + bar_right_w))
            full_segments = middle_total_width // bar_middle_w if bar_middle_w>0 else 0
            remainder = middle_total_width % bar_middle_w if bar_middle_w>0 else 0
            for i in range(full_segments):
                x_pos = self.x + bar_left_w + i * bar_middle_w
                self.draw_part(x_pos, self.y, bar_middle_texture, bar_middle_w, self.height)
            if remainder>0:
                x_pos = self.x + bar_left_w + full_segments*bar_middle_w
                self.draw_part(x_pos, self.y, bar_middle_texture, remainder, self.height, stretch=True)
            right_x = self.x + self.width - bar_right_w
            self.draw_part(right_x, self.y, bar_right_texture, bar_right_w, self.height)

    def draw_part(self, x, y, texture, tex_w, height, stretch=False):
        if texture==0 or tex_w==0:
            glColor3f(0.5,0.5,0.5)
            glBegin(GL_QUADS)
            glVertex2f(x, y)
            glVertex2f(x + tex_w, y)
            glVertex2f(x + tex_w, y + height)
            glVertex2f(x, y + height)
            glEnd()
            return
        glEnable(GL_TEXTURE_2D)
        glBindTexture(GL_TEXTURE_2D, texture)
        glColor3f(1,1,1)
        glBegin(GL_QUADS)
        if stretch:
            glTexCoord2f(0,0); glVertex2f(x,y)
            glTexCoord2f(1,0); glVertex2f(x+tex_w,y)
            glTexCoord2f(1,1); glVertex2f(x+tex_w,y+height)
            glTexCoord2f(0,1); glVertex2f(x,y+height)
        else:
            glTexCoord2f(0,0); glVertex2f(x,y)
            glTexCoord2f(1,0); glVertex2f(x+tex_w,y)
            glTexCoord2f(1,1); glVertex2f(x+tex_w,y+height)
            glTexCoord2f(0,1); glVertex2f(x,y+height)
        glEnd()
        glDisable(GL_TEXTURE_2D)

# ==================== Platform Generation ====================
def generate_platforms(min_y, max_y):
    global platforms
    wall_width = 75
    y = max([p.y for p in platforms])+random.randint(100,150) if platforms else ground_y + 50
    while y < max_y:
        platform_width = random.randint(100,150)
        x = random.randint(wall_width, WINDOW_WIDTH - wall_width - platform_width)
        platform_height = 40
        platforms.append(Platform(x, y, platform_width, platform_height))
        y += random.randint(80,150)

# ==================== Physics Helpers ====================
def is_character_on_solid_ground():
    global y_pos
    if y_pos <= ground_y + char_height/2:
        y_pos = ground_y + char_height/2
        return True
    player_bottom = y_pos - char_height/2
    for platform in platforms:
        platform_top = platform.y + platform.height
        if (x_pos-25 < platform.x + platform.width and x_pos+25 > platform.x and
            player_bottom >= platform_top - 10 and player_bottom <= platform_top + 10):
            y_pos = platform_top + char_height/2
            return True
    return False

def check_platform_collision():
    global y_pos, y_velocity, is_jumping, successful_jumps, camera_speed, score
    if y_velocity < 0:
        player_bottom = y_pos - char_height/2
        for platform in platforms:
            platform_top = platform.y + platform.height
            if (x_pos - char_width/2 < platform.x + platform.width and
                x_pos + char_width/2 > platform.x and
                player_bottom >= platform_top - 10 and player_bottom <= platform_top + 20):
                
                # Land on the platform
                y_pos = platform_top + char_height/2
                y_velocity = 0
                
                if is_jumping:
                    successful_jumps += 1
                    score += 1  # increment score when landing on a platform
                    # Increase camera speed every 10 jumps
                    if successful_jumps % 10 == 0:
                        camera_speed += 0.5
                        
                is_jumping = False
                return True
    return False

pygame.font.init()
font = pygame.font.SysFont("Arial", 36)

def draw_score():
    global score
    text = f"Score: {score}"
    # Render text to surface
    surface = font.render(text, True, (255, 255, 255))
    data = pygame.image.tostring(surface, "RGBA", True)
    
    # Generate OpenGL texture
    tex_id = glGenTextures(1)
    glBindTexture(GL_TEXTURE_2D, tex_id)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, surface.get_width(), surface.get_height(),
                 0, GL_RGBA, GL_UNSIGNED_BYTE, data)
    
    # Draw texture in screen space
    glMatrixMode(GL_MODELVIEW)
    glPushMatrix()
    glLoadIdentity()  # draw in screen coordinates
    glEnable(GL_TEXTURE_2D)
    glBindTexture(GL_TEXTURE_2D, tex_id)
    x, y = 10, WINDOW_HEIGHT - 50
    w, h = surface.get_width(), surface.get_height()
    glColor3f(1, 1, 1)
    glBegin(GL_QUADS)
    glTexCoord2f(0,0); glVertex2f(x, y)
    glTexCoord2f(1,0); glVertex2f(x + w, y)
    glTexCoord2f(1,1); glVertex2f(x + w, y + h)
    glTexCoord2f(0,1); glVertex2f(x, y + h)
    glEnd()
    glBindTexture(GL_TEXTURE_2D, 0)
    glDisable(GL_TEXTURE_2D)
    glPopMatrix()
    
    glDeleteTextures([tex_id])  # free texture memory

# ==================== Bounce Update ====================
def update_bounce_effect():
    global x_pos, bounce_effect, bounce_timer, bounce_direction
    if bounce_effect and bounce_timer>0:
        x_pos += bounce_direction*bounce_speed*(bounce_timer/10)
        bounce_timer -=1
        if bounce_timer<=0:
            bounce_effect = False
            bounce_timer=0

# ==================== Movement ====================
def update_movement(window):
    global x_pos, flip, bounce_effect, bounce_timer, bounce_direction
    moving = False
    if fall_detected:
        return False
    update_bounce_effect()
    if bounce_effect:
        return True
    wall_width = 75
    char_half = 25
    if glfw.get_key(window, glfw.KEY_RIGHT) == glfw.PRESS:
        x_pos += speed
        flip = False
        moving = True
        if x_pos > WINDOW_WIDTH - wall_width - char_half:
            x_pos = WINDOW_WIDTH - wall_width - char_half
            bounce_effect = True
            bounce_timer = 10
            bounce_direction = -1
    if glfw.get_key(window, glfw.KEY_LEFT) == glfw.PRESS:
        x_pos -= speed
        flip = True
        moving = True
        if x_pos < wall_width + char_half:
            x_pos = wall_width + char_half
            bounce_effect = True
            bounce_timer = 10
            bounce_direction = 1
    return moving

# ==================== Draw Infinite Background ====================
def draw_background():
    if background_texture == 0:
        glColor3f(0.6, 0.8, 1.0)
        glBegin(GL_QUADS)
        glVertex2f(0, 0)
        glVertex2f(WINDOW_WIDTH, 0)
        glVertex2f(WINDOW_WIDTH, WINDOW_HEIGHT)
        glVertex2f(0, WINDOW_HEIGHT)
        glEnd()
        return

    glEnable(GL_TEXTURE_2D)
    glBindTexture(GL_TEXTURE_2D, background_texture)
    glColor3f(1, 1, 1)

    start_y = int(camera_y // WINDOW_HEIGHT) * WINDOW_HEIGHT
    end_y = int((camera_y + WINDOW_HEIGHT*2) // WINDOW_HEIGHT) * WINDOW_HEIGHT

    y = start_y
    while y <= end_y:
        glBegin(GL_QUADS)
        glTexCoord2f(0, 0); glVertex2f(0, y)
        glTexCoord2f(1, 0); glVertex2f(WINDOW_WIDTH, y)
        glTexCoord2f(1, 1); glVertex2f(WINDOW_WIDTH, y + WINDOW_HEIGHT)
        glTexCoord2f(0, 1); glVertex2f(0, y + WINDOW_HEIGHT)
        glEnd()
        y += WINDOW_HEIGHT

    glDisable(GL_TEXTURE_2D)

# ==================== Draw Infinite Walls ====================
def draw_walls():
    wall_w = 75
    start_y = int(camera_y // WINDOW_HEIGHT) * WINDOW_HEIGHT
    end_y = int((camera_y + WINDOW_HEIGHT*2) // WINDOW_HEIGHT) * WINDOW_HEIGHT
    y = start_y

    while y <= end_y:
        if wall_texture == 0:
            glColor3f(0.3, 0.3, 0.3)
            # Left wall
            glBegin(GL_QUADS)
            glVertex2f(0, y)
            glVertex2f(wall_w, y)
            glVertex2f(wall_w, y + WINDOW_HEIGHT)
            glVertex2f(0, y + WINDOW_HEIGHT)
            glEnd()
            # Right wall
            glBegin(GL_QUADS)
            glVertex2f(WINDOW_WIDTH - wall_w, y)
            glVertex2f(WINDOW_WIDTH, y)
            glVertex2f(WINDOW_WIDTH, y + WINDOW_HEIGHT)
            glVertex2f(WINDOW_WIDTH - wall_w, y + WINDOW_HEIGHT)
            glEnd()
        else:
            glEnable(GL_TEXTURE_2D)
            glBindTexture(GL_TEXTURE_2D, wall_texture)
            glColor3f(1, 1, 1)
            # Left
            glBegin(GL_QUADS)
            glTexCoord2f(0,0); glVertex2f(0, y)
            glTexCoord2f(1,0); glVertex2f(wall_w, y)
            glTexCoord2f(1,1); glVertex2f(wall_w, y + WINDOW_HEIGHT)
            glTexCoord2f(0,1); glVertex2f(0, y + WINDOW_HEIGHT)
            glEnd()
            # Right
            glBegin(GL_QUADS)
            glTexCoord2f(0,0); glVertex2f(WINDOW_WIDTH - wall_w, y)
            glTexCoord2f(1,0); glVertex2f(WINDOW_WIDTH, y)
            glTexCoord2f(1,1); glVertex2f(WINDOW_WIDTH, y + WINDOW_HEIGHT)
            glTexCoord2f(0,1); glVertex2f(WINDOW_WIDTH - wall_w, y + WINDOW_HEIGHT)
            glEnd()
            glDisable(GL_TEXTURE_2D)
        y += WINDOW_HEIGHT

def draw_game_over():
    if game_over_texture == 0:
        return

    glEnable(GL_TEXTURE_2D)
    glBindTexture(GL_TEXTURE_2D, game_over_texture)
    glColor3f(1, 1, 1)

    w = 400
    h = 200
    x = WINDOW_WIDTH // 2
    y = WINDOW_HEIGHT // 2

    glBegin(GL_QUADS)
    # NOTE: flipped V coordinates
    glTexCoord2f(0, 1); glVertex2f(x - w/2, y - h/2)
    glTexCoord2f(1, 1); glVertex2f(x + w/2, y - h/2)
    glTexCoord2f(1, 0); glVertex2f(x + w/2, y + h/2)
    glTexCoord2f(0, 0); glVertex2f(x - w/2, y + h/2)
    glEnd()

    glBindTexture(GL_TEXTURE_2D, 0)
    glDisable(GL_TEXTURE_2D)


# ==================== Main Game Loop ====================
def main():
    global background_texture, wall_texture
    global bar_left_texture, bar_middle_texture, bar_right_texture, ground_texture
    global bar_left_w, bar_middle_w, bar_right_w
    global idle_texture, walk_texture, jump_texture, current_texture
    global camera_y, platforms
    global x_pos, y_pos, y_velocity, is_jumping, flip
    global game_started, fall_detected, camera_speed

    if not glfw.init():
        sys.exit()
    window = glfw.create_window(WINDOW_WIDTH, WINDOW_HEIGHT, "Icy Tower", None, None)
    if not window:
        glfw.terminate()
        sys.exit()
    glfw.make_context_current(window)
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    glOrtho(0, WINDOW_WIDTH, 0, WINDOW_HEIGHT, -1,1)
    glMatrixMode(GL_MODELVIEW)
    glEnable(GL_BLEND)
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

    # Load textures
    base_path = r"C:\Users\El-Wattaneya\3 Year CS\First Semester\Computer Graphics\Project\Icy_Tower_Project\Images"
    background_texture,_,_ = load_texture(os.path.join(base_path,"gameBack.png"), 1.5)
    wall_texture,_,_ = load_texture(os.path.join(base_path,"wall.png"))
    bar_left_texture,bar_left_w,_ = load_texture(os.path.join(base_path,"bar_l1.png"))
    bar_middle_texture,bar_middle_w,_ = load_texture(os.path.join(base_path,"bar_m1.png"))
    bar_right_texture,bar_right_w,_ = load_texture(os.path.join(base_path,"bar_r1.png"))
    ground_texture,_,_ = load_texture(os.path.join(base_path,"bar_m1.png"))
    idle_texture,_,_ = load_texture(os.path.join(base_path,"character1_0.gif"))
    walk_texture,_,_ = load_texture(os.path.join(base_path,"character1_1.gif"))
    jump_texture,_,_ = load_texture(os.path.join(base_path,"character1_3.png"))
    current_texture = idle_texture

    game_over_texture, game_over_w, game_over_h = load_texture(
    os.path.join(base_path, "GameOver.png")
)
    print("Game Over Texture ID:", game_over_texture)


    # Platforms
    platforms=[]
    ground_platform = Platform(0, ground_y, WINDOW_WIDTH, 50, is_ground=True)
    platforms.append(ground_platform)
    generate_platforms(ground_y+50, WINDOW_HEIGHT*3)

    x_pos = WINDOW_WIDTH//2
    y_pos = ground_platform.y + ground_platform.height + char_height/2
    camera_y = 0

    last_time = time.time()

    # Start gameplay music immediately
    game_play_sound.play(loops=-1)

    while not glfw.window_should_close(window):
        current_time = time.time()
        dt = current_time - last_time
        last_time = current_time
        glfw.poll_events()
        glClear(GL_COLOR_BUFFER_BIT)

        # Start game on first space press
        if not game_started:
            if glfw.get_key(window, glfw.KEY_SPACE) == glfw.PRESS:
                game_started = True
                y_pos = ground_platform.y + ground_platform.height + char_height/2
                y_velocity = 0
                is_jumping = False

        # Movement: only if not fallen
        if not fall_detected:
            moving = update_movement(window)
        else:
            moving = False
            if not hasattr(main, "game_over_played"):
                game_over_sound.play()
                main.game_over_played = True
                game_play_sound.stop()

        # Physics & gameplay
        if game_started and not fall_detected:
            y_velocity += gravity
            y_pos += y_velocity

            landed = check_platform_collision()
            if not landed and y_pos <= ground_y + char_height/2:
                y_pos = ground_y + char_height/2
                y_velocity = 0
                is_jumping=False

            if glfw.get_key(window, glfw.KEY_SPACE) == glfw.PRESS and not is_jumping and is_character_on_solid_ground():
                y_velocity = jump_speed
                is_jumping = True
                jump_sound.play() 

            camera_y += camera_speed
            threshold = WINDOW_HEIGHT * 0.6
            if y_pos > camera_y + threshold:
                camera_y = y_pos - threshold

            if y_pos + char_height/2 < camera_y:
                fall_detected = True
                if not hasattr(main, "game_over_played"):
                    game_over_sound.play()
                    game_play_sound.stop()
                    main.game_over_played = True


        # Texture update
        if is_jumping:
            current_texture = jump_texture
        elif moving or bounce_effect:
            current_texture = walk_texture
        else:
            current_texture = idle_texture

        # Generate platforms above
        top_needed = camera_y + WINDOW_HEIGHT*2
        if len(platforms)==0 or max(p.y for p in platforms) < top_needed:
            generate_platforms(max([p.y for p in platforms]) if platforms else 0, top_needed)

        # Draw world
        glPushMatrix()
        glTranslatef(0, -camera_y, 0)
        draw_background()
        draw_walls()
        for p in platforms:
            if p.y+p.height >= camera_y-100 and p.y<=camera_y+WINDOW_HEIGHT+200:
                p.draw()
        draw_sprite(x_pos, y_pos, current_texture, scale=50, flip_x=flip)
        glPopMatrix()

# ==================== GAME OVER SCREEN ====================
        if fall_detected:
            glMatrixMode(GL_MODELVIEW)
            glPushMatrix()
            glLoadIdentity()

            glEnable(GL_TEXTURE_2D)
            glBindTexture(GL_TEXTURE_2D, game_over_texture)
            glColor3f(1, 1, 1)

            w = 400
            h = 200
            x = WINDOW_WIDTH // 2
            y = WINDOW_HEIGHT // 2

            glBegin(GL_QUADS)
            glTexCoord2f(0, 0); glVertex2f(x - w/2, y - h/2)
            glTexCoord2f(1, 0); glVertex2f(x + w/2, y - h/2)
            glTexCoord2f(1, 1); glVertex2f(x + w/2, y + h/2)
            glTexCoord2f(0, 1); glVertex2f(x - w/2, y + h/2)
            glEnd()

            glBindTexture(GL_TEXTURE_2D, 0)
            glDisable(GL_TEXTURE_2D)

            glPopMatrix()
            
        draw_score()
        if glfw.get_key(window, glfw.KEY_ESCAPE) == glfw.PRESS:
            glfw.set_window_should_close(window, True)

        glfw.swap_buffers(window)
        time.sleep(max(0,1/60 - dt))
    glfw.terminate()

if __name__=="__main__":
    main()
