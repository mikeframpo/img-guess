
import pygame as pg
import sys, os
import urlparse
import random

from vector import Vec2d

sys.path.append('Quads')
from quads import Model

sys.path.append('requests')
import requests

sys.path.append('grequests')
import grequests

import gevent

sys.path.append('pyBingSearchAPI')
from bing_search_api import BingSearchAPI

class ModelIter:

    def __init__(self, path):
        self.model = Model(path)

    def step(self):
        self.model.split()
        return self.model.render()

class AsyncImageFetcher:

    class RequestedImage:
        def __init__(self, req, iword, path, words):
            self.req = req
            self.iword = iword
            self.path = path
            self.words = words

    def __init__(self, fetcher):
        self.requests = {}
        self.fetched = []
        self.fetcher = fetcher

    def get_total_images(self):
        return len(self.requests) + len(self.fetched)

    def queue_fetch_image(self, iword, words):
        cached, url, destpath = self.fetcher.create_request(words[iword])

        if cached:
            self.add_to_fetched(AsyncImageFetcher.RequestedImage(
                                    None, iword, destpath, words))
        else:
            # put the request in a structure with the word and extradata
            if not self.requests.has_key(url):
                req = grequests.get(url,
                                    timeout=BingImageFetcher.TIMEOUT,
                                    hooks={'response': [self.on_response]})
                self.requests[url] = AsyncImageFetcher.RequestedImage(
                                        req, iword, destpath, words)
                grequests.send(req, grequests.Pool(1))

    def add_to_fetched(self, req_image):
        self.fetched.append(req_image)

    def on_response(self, req, **kwargs):
        req_image = self.requests.pop(req.url)
        print('fetched image: ' + req.url)
        if req.status_code != 200:
            raise Exception('Image request for %s failed to return 200 status'
                            % req.url)

        imgfile = open(req_image.path, 'w')
        imgfile.write(req.content)
        imgfile.close()
        self.add_to_fetched(req_image)

class BingImageFetcher:

    NUM_IMGS = 10

    def __init__(self, keypath):
        keyfile = open(keypath, 'r')
        key = keyfile.readline().strip()
        self.bing = BingSearchAPI(key)
        self.params = {
                        #'ImageFilters':'"Face:Face"',
                        '$format': 'json',
                        '$top': self.NUM_IMGS,
                        '$skip': 0}

    TIMEOUT = 10.0
    IMG_FILES = 'img'

    def create_request(self, word):
        # note, throws ConnectionError if failed to fetch
        resp = self.bing.search('image', word, self.params).json()
        image_results = resp['d']['results'][0]['Image']
        if len(image_results) == 0:
            raise Exception('Failed to find any images for query ' + word)
        image_url = image_results[random.randint(0, self.NUM_IMGS-1)]['MediaUrl']
        up = urlparse.urlparse(image_url)
        destfile = os.path.basename(up.path)
        destpath = os.path.join(BingImageFetcher.IMG_FILES, destfile)
        if not os.path.isdir(BingImageFetcher.IMG_FILES):
            os.mkdir(BingImageFetcher.IMG_FILES)
        is_cached = False
        if os.path.isfile(destpath):
            # if we already have that image then just use the cached version
            is_cached = True
        return is_cached, image_url, destpath

class TestFetcher:

    def fetch_image(self, word):
        return 'a.jpg'

