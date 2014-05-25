
import pygame as pg
import sys, os
import urlparse

from vector import Vec2d

sys.path.append('Quads')
from quads import Model

sys.path.append('requests')
import requests

sys.path.append('pyBingSearchAPI')
from bing_search_api import BingSearchAPI

class ModelIter:

    def __init__(self, path):
        self.model = Model(path)

    def step(self):
        self.model.split()
        return self.model.render()

class BingImageFetcher:

    def __init__(self, keypath):
        keyfile = open(keypath, 'r')
        key = keyfile.readline().strip()
        self.bing = BingSearchAPI(key)
        self.params = {
                        #'ImageFilters':'"Face:Face"',
                        '$format': 'json',
                        '$top': 10,
                        '$skip': 0}

    TIMEOUT = 10.0
    IMG_FILES = 'img'

    def fetch_image(self, word):
        # note, throws ConnectionError if failed to fetch
        resp = self.bing.search('image', word, self.params).json()
        image_results = resp['d']['results'][0]['Image']
        if len(image_results) == 0:
            raise Exception('Failed to find any images for query ' + word)
        image_url = image_results[0]['MediaUrl']
        up = urlparse.urlparse(image_url)
        destfile = os.path.basename(up.path)
        destpath = os.path.join(BingImageFetcher.IMG_FILES, destfile)
        if not os.path.isdir(BingImageFetcher.IMG_FILES):
            os.mkdir(BingImageFetcher.IMG_FILES)
        if os.path.isfile(destpath):
            # if we already have that image then just use the cached version
            return destpath
        req_image = requests.get(image_url, timeout=BingImageFetcher.TIMEOUT)
        if req_image.status_code != 200:
            raise Exception('Image request for %s failed to return 200 status'
                            % image_url)
        imgfile = open(destpath, 'w')
        imgfile.write(req_image.content)
        imgfile.close()
        return destpath

