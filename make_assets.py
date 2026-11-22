#!/usr/bin/env python3
"""Visual assets for the SkillDoctor README: a masthead and a demo shot.
The demo image renders the tool's real --demo output inside a terminal
window, so a visitor sees exactly what the tool prints.
"""
import os, subprocess, sys
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
A = os.path.join(HERE, "assets"); os.makedirs(A, exist_ok=True)
FD = os.path.expanduser("~/workspace/github-profile-redo/fonts")
SERIF = os.path.join(FD, "InstrumentSerif-Regular.ttf")
SERIFI = os.path.join(FD, "InstrumentSerif-Italic.ttf")
INTER = os.path.join(FD, "Inter.ttf")
MONO = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"
MONOB = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf"

def F(p, s): return ImageFont.truetype(p, s)

def tracked(d, x, y, txt, font, fill, tr):
    for ch in txt:
        d.text((x, y), ch, font=font, fill=fill)
        x += d.textlength(ch, font=font) + tr
    return x

# ---------------------------------------------------------------- masthead
W, H = 2240, 1040
img = Image.new("RGB", (W, H), (20, 20, 20))
d = ImageDraw.Draw(img)
BONE = (242, 239, 233); GOLD = (169, 139, 79); MUT = (138, 134, 128)
# gold pulse line across the upper third, a heartbeat for a doctor
pts = [(120, 300), (760, 300), (830, 300), (880, 190), (950, 420), (1010, 300), (1500, 300), (1560, 240), (1620, 300), (2120, 300)]
d.line(pts, fill=GOLD, width=5, joint="curve")
# title
t = "SkillDoctor"; fnt = F(SERIF, 215)
tw = d.textlength(t, font=fnt)
d.text(((W - tw) / 2, 470), t, font=fnt, fill=BONE)
# gold caps line
e = "A CHECKUP FOR THE SKILLS YOUR AI RUNS"
f2 = F(INTER, 40)
tw = sum(d.textlength(ch, font=f2) + 10 for ch in e) - 10
tracked(d, (W - tw) / 2, 745, e, f2, GOLD, 10)
# italic claim
c = "Your AI is running skills you never audited."
f3 = F(SERIFI, 52)
tw = d.textlength(c, font=f3)
d.text(((W - tw) / 2, 830), c, font=f3, fill=(200, 195, 185))
img.save(os.path.join(A, "masthead.png"))

# ---------------------------------------------------------------- demo shot
out = subprocess.run([sys.executable, os.path.join(HERE, "skilldoctor.py"), "--demo"],
                     capture_output=True, text=True).stdout.rstrip("\n").split("\n")
FS = 25
LH = 37
PAD = 44
W2 = 1500
H2 = 92 + PAD + len(out) * LH + 26
img = Image.new("RGB", (W2, H2), (21, 24, 26))
d = ImageDraw.Draw(img)
# window chrome
for i, col in enumerate([(224, 92, 84), (224, 182, 84), (84, 190, 110)]):
    d.ellipse([34 + i * 40, 32, 58 + i * 40, 56], fill=col)
tt = "skilldoctor --demo"
fnt = F(MONO, 22)
d.text(((W2 - d.textlength(tt, font=fnt)) / 2, 32), tt, font=fnt, fill=(150, 155, 150))
d.line([(0, 92), (W2, 92)], fill=(52, 57, 60), width=2)
RED = (229, 99, 92); GREEN = (88, 196, 117); AMBER = (224, 182, 84); TXT = (216, 213, 205); DIM = (140, 145, 140)
y = 92 + PAD
for line in out:
    col = TXT; fnt = F(MONO, FS)
    if line.startswith("FAIL"): col = RED; fnt = F(MONOB, FS)
    elif line.startswith("OK"): col = GREEN; fnt = F(MONOB, FS)
    elif line.startswith("WARN"): col = AMBER; fnt = F(MONOB, FS)
    elif line.startswith("SkillDoctor"): col = (242, 239, 233); fnt = F(MONOB, FS)
    elif "[high]" in line or "[error]" in line: col = (240, 170, 162)
    elif "[warn]" in line: col = (238, 205, 140)
    elif line.startswith("Summary") or line.startswith("Always-on"): col = (242, 239, 233)
    elif line.startswith("      -"): col = col
    elif line.startswith("      "): col = DIM
    d.text((PAD, y), line, font=fnt, fill=col)
    y += LH
img.save(os.path.join(A, "demo.png"))
print("assets built:", os.listdir(A))