class Game:

    def __init__(self):
        self.prev_draw_time = None
        self.screen = pg.display.set_mode(Game.SCREEN_DIMS)
 
        self.model = None
        self.font = pg.font.SysFont('monospace', Game.TEXT_SIZE)
        self.font_h1 = pg.font.SysFont('monospace', Game.TEXT_H1_SIZE)

        # initial state of the game
        self.state = Game.STATE_NEWGAME
        self.draw_newgame_screen()

        fetcher = BingImageFetcher(Game.KEYPATH)
        self.async_fetcher = AsyncImageFetcher(fetcher)
        #self.fetcher = TestFetcher()

        self.load_wordlist(Game.WORDSPATH)
        self.timeout = None

    SCREEN_DIMS = Vec2d(960, 720)

    SCORE_YSIZE = 50
    SCORE_YOFFS = 10
    SCORE_SURFACE_DIMS = Vec2d(int(SCREEN_DIMS.x), SCORE_YSIZE)
    SCORE_XSPACING = 50
    SCORE_STAR_SIZE = Vec2d(50, 50)

    IMG_DIMS = Vec2d(SCREEN_DIMS.x * 0.8, SCREEN_DIMS.y * 0.6)
    IMG_YOFFS = 10

    STATE_NEWGAME = 0
    STATE_DRAWING = 1
    STATE_LOADING = 2
    STATE_GUESSED = 3
    STATE_WINNER = 4

    IMAGE_RATE = 60
    IMAGE_RATE_MILLIS = 1.0/IMAGE_RATE * 1000 

    KEY_NEWGAME = pg.K_g

    BG_COLOR = (0, 0, 0)
    TEXT_ANTIALIAS = 1
    TEXT_COLOR = (255, 255, 0)
    TEXT_H1_COLOR = (0, 0, 255)

    TEXT_SIZE = 30
    TEXT_H1_SIZE = 40

    CONTROLS_SURFACE_DIMS = Vec2d(250, 250)
    BUTTONS_BG_COLOR = pg.color.Color('blue')

    P1 = 1
    P2 = 2
    P1_CONTROLS = (pg.K_q, pg.K_w, pg.K_a, pg.K_s)
    P2_CONTROLS = (pg.K_i, pg.K_o, pg.K_k, pg.K_l)

    CONTROLS_YOFFS = 10
    WORDS_SURFACE_DIMS = Vec2d(int(SCREEN_DIMS.x*0.4), int(SCREEN_DIMS.y*0.3))
    P1_CONTROLS_POS = Vec2d(SCREEN_DIMS.x/2 - WORDS_SURFACE_DIMS.x,
        SCORE_YSIZE + SCORE_YOFFS + IMG_DIMS.y + IMG_YOFFS + CONTROLS_YOFFS)
    P2_CONTROLS_POS = P1_CONTROLS_POS + Vec2d(WORDS_SURFACE_DIMS.x, 0)

    KEYPATH = 'key.txt'
    WORDSPATH = 'words.txt'
    
    NUM_WORDS = 4
    SCORE_WIN = 5

    GUESS_TIMEOUT = 2000
    WINNER_TIMEOUT = 5000

    PREFETCHED_IMAGES = 3

    def load_wordlist(self, path):
        wordsfile = open(path)
        self.wordlist = []
        for line in wordsfile:
            self.wordlist.append(line.strip())
        #self.wordlist = ['cheese', 'soldier', 'rubiks', 'gloves', 'mouse',
        #        'shoes', 'guitar', 'piano']

    def pick_words(self):
        words = []
        while len(words) < Game.NUM_WORDS:
            newword = self.wordlist[random.randint(0, len(self.wordlist) - 1)]
            if newword in words:
                continue
            words.append(newword)
        return words

    def draw_text(self, text, loc):
        text_surface = self.font.render(text, Game.TEXT_ANTIALIAS,
                                        Game.TEXT_COLOR)
        self.screen.blit(text_surface, loc)

    def new_game(self):
        self.score = 0

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

    def draw_both_player_words(self, pressed=None):
        self.draw_player_words(Game.P1_CONTROLS, Game.P1_CONTROLS_POS,
                                pressed, 'Player 1')
        self.draw_player_words(Game.P2_CONTROLS, Game.P2_CONTROLS_POS,
                                pressed, 'Player 2')

    def get_player_scores(self):
        p1score = max(0, self.score*-1)
        p2score = max(0, self.score)
        return (p1score, p2score)

    def draw_drawing_screen(self):
        self.screen.fill(self.BG_COLOR)
        self.draw_both_player_words()
        self.draw_scores(*self.get_player_scores())
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
        im_loc = Vec2d(Game.SCREEN_DIMS.x/2 - im_newsize.x/2,
                    Game.SCORE_YOFFS + Game.SCORE_YSIZE + Game.IMG_YOFFS)
        self.screen.blit(surface, im_loc)
        pg.display.flip()

    def draw_player_score(self, surface, score, direction, imgprefix):
        for isc in range(1, Game.SCORE_WIN+1):
            if score >= isc:
                imgpath = imgprefix + '_on.png'
            else:
                imgpath = imgprefix + '_off.png'

            img = pg.image.load(imgpath)
            img = pg.transform.smoothscale(img, Game.SCORE_STAR_SIZE)
            surface.blit(img,
                (surface.get_width()/2 +
                    (isc * direction * Game.SCORE_XSPACING), 0))

    def draw_scores(self, p1score, p2score):
        surface = pg.surface.Surface(Game.SCORE_SURFACE_DIMS)
        assert p1score <= Game.SCORE_WIN and p2score <= Game.SCORE_WIN
        self.draw_player_score(surface, p1score, -1.0, 'red')
        self.draw_player_score(surface, p2score, 1.0, 'blue')
        self.screen.blit(surface, (0,Game.SCORE_YOFFS))

    def draw_words_list(self, surface, wordlist, surface_loc):
        curloc = Vec2d(surface_loc)
        for listelem in wordlist:
            text_surface = self.font.render(listelem[0], Game.TEXT_ANTIALIAS,
                                        Game.TEXT_COLOR)

            highlight = listelem[1]
            if highlight:
                pg.draw.rect(text_surface, Game.TEXT_COLOR,
                        pg.Rect((0,0), text_surface.get_size()))
            surface.blit(text_surface, curloc)

            curloc = curloc + (0, 2*Game.TEXT_SIZE)

    def draw_player_words(self, controls, pos, pressed, pname):
        leftwords = []
        rightwords = []
        for i_word, word in enumerate(self.current_words):

            highlight = False
            if pressed is not None and controls[i_word] in pressed:
                highlight = True

            listelem = ('%s. %s' % (chr(controls[i_word]), word), highlight)
            if i_word % 2 == 0:
                leftwords.append(listelem)
            else:
                rightwords.append(listelem)
        surface = pg.surface.Surface(Game.WORDS_SURFACE_DIMS)
        pname_surface = self.font_h1.render(pname, Game.TEXT_ANTIALIAS, Game.TEXT_H1_COLOR)
        surface.blit(pname_surface, (0,0))
        
        yoffs = Game.TEXT_H1_SIZE + 10
        self.draw_words_list(
                surface, leftwords, Vec2d(0, yoffs))
        self.draw_words_list(
                surface, rightwords, Vec2d(100, Game.TEXT_SIZE + yoffs))
        self.screen.blit(surface, pos)

    def draw_guessed_screen(self):
        text_surface = self.font.render('Guessed', Game.TEXT_ANTIALIAS,
                                        Game.TEXT_COLOR)
        self.screen.blit(text_surface, (0,0))
        self.draw_both_player_words(self.events)
        pg.display.flip()

    def draw_winner_screen(self):
        text_surface = self.font.render('Player X Wins!', Game.TEXT_ANTIALIAS,
                                        Game.TEXT_COLOR)
        self.screen.blit(text_surface,
            (self.SCREEN_DIMS.x/2,self.SCREEN_DIMS.y/2))
        pg.display.flip()

    def key_correct(self, key, controls):
        idx = controls.index(key)
        return idx == self.img_word

    def check_winner(self, key):
        if key in Game.P1_CONTROLS:
            return Game.P1 if self.key_correct(key, Game.P1_CONTROLS) else Game.P2
        if key in Game.P2_CONTROLS:
            return Game.P2 if self.key_correct(key, Game.P2_CONTROLS) else Game.P1
        assert False

    def update_score(self, winner):
        if winner == Game.P1:
            self.score = self.score - 1
        else:
            self.score = self.score + 1

    def process_state(self, time, events):
        winner = None
        nextstate = None

        while self.async_fetcher.get_total_images() < Game.PREFETCHED_IMAGES:
            words = self.pick_words()
            iword = random.randint(0, Game.NUM_WORDS-1)
            self.async_fetcher.queue_fetch_image(iword, words)

        # sleep each game cycle to check if any requests are ready for
        # processing
        gevent.sleep(0)

        # process the current state
        if self.state == Game.STATE_NEWGAME:
            for event in events:
                if event.type == pg.KEYUP and event.key == self.KEY_NEWGAME:
                    self.new_game()
                    nextstate = Game.STATE_LOADING
        elif self.state == Game.STATE_LOADING:
            if len(self.async_fetcher.fetched) > 0:
                req_image = self.async_fetcher.fetched.pop(0)
                self.current_words = req_image.words
                self.img_word = req_image.iword
                self.model = ModelIter(req_image.path)
                nextstate = Game.STATE_DRAWING
        elif self.state == Game.STATE_DRAWING:
            assert self.prev_draw_time is None or time > self.prev_draw_time
            if self.prev_draw_time is None \
                or (time - self.prev_draw_time) > Game.IMAGE_RATE_MILLIS:
                self.prev_draw_time = time
                self.draw_step_drawing_screen()
            for event in events:
                if (event.type == pg.KEYDOWN
                    and (event.key in Game.P1_CONTROLS
                        or event.key in Game.P2_CONTROLS)):
                    self.events.append(event.key)
                    winner = self.check_winner(event.key)
                    print('Player %d wins point' % winner)
                    self.update_score(winner)
                    print('Score %d' % self.score)
                    nextstate = Game.STATE_GUESSED
                    self.timeout = time + Game.GUESS_TIMEOUT
        elif self.state == Game.STATE_GUESSED:
            if time > self.timeout:
                if self.score == Game.SCORE_WIN:
                    self.timeout = time + Game.WINNER_TIMEOUT
                    nextstate = Game.STATE_WINNER
                else:
                    nextstate = Game.STATE_LOADING
        elif self.state == Game.STATE_WINNER:
            if time > self.timeout:
                nextstate = Game.STATE_NEWGAME

        # enter the next state
        if nextstate is not None:
            if nextstate == Game.STATE_NEWGAME:
                self.draw_newgame_screen()
            elif nextstate == Game.STATE_LOADING:
                self.draw_loading_screen()
                self.model = None
            elif nextstate == Game.STATE_DRAWING:
                self.events = []
                self.draw_drawing_screen()
            elif nextstate == Game.STATE_GUESSED:
                self.draw_guessed_screen()
            elif nextstate == Game.STATE_WINNER:
                self.draw_winner_screen()
                
            # set the new state
            self.state = nextstate

class Main:

    FRAMERATE = 120

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

