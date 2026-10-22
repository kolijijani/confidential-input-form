#!/usr/bin/env python3
"""Build a GitHub social-preview card (1280x640) from the real product screenshot.

No gradients, no glow, no abstract shapes: wordmark + one sentence + the actual
form, clamped to the same 15:8 box GitHub uses for link previews.
"""
"""Build the GitHub social preview card (1280x640) from the demo GIF.

Usage:  python3 scripts/make_social_preview.py
Needs Pillow (pip install pillow); this is the only script in the repo with a
third-party dependency and it never runs in the product path.
"""
from PIL import Image, ImageChops, ImageDraw, ImageFont

W, H = 1280, 640
BG = (11, 12, 16)
CARD = (21, 23, 31)
BORDER = (48, 51, 61)
WHITE = (232, 231, 237)
GREY = (168, 168, 179)
DIM = (133, 136, 148)
LIME = (163, 230, 53)

INTER = "/usr/share/fonts/opentype/inter/"
MONO = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"

shot = Image.open("docs/screenshots/terminal-vault.png").convert("RGB")

# trim page background precisely: keeps only rows/columns that carry content
bg_probe = shot.getpixel((2, 2))
mask = ImageChops.difference(shot, Image.new("RGB", shot.size, bg_probe)).convert("L")
mask = mask.point(lambda v: 255 if v > 8 else 0)
mp = mask.load()
rows = [sum(1 for x in range(0, shot.width, 4) if mp[x, y]) for y in range(shot.height)]
top = next(i for i, v in enumerate(rows) if v > 2)
bottom = max(i for i, v in enumerate(rows) if v > 2)
cols = [sum(1 for y in range(top, bottom + 1, 4) if mp[x, y]) for x in range(shot.width)]
left = next(i for i, v in enumerate(cols) if v > 1)
right = max(i for i, v in enumerate(cols) if v > 1)
pad = 12
shot = shot.crop((max(0, left - pad), max(0, top - pad),
                  min(shot.width, right + pad), min(shot.height, bottom + pad)))

img = Image.new("RGB", (W, H), BG)
d = ImageDraw.Draw(img)

f_mono = ImageFont.truetype(MONO, 22)
f_head = ImageFont.truetype(INTER + "InterDisplay-Black.otf", 58)
f_sub = ImageFont.truetype(INTER + "InterDisplay-Medium.otf", 25)
f_small = ImageFont.truetype(MONO, 19)

# wordmark
x = 80
y = 96
d.text((x, y), "// secret", font=f_mono, fill=WHITE)
w1 = d.textlength("// secret", font=f_mono)
d.text((x + w1, y), "_vault", font=f_mono, fill=LIME)

# headline
d.text((x, y + 54), "Hand over a secret", font=f_head, fill=WHITE)
d.text((x, y + 54 + 70), "without typing it", font=f_head, fill=WHITE)
d.text((x, y + 54 + 140), "into chat.", font=f_head, fill=WHITE)

# subline
sub = "One-shot local form. It writes straight to a\nprotected 0600 file, then closes itself."
d.multiline_text((x, y + 300), sub, font=f_sub, fill=GREY, spacing=10)

# footer
d.text((x, H - 96), "github.com/kolijijani/confidential-input-form", font=f_small, fill=DIM)
d.text((x, H - 68), "python stdlib · MIT · linux / macOS", font=f_small, fill=DIM)

# screenshot on the right, cropped to the form area
target_h = H - 112
scale = target_h / shot.height
max_w = W - 620
if shot.width * scale > max_w:
    scale = max_w / shot.width
shot_r = shot.resize((int(shot.width * scale), int(shot.height * scale)), Image.LANCZOS)
card_x = W - shot_r.width - 56
card_y = (H - shot_r.height) // 2

# subtle card frame behind the screenshot
pad = 10
d.rounded_rectangle(
    [card_x - pad, card_y - pad, card_x + shot_r.width + pad, card_y + shot_r.height + pad],
    radius=18, fill=CARD, outline=BORDER, width=1,
)
mask = Image.new("L", shot_r.size, 0)
ImageDraw.Draw(mask).rounded_rectangle([0, 0, shot_r.width, shot_r.height], radius=12, fill=255)
img.paste(shot_r, (card_x, card_y), mask)

img.save("docs/social-preview.png", optimize=True)
print("saved", img.size)
