"""
Platformer Template
"""
import arcade


# --- Constants
SCREEN_TITLE = "Platformer"

SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600

# Constants used to scale our sprites from their original size
CHARACTER_SCALING = 1.3
TILE_SCALING = 2
COIN_SCALING = 2
SPRITE_PIXEL_SIZE = 16
GRID_PIXEL_SIZE = SPRITE_PIXEL_SIZE * TILE_SCALING

# Constants used to track if the player is facing left or right
RIGHT_FACING = 0
LEFT_FACING = 1

# Movement speed of player, in pixels per frame
PLAYER_MOVEMENT_SPEED = 3
GRAVITY = 1
PLAYER_JUMP_SPEED = 15


# Player starting position
PLAYER_START_X = 128
PLAYER_START_Y = 128

# Layer Names from our TileMap
LAYER_NAME_MOVING_PLATFORMS = "moving_platforms"
LAYER_NAME_PLATFORMS = "hard"
LAYER_NAME_COINS = "pets"
LAYER_NAME_FOREGROUND = "table" #выше этого слоя уже front
LAYER_NAME_BACKGROUND = "back"
LAYER_NAME_DONT_TOUCH = "dont_touch"
LAYER_NAME_LADDERS = "ladders"
LAYER_NAME_PLAYER = "Player"

#начальное значение жизней
START_HEALS = 0

def load_texture_pair(filename):
    """
    Load a texture pair, with the second being a mirror image.
    """
    return [
        arcade.load_texture(filename),
        arcade.load_texture(filename, flipped_horizontally=True),
    ]


class PlayerCharacter(arcade.Sprite):
    """Player Sprite"""

    def __init__(self):

        # Set up parent class
        super().__init__()

        # Default to face-right
        self.character_face_direction = RIGHT_FACING

        # Used for flipping between image sequences
        self.cur_texture = 0
        self.scale = CHARACTER_SCALING

        # Track our state
        self.jumping = False
        self.climbing = False
        self.is_on_ladder = False

        # --- Load Textures ---

        main_path = "./img/player/player"

        # Load textures for idle standing
        self.idle_texture_pair = load_texture_pair(f"{main_path}_idle.png")
        self.jump_texture_pair = load_texture_pair(f"{main_path}_jump.png")
        self.fall_texture_pair = load_texture_pair(f"{main_path}_fall.png")

        # Load textures for walking
        self.walk_textures = []
        texture = load_texture_pair(f"{main_path}_walk0.png")
        self.walk_textures.append(texture)
        texture = load_texture_pair(f"{main_path}_walk1.png")
        self.walk_textures.append(texture)


        # Load textures for climbing
        self.climbing_textures = []
        texture = arcade.load_texture(f"{main_path}_climb0.png")
        self.climbing_textures.append(texture)
        texture = arcade.load_texture(f"{main_path}_climb1.png")
        self.climbing_textures.append(texture)

        # Set the initial texture
        self.texture = self.idle_texture_pair[0]

        # Hit box will be set based on the first image used. If you want to specify
        # a different hit box, you can do it like the code below.
        # set_hit_box = [[-22, -64], [22, -64], [22, 28], [-22, 28]]
        self.hit_box = self.texture.hit_box_points


    def update_animation(self, delta_time: float = 1 / 60):

        # Figure out if we need to flip face left or right
        if self.change_x < 0 and self.character_face_direction == RIGHT_FACING:
            self.character_face_direction = LEFT_FACING
        elif self.change_x > 0 and self.character_face_direction == LEFT_FACING:
            self.character_face_direction = RIGHT_FACING

        # Climbing animation
        if self.is_on_ladder:
            self.climbing = True
        if not self.is_on_ladder and self.climbing:
            self.climbing = False
        if self.climbing and abs(self.change_y) > 1:
            self.cur_texture += 1
            if self.cur_texture > 1:
                self.cur_texture = 0
        if self.climbing:
            self.texture = self.climbing_textures[self.cur_texture]
            return

        # Jumping animation
        if self.change_y > 0 and not self.is_on_ladder:
            self.texture = self.jump_texture_pair[self.character_face_direction]
            return
        elif self.change_y < 0 and not self.is_on_ladder:
            self.texture = self.fall_texture_pair[self.character_face_direction]
            return

        # Idle animation
        if self.change_x == 0:
            self.texture = self.idle_texture_pair[self.character_face_direction]
            return

        # Walking animation
        self.cur_texture += 1
        if self.cur_texture > 1:
            self.cur_texture = 0
        self.texture = self.walk_textures[self.cur_texture][
            self.character_face_direction
        ]



