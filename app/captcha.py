#!/usr/bin/env python3


import re
import random
from PIL import Image
from PIL import ImageDraw
from PIL import ImageFont
from PIL import ImageOps
from PIL import ImageFilter


CAPTCHA_CHARS = '345ACEFGHKLMNPRSTWXZacdefhkmnpswx'
CAPTCHA_REGEX = re.compile('[0-9A-z]{4}')


WIDTH = 180
HEIGHT = 75
ROTATE = 30
FONT = ImageFont.truetype('resources/Cantarell-Bold.otf', 36)


def gen_captcha():
    '''Generate a captcha string

    @return str
    '''
    return ''.join(random.choice(CAPTCHA_CHARS) for i in range(0, 4))


def gen_image(content):
    '''Generate a PNG image of the captcha with text content `content`

    @param str content
    @return PIL.Image
    '''

    # ======================================================================
    # Snippet modified from https://github.com/lepture/captcha
    # LICENSE: New BSD License

    image = Image.new('RGB', (WIDTH, HEIGHT))
    draw = ImageDraw.Draw(image)

    def draw_character(c, font=FONT):
        w, h = draw.textsize(c, font=font)

        dx = random.randint(0, 4)
        dy = random.randint(0, 6)
        im = Image.new('RGBA', (w + dx, h + dy))
        ImageDraw.Draw(im).text((dx, dy), c, font=font)

        # rotate
        im = im.crop(im.getbbox())
        im = im.rotate(
            random.uniform(-ROTATE, ROTATE),
            Image.BILINEAR,
            expand=1
        )

        # warp
        dx = w * random.uniform(0.1, 0.3)
        dy = h * random.uniform(0.2, 0.3)
        x1 = int(random.uniform(-dx, dx))
        y1 = int(random.uniform(-dy, dy))
        x2 = int(random.uniform(-dx, dx))
        y2 = int(random.uniform(-dy, dy))
        w2 = w + abs(x1) + abs(x2)
        h2 = h + abs(y1) + abs(y2)
        data = (
            x1, y1,
            -x1, h2 - y2,
            w2 + x2, h2 + y2,
            w2 - x2, -y1,
        )
        im = im.resize((w2, h2))
        im = im.transform((w, h), Image.QUAD, data)
        return im

    images = []
    for c in content:
        images.append(draw_character(c))

    text_width = sum([im.size[0] for im in images])

    width = max(text_width, WIDTH)
    image = image.resize((width, HEIGHT))

    average = int(text_width / len(content))
    rand = int(0.25 * average)
    offset = int(average * 0.1) + 20

    for im in images:
        w, h = im.size
        mask = im.convert('L').point(lambda i: i * 1.97)
        image.paste(im, (offset, int((HEIGHT - h) / 2)), mask)
        offset = offset + w + random.randint(-rand, 0) + 20

    # ======================================================================

    def rand_points():
        return [
            (random.uniform(0, WIDTH), 0),
            (random.uniform(0, WIDTH), HEIGHT)
        ]

    for i in range(0, 20):
        draw.ellipse(rand_points(), outline='black')

    for i in range(0, 5):
        draw.line(
            rand_points(),
            fill = random.choice(['black', 'white']),
            width = random.choice([2, 3])
        )

    image = ImageOps.invert(image)
    image = image.filter(ImageFilter.SMOOTH)
    return image