class Game:

    def __init__(self):
        self.prev_draw_time = None
        self.screen = pg.display.set_mode(Game.SCREEN_DIMS)
 
        self.model = None
        self.font = pg.font.SysFont('monospace', Game.TEXT_SIZE)

        # initial state of the game
        self.state = Game.STATE_NEWGAME
        self.draw_newgame_screen()

        self.fetcher = BingImageFetcher(Game.KEYPATH)

    SCREEN_DIMS = Vec2d(960, 720)
    IMG_DIMS = Vec2d(SCREEN_DIMS.x * 0.8, SCREEN_DIMS.y * 0.7)

    STATE_NEWGAME = 0
    STATE_DRAWING = 1
    STATE_LOADING = 2

    IMAGE_RATE = 20
    IMAGE_RATE_MILLIS = 1.0/IMAGE_RATE * 1000 

    KEY_NEWGAME = pg.K_g

    BG_COLOR = (0, 0, 0)
    TEXT_ANTIALIAS = 1
    TEXT_COLOR = (255, 255, 0)
    TEXT_SIZE = 45

    CONTROLS_SURFACE_DIMS = Vec2d(250, 250)
    BUTTONS_BG_COLOR = pg.color.Color('blue')
    P1_CONTROLS = (pg.K_q, pg.K_w, pg.K_a, pg.K_s)
    P1_CONTROLS_POS = Vec2d(50, 100)
    P2_CONTROLS = (pg.K_i, pg.K_o, pg.K_k, pg.K_l)
    P2_CONTROLS_POS = Vec2d(400, 100)

    KEYPATH = 'key.txt'

    def draw_text(self, text, loc):
        text_surface = self.font.render(text, Game.TEXT_ANTIALIAS,
                                        Game.TEXT_COLOR)
        self.screen.blit(text_surface, loc)

    def draw_newgame_screen(self):
        self.screen.fill(Game.BG_COLOR)
        self.draw_text('Start new game (%s)' % chr(self.KEY_NEWGAME), (0,0))
        self.draw_player_controls('Player 1', Game.P1_CONTROLS,
                                    Game.P1_CONTROLS_POS)
        self.draw_player_controls('Player 2', Game.P2_CONTROLS,
                                    Game.P2_CONTROLS_POS)
        pg.display.flip()

    def draw_player_controls(self, player_text, controls, loc):
        controls_surface = pg.surface.Surface(Game.CONTROLS_SURFACE_DIMS)
        controls_surface.fill(Game.BUTTONS_BG_COLOR)
        curloc = Vec2d(0,0)
        player_text_surface = self.font.render(player_text,
                                        Game.TEXT_ANTIALIAS, Game.TEXT_COLOR)
        controls_surface.blit(player_text_surface, curloc)
        for ibut, but in enumerate(controls):
            curloc = curloc + (0, Game.TEXT_SIZE)
            number_surface = self.font.render('%d. ' % (ibut + 1),
                                        Game.TEXT_ANTIALIAS, Game.TEXT_COLOR)
            controls_surface.blit(number_surface, curloc)
            button_surface = self.font.render(chr(but),
                                        Game.TEXT_ANTIALIAS, Game.TEXT_COLOR)
            buttonloc = curloc + (Game.TEXT_SIZE, 0)
            controls_surface.blit(button_surface, buttonloc)
            pg.draw.rect(controls_surface, Game.TEXT_COLOR,
                    pg.Rect(buttonloc, (Game.TEXT_SIZE, Game.TEXT_SIZE)),
                    3)
        self.screen.blit(controls_surface, loc)

    def draw_loading_screen(self):
        self.screen.fill(self.BG_COLOR)
        loading_text = self.font.render('Loading next image...',
                                        Game.TEXT_ANTIALIAS, Game.TEXT_COLOR)
        self.screen.blit(loading_text, (0,0))
        pg.display.flip()

    def draw_step_drawing_screen(self):
        # draw the words on the screen
        im = self.model.step()
        im_size = Vec2d(im.size)
        r_x = float(im_size.x)/Game.IMG_DIMS.x
        r_y = float(im_size.y)/Game.IMG_DIMS.y

        if r_x > r_y:
            im_newsize = im_size/r_x
        else:
            im_newsize = im_size/r_y
        im_newsize = Vec2d(int(im_newsize.x), int(im_newsize.y))
        im_resized = im.resize(im_newsize)

        surface = pg.image.fromstring(im_resized.tostring(), im_resized.size,
                                    im_resized.mode)
        im_loc = Vec2d(Game.SCREEN_DIMS.x/2 - im_newsize.x/2, 30)
        self.screen.blit(surface, im_loc)
        pg.display.flip()

    def process_state(self, time, events):
        nextstate = None

        # process the current state
        if self.state == Game.STATE_NEWGAME:
            for event in events:
                if event.type == pg.KEYUP and event.key == self.KEY_NEWGAME:
                    nextstate = Game.STATE_LOADING
        elif self.state == Game.STATE_LOADING:
            if self.model is None:
                print('Image fetch failed')
                nextstate = Game.STATE_LOADING
            else:
                nextstate = Game.STATE_DRAWING
        elif self.state == Game.STATE_DRAWING:
            assert self.prev_draw_time is None or time > self.prev_draw_time
            if self.prev_draw_time is None \
                or (time - self.prev_draw_time) > Game.IMAGE_RATE_MILLIS:
                self.prev_draw_time = time
                self.draw_step_drawing_screen()

        # enter the next state
        if nextstate is not None:
            if nextstate == Game.STATE_NEWGAME:
                self.draw_newgame_screen()
            if nextstate == Game.STATE_LOADING:
                self.draw_loading_screen()
                # TODO: pull a random word out of the wordlist
                self.model = None
                # TODO: catch the exception for a failed fetch
                imagepath = self.fetcher.fetch_image('flower')
                self.model = ModelIter(imagepath)
                
            # set the new state
            self.state = nextstate

class Main:

    FRAMERATE = 60

    def __init__(self):
        pg.init()
        self.clock = pg.time.Clock()
        self.game = Game()

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

def test_bing_search(word):
    bing = BingImageFetcher('key.txt')
    return(bing.fetch_image(word))

if __name__ == '__main__':

    test_bing_search('jazzman')

