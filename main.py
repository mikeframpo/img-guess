
import pygame
import sys

sys.path.append('Quads')
from quads import Model

class ModelIter:

    def __init__(self, path):
        self.model = Model(path)

    def step(self):
        self.model.split()
        return self.model.render()

class Main:

    def __init__(self, path):
        pygame.init()
        self.screen = pygame.display.set_mode((640, 480))
        self.model = ModelIter(path)

    def mainloop(self):

        # test code for drawing the initial image
        im = self.model.step()
        surface = pygame.image.fromstring(im.tostring(), im.size, im.mode)
        self.screen.blit(surface, (0,0))
        pygame.display.flip()

        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    sys.exit()

if __name__ == '__main__':

    args = sys.argv[1:]
    if len(args) != 1:
        print 'Usage: python main.py input_image'
        sys.exit(1)
    
    main = Main(args[0])
    main.mainloop()

