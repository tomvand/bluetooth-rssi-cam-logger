# Helper function to extract and show images from a .zip log file
from io import BytesIO
import pygame
import sys

resolution = (640,480)
screen = pygame.display.set_mode(resolution)

def show_image(zipfile, timestamp):
    # extract the image from the zip file
    filename_list = zipfile.namelist()
    filename = timestamp.strftime("%Y%m%d-%H.%M.%S.jpg")
    pygame.display.set_caption(filename)
    filename = next(name for name in filename_list if name.endswith(filename))
    print "Opening image '{}'...".format(filename)
    try:
        img_data = zipfile.read(filename)
        image = pygame.image.load(BytesIO(img_data))
        screen.blit(pygame.transform.scale(image, resolution), (0,0))
        pygame.display.flip()
    except Exception:
        print "Can open '{}'.".format(filename)