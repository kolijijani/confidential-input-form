#!/usr/bin/env python3
"""Build the repo banner (1280x320) in the same spirit as a hand-made wordmark header.

Dark grain background, one big mono wordmark, one small line underneath. No
gradients, no glow, no icon: the text is the brand.
"""
import random

from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H = 1280, 320
BG = (10, 11, 15)
WHITE = (236, 235, 240)
LIME = (163, 230, 53)
DIM = (140, 143, 155)
MONO_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf"
MONO = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"

img = Image.new("RGB", (W, H), BG)

# film-grain texture: small, deterministic, low contrast
rnd = random.Random(20261022)
noise = Image.new("L", (W, H))
noise.putdata([rnd.randint(0, 26) for _ in range(W * H)])
noise = noise.filter(ImageFilter.GaussianBlur(0.6))
img = Image.composite(Image.new("RGB", (W, H), (26, 27, 33)), img, noise.point(lambda v: v * 2))

d = ImageDraw.Draw(img)

f_word = ImageFont.truetype(MONO_BOLD, 96)
f_sub = ImageFont.truetype(MONO, 24)

word_a = "// secret"
word_b = "_vault"
wa = d.textlength(word_a, font=f_word)
wb = d.textlength(word_b, font=f_word)
total = wa + wb
x = (W - total) / 2
baseline_y = 112

d.text((x, baseline_y), word_a, font=f_word, fill=WHITE)
d.text((x + wa, baseline_y), word_b, font=f_word, fill=LIME)

sub = "one-shot form for handing secrets to an agent"
sw = d.textlength(sub, font=f_sub)
d.text(((W - sw) / 2, baseline_y + 120), sub, font=f_sub, fill=DIM)

handle = "github.com/kolijijani"
hw = d.textlength(handle, font=f_sub)
d.text(((W - hw) / 2, H - 58), handle, font=f_sub, fill=(96, 99, 110))

img.save("docs/banner.png", optimize=True)
print("saved docs/banner.png", img.size)
