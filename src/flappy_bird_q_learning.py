#! /usr/bin/env python3

"""Flappy Bird, implemented using Pygame."""

import math
import os
from random import randint
from collections import deque
from collections import Counter
import random

import pygame
from pygame.locals import *


FPS = 60
# FPS = 40
ANIMATION_SPEED = 0.18  # pixels per millisecond
WIN_WIDTH = 284 * 2     # BG image size: 284x512 px; tiled twice
WIN_HEIGHT = 512


class Bird(pygame.sprite.Sprite):
    """Represents the bird controlled by the player.

    The bird is the 'hero' of this game.  The player can make it climb
    (ascend quickly), otherwise it sinks (descends more slowly).  It must
    pass through the space in between pipes (for every pipe passed, one
    point is scored); if it crashes into a pipe, the game ends.

    Attributes:
    x: The bird's X coordinate.
    y: The bird's Y coordinate.
    msec_to_climb: The number of milliseconds left to climb, where a
        complete climb lasts Bird.CLIMB_DURATION milliseconds.

    Constants:
    WIDTH: The width, in pixels, of the bird's image.
    HEIGHT: The height, in pixels, of the bird's image.
    SINK_SPEED: With which speed, in pixels per millisecond, the bird
        descends in one second while not climbing.
    CLIMB_SPEED: With which speed, in pixels per millisecond, the bird
        ascends in one second while climbing, on average.  See also the
        Bird.update docstring.
    CLIMB_DURATION: The number of milliseconds it takes the bird to
        execute a complete climb.
    """

    WIDTH = HEIGHT = 32
    SINK_SPEED = 0.18
    CLIMB_SPEED = 0.3
    CLIMB_DURATION = 333.3

    def __init__(self, x, y, msec_to_climb, images):
        """Initialise a new Bird instance.

        Arguments:
        x: The bird's initial X coordinate.
        y: The bird's initial Y coordinate.
        msec_to_climb: The number of milliseconds left to climb, where a
            complete climb lasts Bird.CLIMB_DURATION milliseconds.  Use
            this if you want the bird to make a (small?) climb at the 
            very beginning of the game.
        images: A tuple containing the images used by this bird.  It
            must contain the following images, in the following order:
                0. image of the bird with its wing pointing upward
                1. image of the bird with its wing pointing downward
        """
        super(Bird, self).__init__()
        self.x, self.y = x, y
        self.msec_to_climb = msec_to_climb
        self._img_wingup, self._img_wingdown = images
        self._mask_wingup = pygame.mask.from_surface(self._img_wingup)
        self._mask_wingdown = pygame.mask.from_surface(self._img_wingdown)

    def update(self, delta_frames=1):
        """Update the bird's position.

        This function uses the cosine function to achieve a smooth climb:
        In the first and last few frames, the bird climbs very little, in the
        middle of the climb, it climbs a lot.
        One complete climb lasts CLIMB_DURATION milliseconds, during which
        the bird ascends with an average speed of CLIMB_SPEED px/ms.
        This Bird's msec_to_climb attribute will automatically be
        decreased accordingly if it was > 0 when this method was called.

        Arguments:
        delta_frames: The number of frames elapsed since this method was
            last called.
        """
        if self.msec_to_climb > 0:
            frac_climb_done = 1 - self.msec_to_climb/Bird.CLIMB_DURATION
            self.y -= (Bird.CLIMB_SPEED * frames_to_msec(delta_frames) *
                       (1 - math.cos(frac_climb_done * math.pi)))
            self.msec_to_climb -= frames_to_msec(delta_frames)
        else:
            self.y += Bird.SINK_SPEED * frames_to_msec(delta_frames)

    @property
    def image(self):
        """Get a Surface containing this bird's image.

        This will decide whether to return an image where the bird's
        visible wing is pointing upward or where it is pointing downward
        based on pygame.time.get_ticks().  This will animate the flapping
        bird, even though pygame doesn't support animated GIFs.
        """
        if pygame.time.get_ticks() % 500 >= 250:
            return self._img_wingup
        else:
            return self._img_wingdown

    @property
    def mask(self):
        """Get a bitmask for use in collision detection.

        The bitmask excludes all pixels in self.image with a
        transparency greater than 127."""
        if pygame.time.get_ticks() % 500 >= 250:
            return self._mask_wingup
        else:
            return self._mask_wingdown

    @property
    def rect(self):
        """Get the bird's position, width, and height, as a pygame.Rect."""
        return Rect(self.x, self.y, Bird.WIDTH, Bird.HEIGHT)