class GameView(arcade.View):
    """
    Main application class.
    """

    def __init__(self, level, heals):

        # Call the parent class and set up the window
        #super().__init__(SCREEN_WIDTH, SCREEN_HEIGHT,SCREEN_TITLE, resizable=True)
        #super().__init__(SCREEN_WIDTH, SCREEN_HEIGHT, SCREEN_TITLE, fullscreen=True)        
        super().__init__()
    
        #arcade.set_viewport(0, self.window.width, 0, self.window.height)
        
        # Track the current state of what key is pressed
        self.window.set_mouse_visible(False)
        self.left_pressed = False
        self.right_pressed = False
        self.up_pressed = False
        self.down_pressed = False
        self.jump_needs_reset = False
        
        
        # Our TileMap Object
        self.tile_map = None

        # Our Scene Object
        self.scene = None

        # Separate variable that holds the player sprite
        self.player_sprite = None

        # Our physics engine
        self.physics_engine = None

        # A Camera that can be used for scrolling the screen
        self.camera_sprites = None

        # A non-scrolling camera that can be used to draw GUI elements
        self.camera_gui = None

        # Keep track of the score
        self.score = 0
        
        self.max_score = [3,4,3,3,3,1] #на первом уровне 3, на втором 4 и т.д.
        self.pets_name = ['Кошки', 'Куры', 'Щенки', 'Еноты', 'Птицы', 'Медведь']

        # What key is pressed down?
        self.left_key_down = False
        self.right_key_down = False
        
        # Where is the right edge of the map?
        self.end_of_map = 0

        # Level
        self.level = level
        self.reset_score = True

        self.heals = heals

        self.heals_count_list = None

        # Load sounds
        self.cat_sound = arcade.load_sound("./sounds/cat.mp3")
        self.jump_sound = arcade.load_sound("./sounds/jump.mp3")
        self.game_over_sound = arcade.load_sound("./sounds/gameover.mp3")

    def setup(self):
        """Set up the game here. Call this function to restart the game."""

        # Setup the Cameras
        self.camera_sprites = arcade.Camera(self.window.width, self.window.height)#когда приложение было на основе окна а не представления, было без window
        self.camera_gui = arcade.Camera(self.window.width, self.window.height)

        # Name of map file to load
        map_name = f"./level_{self.level}.json"

        # Layer specific options are defined based on Layer names in a dictionary
        # Doing this will make the SpriteList for the platforms layer
        # use spatial hashing for detection.
        layer_options = {
            "hard": {
                "use_spatial_hash": True,
            },
            "pets": {
                "use_spatial_hash": True,
            },
            "table": {
                "use_spatial_hash": True,
            },
            "moving_platforms": {
                "use_spatial_hash": True,
            },
            "ladder": {
                "use_spatial_hash": True,
            },
            "exit": {
                "use_spatial_hash": True,
            },
            "heals": {
                "use_spatial_hash": True,
            },
        }

        # Read in the tiled map
        self.tile_map = arcade.load_tilemap(map_name, TILE_SCALING, layer_options)

        # Initialize Scene with our TileMap, this will automatically add all layers
        # from the map as SpriteLists in the scene in the proper order.
        self.scene = arcade.Scene.from_tilemap(self.tile_map)

        # Set the background color
        if self.tile_map.background_color:
            arcade.set_background_color(self.tile_map.background_color)

        # Keep track of the score
        if self.reset_score:
            self.score = 0
        self.reset_score = True

        self.scene.add_sprite_list_after("Player", LAYER_NAME_FOREGROUND)

        # Set up the player, specifically placing it at these coordinates.
        self.player_sprite = PlayerCharacter()
        self.player_sprite.center_x = PLAYER_START_X
        self.player_sprite.center_y = PLAYER_START_Y
        self.scene.add_sprite(LAYER_NAME_PLAYER, self.player_sprite)

     
        
        # Calculate the right edge of the my_map in pixels
        self.end_of_map = self.tile_map.width * GRID_PIXEL_SIZE
        
        # --- Other stuff
        # Create the 'physics engine'
        self.physics_engine = arcade.PhysicsEnginePlatformer(
            self.player_sprite,
            platforms=self.scene[LAYER_NAME_MOVING_PLATFORMS],
            gravity_constant=GRAVITY,
            ladders=self.scene[LAYER_NAME_LADDERS],
            walls=self.scene[LAYER_NAME_PLATFORMS],
            )




        self.heals_count_list = arcade.SpriteList()
        '''
        hhh = arcade.Sprite("./img/heals.png",1)
        hhh.center_x = 750 * 2
        hhh.center_y = 550 * 2          
        self.heals_count_list.append(hhh)        
        '''
            

    def on_draw(self):
        """Render the screen."""

        # Clear the screen to the background color
        self.clear()

        # Activate the game camera
        self.camera_sprites.use()

        # Draw our Scene
        # Note, if you a want pixelated look, add pixelated=True to the parameters
        self.scene.draw()

        # Activate the GUI camera before drawing GUI elements
        self.camera_gui.use()

        # Draw our score on the screen, scrolling it with the viewport
        max_score_now = self.max_score[self.level - 1]
        pets_name_now = self.pets_name[self.level - 1]
        
        score_text = f"{pets_name_now}: {self.score} из {max_score_now}"
        #heals_text = f"Жизней = {self.heals}"

        arcade.draw_text(score_text,
                         start_x=10,
                         start_y=10,
                         color=arcade.csscolor.WHITE,
                         font_size=18)
        '''                 
        arcade.draw_text(heals_text,
                         start_x=10,
                         start_y=550,
                         color=arcade.csscolor.WHITE,
                         font_size=18)
        '''              
                       
        self.heals_count_list.draw()


    def update_player_speed(self):

        # Calculate speed based on the keys pressed
        self.player_sprite.change_x = 0

        if self.left_key_down and not self.right_key_down:
            self.player_sprite.change_x = -PLAYER_MOVEMENT_SPEED
        elif self.right_key_down and not self.left_key_down:
            self.player_sprite.change_x = PLAYER_MOVEMENT_SPEED

    def process_keychange(self):
        """
        Called when we change a key up/down or we move on/off a ladder.
        """
        # Process up/down
        if self.up_pressed and not self.down_pressed:
            if self.physics_engine.is_on_ladder():
                self.player_sprite.change_y = PLAYER_MOVEMENT_SPEED
            elif (
                self.physics_engine.can_jump(y_distance=10)
                and not self.jump_needs_reset
            ):
                self.player_sprite.change_y = PLAYER_JUMP_SPEED
                self.jump_needs_reset = True
                arcade.play_sound(self.jump_sound)
        elif self.down_pressed and not self.up_pressed:
            if self.physics_engine.is_on_ladder():
                self.player_sprite.change_y = -PLAYER_MOVEMENT_SPEED

        # Process up/down when on a ladder and no movement
        if self.physics_engine.is_on_ladder():
            if not self.up_pressed and not self.down_pressed:
                self.player_sprite.change_y = 0
            elif self.up_pressed and self.down_pressed:
                self.player_sprite.change_y = 0

        # Process left/right
        if self.right_pressed and not self.left_pressed:
            self.player_sprite.change_x = PLAYER_MOVEMENT_SPEED
        elif self.left_pressed and not self.right_pressed:
            self.player_sprite.change_x = -PLAYER_MOVEMENT_SPEED
        else:
            self.player_sprite.change_x = 0

    '''
    def on_key_press(self, key, modifiers):
        """Called whenever a key is pressed."""

        # Jump and ladder
        if key == arcade.key.UP or key == arcade.key.W:
            if self.physics_engine.is_on_ladder():
                self.player_sprite.change_y = PLAYER_MOVEMENT_SPEED
            elif self.physics_engine.can_jump():
                self.player_sprite.change_y = PLAYER_JUMP_SPEED
                arcade.play_sound(self.jump_sound)
        elif key == arcade.key.DOWN or key == arcade.key.S:
            if self.physics_engine.is_on_ladder():
                self.player_sprite.change_y = -PLAYER_MOVEMENT_SPEED
        # Left
        elif key == arcade.key.LEFT or key == arcade.key.A:
            self.left_key_down = True
            self.update_player_speed()

        # Right
        elif key == arcade.key.RIGHT or key == arcade.key.D:
            self.right_key_down = True
            self.update_player_speed()
    '''
    
    def on_key_press(self, key, modifiers):
        """Called whenever a key is pressed."""

        if key == arcade.key.UP or key == arcade.key.W:
            self.up_pressed = True
        elif key == arcade.key.DOWN or key == arcade.key.S:
            self.down_pressed = True
        elif key == arcade.key.LEFT or key == arcade.key.A:
            self.left_pressed = True
        elif key == arcade.key.RIGHT or key == arcade.key.D:
            self.right_pressed = True
        
        self.process_keychange()


        
    def on_key_release(self, key, modifiers):
        """Called when the user releases a key."""

        if key == arcade.key.UP or key == arcade.key.W:
            self.up_pressed = False
            self.jump_needs_reset = False
        elif key == arcade.key.DOWN or key == arcade.key.S:
            self.down_pressed = False
        elif key == arcade.key.LEFT or key == arcade.key.A:
            self.left_pressed = False
        elif key == arcade.key.RIGHT or key == arcade.key.D:
            self.right_pressed = False

        self.process_keychange()

    def center_camera_to_player(self):
        # Find where player is, then calculate lower left corner from that
        screen_center_x = self.player_sprite.center_x - (self.camera_sprites.viewport_width / 2)
        screen_center_y = self.player_sprite.center_y - (self.camera_sprites.viewport_height / 2)

        # Set some limits on how far we scroll
        if screen_center_x < 0:
            screen_center_x = 0
        if screen_center_y < 0:
            screen_center_y = 0
        if screen_center_x > self.end_of_map - 800:
            screen_center_x = self.end_of_map - 800
        
        # Here's our center, move to it
        player_centered = screen_center_x, screen_center_y
        self.camera_sprites.move_to(player_centered)

    def on_update(self, delta_time):
        """Movement and game logic"""

        # Move the player with the physics engine
        self.physics_engine.update()

        # Update animations
        if self.physics_engine.can_jump():
            self.player_sprite.can_jump = False
        else:
            self.player_sprite.can_jump = True

        if self.physics_engine.is_on_ladder() and not self.physics_engine.can_jump():
            self.player_sprite.is_on_ladder = True
            self.process_keychange()
        else:
            self.player_sprite.is_on_ladder = False
            self.process_keychange()

        # Update Animations
        self.scene.update_animation(
            delta_time, [LAYER_NAME_COINS, LAYER_NAME_BACKGROUND, LAYER_NAME_PLAYER]
        )


        self.scene.update([LAYER_NAME_MOVING_PLATFORMS])

        # See if we hit any coins
        coin_hit_list = arcade.check_for_collision_with_list(
            self.player_sprite, self.scene["pets"]
        )
        
        exit_hit_list = arcade.check_for_collision_with_list(
            self.player_sprite, self.scene["exit"]
        )
        
        heals_hit_list = arcade.check_for_collision_with_list(
            self.player_sprite, self.scene["heals"]
        )
        
        
        
        '''
        if self.score == 1:
            self.scene["end_ladder"].visible = True
            view = GameOverView()
            self.window.show_view(view)
        '''
        # Loop through each coin we hit (if any) and remove it
        for coin in coin_hit_list:
            # Remove the coin
            coin.remove_from_sprite_lists()
            # Add one to the score
            self.score += 1
            arcade.play_sound(self.cat_sound)

        
        max_score_now = self.max_score[self.level - 1]
        for i in exit_hit_list:
            if self.score == max_score_now:
              
                # Advance to the next level
                #self.level += 1
                # Make sure to keep the score from this level when setting up the next level
                #self.reset_score = True

                # Load the next level
                
                
                current_level = self.level
                current_heals = self.heals
                finish_level_view = View_dialog_level_finish(current_level,current_heals)
                #game_view.setup()
                self.window.show_view(finish_level_view)
                
        for i in heals_hit_list:
            # Remove the coin
            i.remove_from_sprite_lists()
            # Add one to the score
            self.heals += 1
            arcade.play_sound(self.cat_sound)
            self.heals_count_list.update()
            self.heals_count_list.draw()
            
        self.heals_count_list = arcade.SpriteList()
        for a in range(self.heals):
            hhh = arcade.Sprite("./img/heals.png",2)
            hhh.center_x = 770 - (24 * a)
            hhh.center_y = 570          
            self.heals_count_list.append(hhh)     
            
        
        # Did the player fall off the map?
        if self.player_sprite.center_y < -100:
            self.player_sprite.center_x = PLAYER_START_X
            self.player_sprite.center_y = PLAYER_START_Y

            arcade.play_sound(self.game_over_sound)

        # Did the player touch something they should not?

        if arcade.check_for_collision_with_list(
            self.player_sprite, self.scene[LAYER_NAME_DONT_TOUCH]
        ):
            if self.heals >= 1:
                arcade.play_sound(self.game_over_sound)
                self.heals -= 1
                self.heals_count_list.update()
                self.heals_count_list.draw()
                self.player_sprite.change_x = 0
                self.player_sprite.change_y = 0
                self.player_sprite.center_x = PLAYER_START_X
                self.player_sprite.center_y = PLAYER_START_Y
            else:
                #game_over_view = GameOverView()
                self.window.show_view(GameOverView())                

            

   
        
        # Position the camera
        self.center_camera_to_player()





    def on_resize(self, width, height):
        """ Resize window """
        self.camera_sprites.resize(int(width), int(height))
        self.camera_gui.resize(int(width), int(height))





