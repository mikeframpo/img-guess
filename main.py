
import pygame as pg
import sys

sys.path.append('Quads')
from quads import Model

class ModelIter:

    def __init__(self, path):
        self.model = Model(path)

    def step(self):
        self.model.split()
        return self.model.render()

class Game:

    def __init__(self, screen, path):
        self.prev_draw_time = None
        self.screen = screen
        self.model = ModelIter(path)
        self.font = pg.font.SysFont('monospace', 45)

        # initial state of the game
        self.state = Game.STATE_NEWGAME
        self.draw_newgame_screen()

    STATE_NEWGAME = 0
    STATE_DRAWING = 1

    IMAGE_RATE = 20
    IMAGE_RATE_MILLIS = 1.0/IMAGE_RATE * 1000 

    KEY_NEWGAME = pg.K_g

    BG_COLOR = (0, 0, 0)
    TEXT_ANTIALIAS = 1
    TEXT_COLOR = (255, 255, 0)

    def draw_text(self, text, loc):
        text_surface = self.font.render(text, Game.TEXT_ANTIALIAS,
                                        Game.TEXT_COLOR)
        self.screen.blit(text_surface, loc)

    def draw_newgame_screen(self):
        self.screen.fill(Game.BG_COLOR)
        self.draw_text('Start new game (%s)' % chr(self.KEY_NEWGAME), (0,0))
        pg.display.flip()

    def process_state(self, time, events):
        nextstate = None
        # process the current state
        if self.state == Game.STATE_NEWGAME:
            for event in events:
                if event.type == pg.KEYUP and event.key == self.KEY_NEWGAME:
                    nextstate = Game.STATE_DRAWING
        elif self.state == Game.STATE_DRAWING:
            assert self.prev_draw_time is None or time > self.prev_draw_time
            if self.prev_draw_time is None \
                or (time - self.prev_draw_time) > Game.IMAGE_RATE_MILLIS:
                self.prev_draw_time = time
                im = self.model.step()
                surface = pg.image.fromstring(im.tostring(), im.size, im.mode)
                self.screen.blit(surface, (0,0))
                pg.display.flip()
        # enter the next state
        if nextstate is not None:
            if nextstate == Game.STATE_NEWGAME:
                self.draw_newgame_screen()
            # set the new state
            self.state = nextstate

class Main:

    FRAMERATE = 60

    def __init__(self, path):
        pg.init()
        self.clock = pg.time.Clock()
        screen = pg.display.set_mode((640, 480))
        self.game = Game(screen, path)

    def mainloop(self):
        while True:
            self.clock.tick(self.FRAMERATE)
            time = pg.time.get_ticks()
            events = []
            for event in pg.event.get():
                if event.type == pg.QUIT:
                    sys.exit()
                else:
                    events.append(event)
            self.game.process_state(time, events)

if __name__ == '__main__':
    args = sys.argv[1:]
    if len(args) != 1:
        print 'Usage: python main.py input_image'
        sys.exit(1)
    
    main = Main(args[0])
    main.mainloop()