class PipePair(pygame.sprite.Sprite):
    """Represents an obstacle.

    A PipePair has a top and a bottom pipe, and only between them can
    the bird pass -- if it collides with either part, the game is over.

    Attributes:
    x: The PipePair's X position.  This is a float, to make movement
        smoother.  Note that there is no y attribute, as it will only
        ever be 0.
    image: A pygame.Surface which can be blitted to the display surface
        to display the PipePair.
    mask: A bitmask which excludes all pixels in self.image with a
        transparency greater than 127.  This can be used for collision
        detection.
    top_pieces: The number of pieces, including the end piece, in the
        top pipe.
    bottom_pieces: The number of pieces, including the end piece, in
        the bottom pipe.

    Constants:
    WIDTH: The width, in pixels, of a pipe piece.  Because a pipe is
        only one piece wide, this is also the width of a PipePair's
        image.
    PIECE_HEIGHT: The height, in pixels, of a pipe piece.
    ADD_INTERVAL: The interval, in milliseconds, in between adding new
        pipes.
    """

    WIDTH = 80
    PIECE_HEIGHT = 32
    ADD_INTERVAL = 3000

    def __init__(self, pipe_end_img, pipe_body_img):
        """Initialises a new random PipePair.

        The new PipePair will automatically be assigned an x attribute of
        float(WIN_WIDTH - 1).

        Arguments:
        pipe_end_img: The image to use to represent a pipe's end piece.
        pipe_body_img: The image to use to represent one horizontal slice
            of a pipe's body.
        """
        self.x = float(WIN_WIDTH - 1)
        self.score_counted = False

        self.image = pygame.Surface((PipePair.WIDTH, WIN_HEIGHT), SRCALPHA)
        self.image.convert()   # speeds up blitting
        self.image.fill((0, 0, 0, 0))
        total_pipe_body_pieces = int(
            (WIN_HEIGHT -                  # fill window from top to bottom
             3 * Bird.HEIGHT -             # make room for bird to fit through
             3 * PipePair.PIECE_HEIGHT) /  # 2 end pieces + 1 body piece
            PipePair.PIECE_HEIGHT          # to get number of pipe pieces
        )
        self.bottom_pieces = randint(1, total_pipe_body_pieces)
#         self.bottom_pieces =6

#         print("Bottom_pieces", self.bottom_pieces)
        self.top_pieces = total_pipe_body_pieces - self.bottom_pieces
#         print("Top_pieces", self.top_pieces)
        # bottom pipe
        for i in range(1, self.bottom_pieces + 1):
            piece_pos = (0, WIN_HEIGHT - i*PipePair.PIECE_HEIGHT)
            self.image.blit(pipe_body_img, piece_pos)
        bottom_pipe_end_y = WIN_HEIGHT - self.bottom_height_px
#         print("bottom_pipe_end_y",bottom_pipe_end_y)
        bottom_end_piece_pos = (0, bottom_pipe_end_y - PipePair.PIECE_HEIGHT)