class StartView(arcade.View):
    
    def __init__(self):
        """ This is run once when we switch to this view """
        super().__init__()
        
       
        self.x1 = 640#координаты и размеры первого пункта меню (Играть)
        self.y1 = 400
        self.w1 = 235
        self.h1 = 77
        
        self.x2 = 640#координаты и размеры второго пункта меню (Выход)
        self.y2 = 200
        self.w2 = 235
        self.h2 = 77
    
    def on_show_view(self):
        """ This is run once when we switch to this view """
        arcade.set_background_color(arcade.csscolor.STEEL_BLUE)

        # Reset the viewport, necessary if we have a scrolling game and we need
        # to reset the viewport back to the start so we can see what we draw.
        arcade.set_viewport(0, self.window.width, 0, self.window.height)
    def on_draw(self):
        """ Draw this view """
        self.clear()
        self.texture = arcade.load_texture("./img/views/start.jpg")
        #self.texture.draw_sized(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2, SCREEN_WIDTH, SCREEN_HEIGHT)
        self.texture.draw_sized(self.window.width / 2, self.window.height / 2, SCREEN_WIDTH, SCREEN_HEIGHT)
        self.texture2 = arcade.load_texture("./img/views/startmenu1.png")
        self.texture2.draw_sized(self.x1, self.y1, self.w1, self.h1) #координаты по ширине и высоте, размеры ширина и высота
        self.texture3 = arcade.load_texture("./img/views/startmenu2.png")
        self.texture3.draw_sized(self.x2, self.y2, self.w2, self.h2)
    '''    
    def on_key_press(self, key, modifiers):
        """Called whenever a key is pressed. """
        if key == arcade.key.F:

            arcade.set_viewport(0, self.window.width, 0, self.window.height)

        if key == arcade.key.S:
            
            self.fullscreen = False
            # Instead of a one-to-one mapping, stretch/squash window to match the
            # constants. This does NOT respect aspect ratio. You'd need to
            # do a bit of math for that.
            arcade.set_viewport(0, SCREEN_WIDTH, 0, SCREEN_HEIGHT)        
        
    '''    
        #self.texture.draw_sized(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2,
        #                        SCREEN_WIDTH / 4, SCREEN_HEIGHT / 4)
        #arcade.draw_text("Приключения Алисы", self.window.width / 2, self.window.height / 3 * 2,
        #                 arcade.color.WHITE, font_size=30, anchor_x="center")
        #arcade.draw_text("Старт", self.window.width / 2, self.window.height / 3,
        #                 arcade.color.BLACK, font_size=20, anchor_x="center")

    def on_mouse_motion(self, _x, _y, _dx, _dy):
        if _x >=500 and _x<=750 and _y<=440 and _y>=350:
            self.w1 = 235*1.2
            self.h1 = 77*1.2
        elif _x >=500 and _x<=750 and _y<=240 and _y>=150:
            self.w2 = 235*1.2
            self.h2 = 77*1.2            
        else:
            self.w1 = 235
            self.h1 = 77            
            self.w2 = 235
            self.h2 = 77
            
    def on_mouse_press(self, _x, _y, _button, _modifiers):
        """ If the user presses the mouse button, start the game. """
        if _x >=500 and _x<=750 and _y<=440 and _y>=350:
            View1 = View_map(next_level = 1, heals = START_HEALS)
            #game_view.setup()
            self.window.show_view(View1)
        elif _x >=500 and _x<=750 and _y<=240 and _y>=150:
            self.window.close()

