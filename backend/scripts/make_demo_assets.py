"""Generate SYNTHETIC demo assets: a handwritten-style prescription and a medicine strip label.

Usage: python scripts/make_demo_assets.py
Fonts: Reenie Beanie (OFL) and Homemade Apple (Apache 2.0) from Google Fonts, in demo_assets/fonts/.
The doctor, clinic and patient are fictional. Every image is watermarked as synthetic.
"""
import random
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "demo_assets"
FONTS = OUT / "fonts"
PRINT_FONT = "/System/Library/Fonts/Supplemental/Arial.ttf"
PRINT_BOLD = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"
INK = (28, 45, 140)

CONTEXT = "Fever and body ache for 3 days. Known vitamin D deficiency with joint pain. Allergic to penicillin."


def font(path, size):
    try:
        return ImageFont.truetype(str(path), size)
    except OSError:
        return ImageFont.load_default()


def scrawl(img, xy, text, fnt, angle=0.0, fill=INK):
    """Draw text on its own layer, rotated slightly, to imitate a hand-written line."""
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(layer).text(xy, text, font=fnt, fill=fill + (235,))
    layer = layer.rotate(angle, center=xy, resample=Image.BICUBIC)
    img.alpha_composite(layer)
    return ImageDraw.Draw(img).textbbox(xy, text, font=fnt)


def prescription():
    random.seed(7)
    img = Image.new("RGBA", (1400, 1800), (252, 250, 244, 255))
    d = ImageDraw.Draw(img)
    # Printed letterhead (fictional clinic).
    d.rectangle([0, 0, 1400, 190], fill=(232, 244, 241, 255))
    d.text((60, 40), "Dr. Meera Iyer, MBBS, MD (General Medicine)", font=font(PRINT_BOLD, 44), fill=(15, 80, 75))
    d.text((60, 100), "Sunrise Family Clinic (fictional) · Reg. No. DEMO-0000", font=font(PRINT_FONT, 30), fill=(60, 60, 60))
    d.line([(60, 200), (1340, 200)], fill=(15, 118, 110), width=4)
    d.text((60, 225), "Patient: Ramesh K. (fictional)    Age/Sex: 58/M    Date: 30/10/2026", font=font(PRINT_FONT, 30), fill=(40, 40, 40))
    d.text((60, 300), "Rx", font=font(PRINT_BOLD, 80), fill=(15, 80, 75))

    hand = font(FONTS / "HomemadeApple.ttf", 58)
    hand_small = font(FONTS / "ReenieBeanie.ttf", 70)
    scrawl(img, (90, 420), "c/o fever, bodyache x 3d · Vit D def", hand_small, angle=1.2)

    lines = [
        ("1)  Tab. Dolo 650", "1 - 1 - 1  TDS x 5d"),
        ("2)  Tab. Combiflam", "1  SOS"),
        ("3)  Tab. Augmentin 625 Duo", "1 - 0 - 1  BD x 5d"),
    ]
    y = 560
    for left, right in lines:
        box = scrawl(img, (90, y), left, hand, angle=random.uniform(-2.0, 1.5))
        scrawl(img, (max(820, box[2] + 50), y + 10), right, hand_small, angle=random.uniform(-2.5, 2.5))
        y += 190

    # Line 4: the vowel after "C" is a smudged a/e, so "Calcimax" vs "Celemax" is genuinely ambiguous.
    x0, y0 = 90, y
    box = scrawl(img, (x0, y0), "4)  Tab. C", hand, angle=-1.0)
    vowel = Image.new("RGBA", img.size, (0, 0, 0, 0))
    vd = ImageDraw.Draw(vowel)
    vx = box[2] - 4
    vd.text((vx, y0), "a", font=hand, fill=INK + (200,))
    vd.text((vx + 4, y0 + 3), "e", font=hand, fill=INK + (215,))
    img.alpha_composite(vowel.filter(ImageFilter.GaussianBlur(0.9)))
    vw = ImageDraw.Draw(img).textbbox((0, 0), "a", font=hand)[2]
    scrawl(img, (vx + vw - 2, y0 + 2), "lcimax", hand, angle=-1.5)
    scrawl(img, (820, y0 + 14), "1  OD x 3 mo", hand_small, angle=2.0)

    scrawl(img, (860, 1450), "Dr. M. Iyer", font(FONTS / "HomemadeApple.ttf", 50), angle=4)
    d = ImageDraw.Draw(img)
    d.text((60, 1720), "SYNTHETIC DEMO PRESCRIPTION · generated for AushNexa · not a real patient or doctor", font=font(PRINT_FONT, 26), fill=(150, 150, 150))
    # Light paper noise, so it isn't too clean.
    noise = Image.effect_noise(img.size, 12).convert("L")
    img = Image.composite(img, Image.new("RGBA", img.size, (236, 233, 225, 255)), noise.point(lambda p: 255 if p > 40 else 225))
    img.convert("RGB").rotate(-1.2, expand=False, fillcolor=(240, 238, 230)).save(OUT / "prescription.jpg", quality=88)


def strip():
    img = Image.new("RGB", (1200, 700), (200, 204, 210))
    d = ImageDraw.Draw(img)
    for x in range(0, 1200, 6):  # foil sheen
        shade = 196 + int(18 * ((x // 6) % 7) / 7)
        d.line([(x, 0), (x, 700)], fill=(shade, shade + 3, shade + 8))
    d.rounded_rectangle([60, 60, 1140, 640], radius=30, outline=(90, 90, 100), width=4)
    d.text((110, 110), "PARACETAMOL TABLETS I.P.", font=font(PRINT_BOLD, 64), fill=(20, 40, 120))
    d.text((110, 200), "500 mg", font=font(PRINT_BOLD, 96), fill=(170, 20, 40))
    d.text((110, 340), "Each uncoated tablet contains:", font=font(PRINT_FONT, 36), fill=(30, 30, 30))
    d.text((110, 390), "Paracetamol I.P. ............ 500 mg", font=font(PRINT_FONT, 36), fill=(30, 30, 30))
    d.text((110, 450), "10 Tablets · Store below 30°C · Batch DEMO01", font=font(PRINT_FONT, 32), fill=(50, 50, 50))
    d.text((110, 580), "SYNTHETIC DEMO STRIP · generated for AushNexa", font=font(PRINT_FONT, 26), fill=(110, 110, 110))
    img.rotate(2.5, expand=False, fillcolor=(190, 190, 195)).save(OUT / "strip.jpg", quality=88)


def ink_blot():
    """Re-open the saved prescription and drop an ink blot over line 4's drug name (a realistic smudge)."""
    img = Image.open(OUT / "prescription.jpg").convert("RGBA")
    y0, y1 = 1154, 1210  # ink rows of line 4
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(layer).ellipse((405, y0 + 2, 545, y1 - 2), fill=(30, 45, 130, 175))
    img.alpha_composite(layer.filter(ImageFilter.GaussianBlur(10)))
    img.convert("RGB").save(OUT / "prescription.jpg", quality=88)


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    prescription()
    ink_blot()
    strip()
    (OUT / "context.txt").write_text(CONTEXT + "\n")
    (OUT / "allergies.txt").write_text("penicillin\n")
    print("wrote", *(p.name for p in sorted(OUT.glob("*.*"))))