#         print("bottom_end_piece_pos",bottom_end_piece_pos)
        self.image.blit(pipe_end_img, bottom_end_piece_pos)

        # top pipe
        for i in range(self.top_pieces):
            self.image.blit(pipe_body_img, (0, i * PipePair.PIECE_HEIGHT))
        top_pipe_end_y = self.top_height_px
        self.image.blit(pipe_end_img, (0, top_pipe_end_y))

        # compensate for added end pieces
        self.top_pieces += 1
        self.bottom_pieces += 1

        # for collision detection
        self.mask = pygame.mask.from_surface(self.image)

    @property
    def top_height_px(self):
        """Get the top pipe's height, in pixels."""
        return self.top_pieces * PipePair.PIECE_HEIGHT

    @property
    def bottom_height_px(self):
        """Get the bottom pipe's height, in pixels."""
        return self.bottom_pieces * PipePair.PIECE_HEIGHT

    @property
    def visible(self):
        """Get whether this PipePair on screen, visible to the player."""
        return -PipePair.WIDTH < self.x < WIN_WIDTH

    @property
    def rect(self):
        """Get the Rect which contains this PipePair."""
        return Rect(self.x, 0, PipePair.WIDTH, PipePair.PIECE_HEIGHT)

    def update(self, delta_frames=1):
        """Update the PipePair's position.

        Arguments:
        delta_frames: The number of frames elapsed since this method was
            last called.
        """
        self.x -= ANIMATION_SPEED * frames_to_msec(delta_frames)

    def collides_with(self, bird):
        """Get whether the bird collides with a pipe in this PipePair.

        Arguments:
        bird: The Bird which should be tested for collision with this
            PipePair.
        """
#         print(pygame.sprite.collide_mask(self,bird))
        return pygame.sprite.collide_mask(self, bird)

class State:
    
    NUM_TILES_X = 40
    NUM_TILES_Y = 40
    def __init__(self, bird, pipes):
        print("PIPES: ",pipes[0].x, " ",(WIN_HEIGHT-pipes[0].bottom_height_px)," BIRD: ",bird.x," ",bird.y)
#         self.x = int((pipes[0].x - bird.x)*(State.NUM_TILES_X/float(WIN_WIDTH)))
#         self.y = int((WIN_HEIGHT-pipes[0].bottom_height_px) - bird.y)*State.NUM_TILES_Y/float(WIN_HEIGHT)
        self.x = int(pipes[0].x*State.NUM_TILES_X/float(WIN_WIDTH) - bird.x*State.NUM_TILES_X/float(WIN_WIDTH))
        self.y = int((WIN_HEIGHT-pipes[0].bottom_height_px)*State.NUM_TILES_Y/float(WIN_HEIGHT) - bird.y*State.NUM_TILES_Y/float(WIN_HEIGHT))
        print("x",self.x," y",self.y)
        
    def short(self):
        return (self.x,self.y)

    def __str__(self):
        return 'Bird({},{}) '.format(self.x, self.y)

    def __lt__(self, other):
        return True


class QValue:

    GAMMA = 0.9

    def __init__(self, gamma):
        self.Q = Counter()
        if gamma is not None:
            self.GAMMA = gamma

    def update(self,state,action,reward,nextState,N):
#         ETA = 1/math.sqrt(N+1)
        ETA=0.7
        self.Q[(state,action)] = (1-ETA)*self.Q[(state,action)] + ETA*(reward + self.GAMMA*max(self.Q[(nextState,'jump')],self.Q[(nextState,'stay')]))
        print("state :",state," action:",action," reward: ",reward," nextState: ",nextState," N: ",N," Q:",self.Q[state,action],"")
    
    
    def policy(self, state):
        print("Q : JUMP: ",self.Q[(state,'jump')]," STAY:",self.Q[(state,'stay')])
        if self.Q[(state,'jump')]>self.Q[(state,'stay')]:
            return "jump"
        else:
            return "stay"
            

        
#         print("Q : JUMP: ",self.Q[(state,'jump')]," STAY:",self.Q[(state,'stay')])
#         if self.Q[(state,'jump')] > self.Q[(state,'stay')]:
#             return 'jump'
#         else:
#             return 'stay'
        
#         return lambda self.Q(state,'jump'),self.Q(state,'stay'))
        
def epsilon_greedy(Qvalue,epsilon,state):
    if epsilon > random.uniform(0,1):
        print("RANDOM")
        return random.choice(['jump','stay'])
    else:
        return Qvalue.policy(state.short())