class View_map(arcade.View):#карта вход в уровень 1

    def __init__(self, next_level, heals):
        """ This is run once when we switch to this view """
        super().__init__()
        
        self.window.set_mouse_visible(True)
        
        self.x1 = 150#координаты и размеры
        self.y1 = 50
        self.w1 = 247
        self.h1 = 58
        self.next_level = next_level
        self.heals = heals

    def on_show_view(self):
        """ This is run once when we switch to this view """
        arcade.set_background_color(arcade.csscolor.STEEL_BLUE)

        # Reset the viewport, necessary if we have a scrolling game and we need
        # to reset the viewport back to the start so we can see what we draw.
        arcade.set_viewport(0, self.window.width, 0, self.window.height)
    def on_draw(self):
        """ Draw this view """
        self.clear()
        self.texture = arcade.load_texture(f"./img/views/map_{self.next_level}.jpg")
        #self.texture.draw_sized(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2, SCREEN_WIDTH, SCREEN_HEIGHT)
        self.texture.draw_sized(self.window.width / 2, self.window.height / 2, SCREEN_WIDTH, SCREEN_HEIGHT)
        self.texture2 = arcade.load_texture("./img/views/next.png")
        self.texture2.draw_sized(self.x1, self.y1, self.w1, self.h1) #координаты по ширине и высоте, размеры ширина и высота


    def on_mouse_motion(self, _x, _y, _dx, _dy):
        if _x >=25 and _x<=275 and _y<=80 and _y>=20:
            self.w1 = 247*1.1
            self.h1 = 58*1.1
        else:
            self.w1 = 247
            self.h1 = 58           

            
    def on_mouse_press(self, _x, _y, _button, _modifiers):
        """ If the user presses the mouse button, start the game. """
        if _x >=25 and _x<=275 and _y<=80 and _y>=20:
            start_level_view = View_dialog_level_start(self.next_level, self.heals)
            #game_view.setup()
            self.window.show_view(start_level_view)