def load_images():
    """Load all images required by the game and return a dict of them.

    The returned dict has the following keys:
    background: The game's background image.
    bird-wingup: An image of the bird with its wing pointing upward.
        Use this and bird-wingdown to create a flapping bird.
    bird-wingdown: An image of the bird with its wing pointing downward.
        Use this and bird-wingup to create a flapping bird.
    pipe-end: An image of a pipe's end piece (the slightly wider bit).
        Use this and pipe-body to make pipes.
    pipe-body: An image of a slice of a pipe's body.  Use this and
        pipe-body to make pipes.
    """

    def load_image(img_file_name):
        """Return the loaded pygame image with the specified file name.

        This function looks for images in the game's images folder
        (./images/).  All images are converted before being returned to
        speed up blitting.

        Arguments:
        img_file_name: The file name (including its extension, e.g.
            '.png') of the required image, without a file path.
        """
        file_name = os.path.join('.', 'images', img_file_name)
        img = pygame.image.load(file_name)
        img.convert()
        return img

    return {'background': load_image('background.png'),
            'pipe-end': load_image('pipe_end.png'),
            'pipe-body': load_image('pipe_body.png'),
            # images for animating the flapping bird -- animated GIFs are
            # not supported in pygame
            'bird-wingup': load_image('bird_wing_up.png'),
            'bird-wingdown': load_image('bird_wing_down.png')}


def frames_to_msec(frames, fps=FPS):
    """Convert frames to milliseconds at the specified framerate.

    Arguments:
    frames: How many frames to convert to milliseconds.
    fps: The framerate to use for conversion.  Default: FPS.
    """
    return 1000.0 * frames / fps


def msec_to_frames(milliseconds, fps=FPS):
    """Convert milliseconds to frames at the specified framerate.

    Arguments:
    milliseconds: How many milliseconds to convert to frames.
    fps: The framerate to use for conversion.  Default: FPS.
    """
    return fps * milliseconds / 1000.0

  

def main(maxGames, gamma, epsilon, bird_has_learned, q_values_counter):
# def main():
    """The application's entry point.

    If someone executes this module (instead of importing it, for
    example), this function is called.
    """
    # Added for Q Learning
    counter=0
#     maxGames=20
#     epsilon= 80
    maxScore=0
    QLearning=QValue(gamma)
    if bird_has_learned == 1:
        QLearning.Q = q_values_counter
        print(QLearning.Q)
#     else:
#     file = open("q_values_train_v2_random_pipes.txt", "w")
#     fileAvgScore = open("avgScore_v2_random_pipes.txt", "w")
#     fileScore = open("Score_v2_random_pipes.txt", "w")      
    reward=15
#     reward_dead = -1000
    reward_dead = -100
    reward_pass = 15
    reward_ingap = 15
    scoreList = []
    avgScore = []
        # Added for Q Learning
    pygame.init()
    
    # Added for Q Learning

    while counter < maxGames:
        listState=[]
        display_surface = pygame.display.set_mode((WIN_WIDTH, WIN_HEIGHT))
#         print("display",display_surface)
        pygame.display.set_caption('Pygame Flappy Bird')
        
        clock = pygame.time.Clock()
        score_font = pygame.font.SysFont(None, 32, bold=True)  # default font    
        images = load_images()
        
        # the bird stays in the same x position, so bird.x is a constant
        # center bird on screen
        bird = Bird(50, int(WIN_HEIGHT/2 - Bird.HEIGHT/2), 2,
                    (images['bird-wingup'], images['bird-wingdown']))
        
        pipes = deque()
        # Added for Q Learning
        nextPipes = deque()
        fcounter = 0    
        #Added for Q Learning
        frame_clock = 0  # this counter is only incremented if the game isn't paused
        score = 0
        done = paused = False
        
        while not done:
            clock.tick(FPS)
        
            # Handle this 'manually'.  If we used pygame.time.set_timer(),
            # pipe addition would be messed up when paused.
            if not (paused or frame_clock % msec_to_frames(PipePair.ADD_INTERVAL)):
                pp = PipePair(images['pipe-end'], images['pipe-body'])
#                 print(" YES ",pp.bottom_height_px," ",pp.top_height_px," ",bird.x," ",bird.y," ",bird.HEIGHT," ",bird.WIDTH)
                pipes.append(pp)
                #Added for Q Learning
                nextPipes.append(pp)
        
            for e in pygame.event.get():
        #             print("e.type",e.type)
                if e.type == QUIT or (e.type == KEYUP and e.key == K_ESCAPE) or (e.type == KEYDOWN and e.key == K_ESCAPE):
#                     done = True
#                     break
                    pygame.quit()
#                     sys.exit()
                elif e.type == KEYUP and e.key in (K_PAUSE, K_p):
                    paused = not paused
                elif e.type == MOUSEBUTTONUP or (e.type == KEYUP and
                        e.key in (K_UP, K_RETURN, K_SPACE)):
                    bird.msec_to_climb = Bird.CLIMB_DURATION
            # ADDED FOR Q LEARNING
            if (fcounter%(FPS/6) == 0):
                newState = State(bird,pipes)
                print(newState.x,newState.y)
#                 if counter%10 == 0:
                if bird_has_learned == 1:
                    newAction = epsilon_greedy(QLearning,0.0,newState)
#                     newAction = epsilon_greedy(QLearning,min(0.1,epsilon/float(counter+1)),newState)
                else:
                    newAction = epsilon_greedy(QLearning,min(0.1,epsilon/float(counter+1)),newState)
                if newAction == 'jump':
#                     print(newState.x,newState.y)
                    bird.msec_to_climb = Bird.CLIMB_DURATION
                listState.append((newState.short(),newAction))
            fcounter+=1
            
            # ADDED FOR Q LEARNING
            if paused:
                continue  # don't draw anything
        
            # check for collisions
            
            pipe_collision = any(p.collides_with(bird) for p in pipes)
            
        #         print(pipe_collision," ",bird.y, " ",bird.x," ",Bird.HEIGHT," Win H",WIN_HEIGHT)
            if pipe_collision or 0 >= bird.y or bird.y >= WIN_HEIGHT - Bird.HEIGHT:
                done = True
#                 pygame.init()
#                 display_surface = pygame.display.set_mode((WIN_WIDTH, WIN_HEIGHT))
#                 pygame.display.set_caption('Pygame Flappy Bird')
#         
#                 clock = pygame.time.Clock()
#                 score_font = pygame.font.SysFont(None, 32, bold=True)  # default font
#         
#                 images = load_images()
#         
#                 # the bird stays in the same x position, so bird.x is a constant
#                 # center bird on screen
#                 bird = Bird(50, int(WIN_HEIGHT/2 - Bird.HEIGHT/2), 2,
#                             (images['bird-wingup'], images['bird-wingdown']))
#         
#                 pipes = deque()
#         
#                 frame_clock = 0  # this counter is only incremented if the game isn't paused
#                 score = 0
#                 done = paused = False
#         #             if not (paused or frame_clock % msec_to_frames(PipePair.ADD_INTERVAL)):
        #                 pp = PipePair(images['pipe-end'], images['pipe-body'])
        #                 pipes.append(pp)
#                 continue
                
                
        
            for x in (0, WIN_WIDTH / 2):
                display_surface.blit(images['background'], (x, 0))
        
            while pipes and not pipes[0].visible:
                pipes.popleft()
        
            for p in pipes:
                p.update()
                display_surface.blit(p.image, p.rect)
#             if bird_has_learned !=1:
#                 for i in range(len(listState)-2):
#                     if listState[i+1][0][1] >= 0 and listState[i+1][0][1] <= 3:
#                         QLearning.update(listState[i][0],listState[i][1],reward_ingap,listState[i+1][0],counter)
#                     else:
#                         QLearning.update(listState[i][0],listState[i][1],reward,listState[i+1][0],counter)
#                 QLearning.update(listState[len(listState)-2][0],listState[len(listState)-2][1],reward_dead,listState[len(listState)-1][0],counter)
    #             
            bird.update()
            display_surface.blit(bird.image, bird.rect)
            if maxScore < score:
                maxScore=score
            # update and display score
            for p in pipes:
                if p.x + PipePair.WIDTH < bird.x and not p.score_counted:
                    score += 1
                    p.score_counted = True
            score_str="Score: "+str(score)+" Max: "+str(maxScore)