class View_dialog_level_start(arcade.View):
    
    def __init__(self, level, heals):
        """ This is run once when we switch to this view """
        super().__init__()
        
        self.window.set_mouse_visible(True)
        self.level = level
        self.heals = heals
        self.x1 = 150#координаты и размеры
        self.y1 = 50
        self.w1 = 247
        self.h1 = 58

    def on_show_view(self):
        """ This is run once when we switch to this view """
        arcade.set_background_color(arcade.csscolor.STEEL_BLUE)

        # Reset the viewport, necessary if we have a scrolling game and we need
        # to reset the viewport back to the start so we can see what we draw.
        arcade.set_viewport(0, self.window.width, 0, self.window.height)
    def on_draw(self):
        """ Draw this view """
        self.clear()
        self.texture = arcade.load_texture(f"./img/views/level_{self.level}_start.jpg")
        #self.texture.draw_sized(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2, SCREEN_WIDTH, SCREEN_HEIGHT)
        self.texture.draw_sized(self.window.width / 2, self.window.height / 2, SCREEN_WIDTH, SCREEN_HEIGHT)
        self.texture2 = arcade.load_texture("./img/views/next.png")
        self.texture2.draw_sized(self.x1, self.y1, self.w1, self.h1) #координаты по ширине и высоте, размеры ширина и высота


    def on_mouse_motion(self, _x, _y, _dx, _dy):
        if _x >=25 and _x<=275 and _y<=80 and _y>=20:
            self.w1 = 247*1.1
            self.h1 = 58*1.1
        else:
            self.w1 = 247
            self.h1 = 58           

            
    def on_mouse_press(self, _x, _y, _button, _modifiers):
        """ If the user presses the mouse button, start the game. """
        if _x >=25 and _x<=275 and _y<=80 and _y>=20:
            game_view = GameView(self.level, self.heals)
            game_view.setup()
            self.window.show_view(game_view)

class View_dialog_level_finish(arcade.View):
    
    def __init__(self, current_level,current_heals):
        """ This is run once when we switch to this view """
        super().__init__()
        
        self.window.set_mouse_visible(True)
       
        self.x1 = 150#координаты и размеры
        self.y1 = 50
        self.w1 = 247
        self.h1 = 58
        self.current_level = current_level
        self.current_heals = current_heals

    def on_show_view(self):
        """ This is run once when we switch to this view """
        arcade.set_background_color(arcade.csscolor.STEEL_BLUE)

        # Reset the viewport, necessary if we have a scrolling game and we need
        # to reset the viewport back to the start so we can see what we draw.
        arcade.set_viewport(0, self.window.width, 0, self.window.height)
    def on_draw(self):
        """ Draw this view """
        self.clear()
        
        self.texture = arcade.load_texture(f"./img/views/level_{self.current_level}_finish.jpg")
        #self.texture.draw_sized(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2, SCREEN_WIDTH, SCREEN_HEIGHT)
        self.texture.draw_sized(self.window.width / 2, self.window.height / 2, SCREEN_WIDTH, SCREEN_HEIGHT)
        self.texture2 = arcade.load_texture("./img/views/next.png")
        self.texture2.draw_sized(self.x1, self.y1, self.w1, self.h1) #координаты по ширине и высоте, размеры ширина и высота


    def on_mouse_motion(self, _x, _y, _dx, _dy):
        if _x >=25 and _x<=275 and _y<=80 and _y>=20:
            self.w1 = 247*1.1
            self.h1 = 58*1.1
        else:
            self.w1 = 247
            self.h1 = 58           

            
    def on_mouse_press(self, _x, _y, _button, _modifiers):
        """ If the user presses the mouse button, start the game. """
        if _x >=25 and _x<=275 and _y<=80 and _y>=20:
            next_level = self.current_level + 1
            heals = self.current_heals
            map_view = View_map(next_level, heals)
            self.window.show_view(map_view)


                        