#             score_surface = score_font.render(str(score), True, (255, 255, 255))
            score_surface = score_font.render(score_str, True, (255, 255, 255))
            score_x = WIN_WIDTH/2 - score_surface.get_width()/2
            display_surface.blit(score_surface, (score_x, PipePair.PIECE_HEIGHT))
        
            pygame.display.flip()
            frame_clock += 1
        #ADDED FOR Q LEARNING

        for i in range(len(listState)-2):
            if listState[i+1][0][1] >= 0 and listState[i+1][0][1] <= 3:
                QLearning.update(listState[i][0],listState[i][1],reward_ingap,listState[i+1][0],counter)
            else:
                QLearning.update(listState[i][0],listState[i][1],reward,listState[i+1][0],counter)
        QLearning.update(listState[len(listState)-2][0],listState[len(listState)-2][1],reward_dead,listState[len(listState)-1][0],counter)
        print('Game over! Score: %i\tnum states:%i\tnum games:%i' % (score, len(QLearning.Q), counter))
    #        print(QL.Q)
        counter+=1

        print("counter",counter)
#         if (counter-1) == 0:
#             avgScore.append(score)
#         elif((counter-1)%10 == 0):
#             avgScore.append(avgScore[-1]*(counter-1)/counter + score/counter)
#         if (counter-1)%10==0:
#             scoreList.append(score)
        if len(avgScore) == 0:
            avgScore.append(score)
        else:
            avgScore.append((avgScore[-1]*(counter-1)+ score)/float(counter))
        scoreList.append(score)
        if(counter%50==0):
            file = open("q_values_train_v2_random_pipes_0.7.txt", "w")
            fileAvgScore = open("avgScore_v2_random_pipes_0.7.txt", "w")
            fileScore = open("Score_v2_random_pipes_0.7.txt", "w")  
#             file = open("q_values_train_v2_random_pipes_3.txt", "w")
#             fileAvgScore = open("avgScore_v2_random_pipes_3.txt", "w")
#             fileScore = open("Score_v2_random_pipes_3.txt", "w")
#             file = open("q_values_train_v2_same_pipes.txt", "w")
#             fileAvgScore = open("avgScore_v2_same_pipes.txt", "w") 
#             fileScore = open("Score_v2_same_pipes.txt", "w")        
            fileAvgScore.write(str(avgScore))
            fileScore.write(str(scoreList))
            file.write(str(QLearning.Q))
            file.close()
            fileAvgScore.close()
            fileScore.close()
    #ADDED FOR QLEARNING
    print("Game over! Score: %i" % score)
    print("scoreList",scoreList)
    pygame.quit()
    print(avgScore)


if __name__ == '__main__':
    # If this module had been imported, __name__ would be 'flappybird'.
    # It was executed (e.g. by double-clicking the file), so call main.
#     main()
#     main()
    maxGames =5000
#     Trail one 
#     gamma = 0.6
#     epsilon=0.8
# Trial 2
    gamma = 0.91
    epsilon=0.6
#     main(maxGames, gamma, epsilon, 0, None)
#     Same pipes
#     qfile = open('q_values_train_v2_same_pipes.txt')
#     qfile = open('q_values_train_v2_random_pipes.txt')
#     qfile = open('q_values_train_v2_random_pipes.txt')
    qfile = open('q_values_train_v2_random_pipes_0.7.txt')
#     qfile = open('q_values_train_v2_random_pipes_3.txt')
    q_values = eval(qfile.read())
    print (len(q_values))
#     maxGames=2000
    main(maxGames, gamma, epsilon,1, q_values)

#     print ("now running for training: main(maxGames=%d, gamma=%f, epsilon=fn(%f), learning=0, None)" % (maxGames, gamma, epsilon))
#     Qvalues = main(maxGames, gamma, epsilon, 0, None)
#     maxGames = 500
#     print ("now running for test: main(maxGames=%d, gamma=%f, epsilon=fn(%f), learning=1, Qvalues)" % (maxGames, gamma, epsilon))
#     main(maxGames, gamma, epsilon, 1, Qvalues)