class GameOverView(arcade.View):
    """ View to show when game is over """

    def __init__(self):
        """ This is run once when we switch to this view """
        super().__init__()
        self.texture = arcade.load_texture("./img/views/gameover.png")
        

        # Reset the viewport, necessary if we have a scrolling game and we need
        # to reset the viewport back to the start so we can see what we draw.
        arcade.set_viewport(0, SCREEN_WIDTH - 1, 0, SCREEN_HEIGHT - 1)
        
        
    def on_draw(self):
        """ Draw this view """
        self.clear()
        self.texture.draw_sized(self.window.width / 2, self.window.height / 2, SCREEN_WIDTH, SCREEN_HEIGHT)

    def on_mouse_press(self, _x, _y, _button, _modifiers):
        """ If the user presses the mouse button, re-start the game. """
        start_view = StartView()
        #game_view.setup()
        self.window.show_view(start_view)

                         

def main():
    """ Main function """

    #window = arcade.Window(SCREEN_WIDTH, SCREEN_HEIGHT, SCREEN_TITLE, fullscreen=True)
    #window = arcade.Window(SCREEN_WIDTH, SCREEN_HEIGHT, SCREEN_TITLE, resizable=True)
    window = arcade.Window(SCREEN_WIDTH, SCREEN_HEIGHT, SCREEN_TITLE)
    start_view = StartView()
    window.show_view(start_view)
    arcade.run()


if __name__ == "__main__":
    main()