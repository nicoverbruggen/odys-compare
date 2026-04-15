#!/usr/bin/env python3
"""Build the experimental OpenDyslexic T and UT variants.

Both are kernless, metrics-tightened derivatives of upstream OpenDyslexic v0.99.
T is moderately tight (-90u advance, space 847->560).
UT is aggressively tight (-150u advance, space 847->480).

Steps applied to every cut (Regular, Bold, Italic, BoldItalic):
  1. Shrink every glyph's advance width by ADV_DELTA and shift outlines left
     by |ADV_DELTA|/2 so tightening is symmetric on both sidebearings.
  2. Narrow the space glyph to SPACE_ADV.
  3. Strip all kerning (GPOS PairPos lookups + legacy `kern` table). The
     Italic/BoldItalic upstream cuts ship with kerning; T/UT are kernless by
     design, so we remove it for consistency.
  4. Disable the `liga`/`dlig`/`rlig` GSUB features so fi/fl sequences render
     as separate glyphs.
  5. For Italic and BoldItalic only: skew quote glyphs by QUOTE_SKEW_DEG
     (negative = leaning left relative to upstream) and add QUOTE_PAD units
     of advance (half on each side) so quoted passages breathe.
  6. Rewrite the `name` table so the family reads "OpenDyslexic T" / "UT".

Usage:
    python3 build_tight.py [--src DIR]

Requires fontTools. By default source OTFs are read from ./src/0.99/ (drop the
four upstream v0.99 OpenDyslexic-*.otf files there). Outputs go to
./public/fonts/T/ and ./public/fonts/UT/.
"""

from __future__ import annotations
import argparse
import math
import os
from fontTools.ttLib import TTFont
from fontTools.pens.t2CharStringPen import T2CharStringPen
from fontTools.pens.transformPen import TransformPen

REPO_ROOT = os.path.dirname(os.path.abspath(__file__))
DEFAULT_SRC_DIR = os.path.join(REPO_ROOT, "src", "0.99")
OUT_ROOT = os.path.join(REPO_ROOT, "public", "fonts")

STYLES = [
    ("Regular",    "OpenDyslexic-Regular.otf"),
    ("Bold",       "OpenDyslexic-Bold.otf"),
    ("Italic",     "OpenDyslexic-Italic.otf"),
    ("BoldItalic", "OpenDyslexic-BoldItalic.otf"),
]

VARIANTS = {
    "T":  {"adv_delta": -90,  "space": 560},
    "UT": {"adv_delta": -150, "space": 480},
}

QUOTE_GLYPHS = (
    "quoteleft", "quoteright", "quotedblleft", "quotedblright",
    "quotesinglbase", "quotedblbase", "quotesingle", "quotedbl",
)
QUOTE_SKEW_DEG = -12   # leans quotes opposite to the italic body slant
QUOTE_PAD = 120        # total extra advance per quote glyph (half each side)


def shift_cff_outlines(font: TTFont, dx: int) -> None:
    """Shift every glyph's outline left/right by `dx` units (CFF only)."""
    charStrings = font["CFF "].cff.topDictIndex[0].CharStrings
    for gname in charStrings.keys():
        cs = charStrings[gname]
        cs.decompile()
        prog = cs.program
        i, args = 0, []
        while i < len(prog) and not isinstance(prog[i], str):
            args.append(prog[i]); i += 1
        if i >= len(prog):
            continue
        op = prog[i]
        if op == "rmoveto" and len(args) >= 2:
            prog[i - 2] = args[-2] + dx
        elif op == "hmoveto" and len(args) >= 1:
            prog[i - 1] = args[-1] + dx
        elif op == "vmoveto":
            prog[: i + 1] = [dx, args[-1], "rmoveto"]
        cs.program = prog


def retarget_metrics(font: TTFont, adv_delta: int, space_adv: int, shift: int) -> None:
    hmtx = font["hmtx"]
    new = {}
    for gname, (aw, lsb) in hmtx.metrics.items():
        if gname == "space":
            new[gname] = (space_adv, lsb)
        else:
            new[gname] = (max(0, aw + adv_delta), lsb + shift)
    hmtx.metrics = new


def strip_kerning(font: TTFont) -> None:
    if "kern" in font:
        del font["kern"]
    if "GPOS" in font:
        gpos = font["GPOS"].table
        if any(l.LookupType == 2 for l in gpos.LookupList.Lookup):
            del font["GPOS"]


def disable_ligatures(font: TTFont) -> None:
    if "GSUB" not in font:
        return
    fl = font["GSUB"].table.FeatureList
    for fr in fl.FeatureRecord:
        if fr.FeatureTag in ("liga", "dlig", "rlig"):
            fr.Feature.LookupListIndex = []
            fr.Feature.LookupCount = 0


def restyle_quotes(font: TTFont) -> None:
    """Skew and pad quote glyphs for the italic cuts."""
    cff = font["CFF "].cff
    cs = cff.topDictIndex[0].CharStrings
    glyphSet = font.getGlyphSet()
    hmtx = font["hmtx"]
    skew = math.tan(math.radians(QUOTE_SKEW_DEG))
    for gname in QUOTE_GLYPHS:
        if gname not in cs:
            continue
        glyph = glyphSet[gname]
        aw, lsb = hmtx[gname]
        new_aw = aw + QUOTE_PAD
        pen = T2CharStringPen(new_aw, glyphSet)
        tpen = TransformPen(pen, (1, 0, skew, 1, QUOTE_PAD // 2, 0))
        glyph.draw(tpen)
        cs[gname] = pen.getCharString(
            private=cs[gname].private, globalSubrs=cs[gname].globalSubrs
        )
        hmtx[gname] = (new_aw, lsb + QUOTE_PAD // 2)


def rename_family(font: TTFont, variant_tag: str) -> None:
    for rec in font["name"].names:
        s = rec.toUnicode()
        if "OpenDyslexic" not in s:
            continue
        # Avoid double-prefixing if already done.
        after = s.split("OpenDyslexic", 1)[1]
        if after.lstrip().startswith(variant_tag):
            continue
        s2 = s.replace("OpenDyslexic", f"OpenDyslexic {variant_tag}", 1)
        try:
            rec.string = (
                s2.encode("utf-16-be") if rec.platformID == 3
                else s2.encode("mac-roman", errors="replace")
            )
        except Exception:
            rec.string = s2.encode("utf-8", errors="replace")


def build(src: str, out: str, variant: str, style: str, adv_delta: int, space_adv: int) -> None:
    font = TTFont(src)
    shift = -abs(adv_delta) // 2
    shift_cff_outlines(font, shift)
    retarget_metrics(font, adv_delta, space_adv, shift)
    strip_kerning(font)
    disable_ligatures(font)
    if "Italic" in style:
        restyle_quotes(font)
    rename_family(font, variant)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    font.save(out)
    print(f"wrote {out}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--src", default=DEFAULT_SRC_DIR,
        help=f"directory containing upstream v0.99 OpenDyslexic-*.otf files (default: {DEFAULT_SRC_DIR})",
    )
    args = parser.parse_args()

    missing = [n for _, n in STYLES if not os.path.isfile(os.path.join(args.src, n))]
    if missing:
        raise SystemExit(
            f"Missing upstream source OTFs in {args.src}:\n  "
            + "\n  ".join(missing)
            + "\n\nDownload OpenDyslexic v0.99 from https://forge.hackers.town/antijingoist/opendyslexic"
              " and place the four Regular/Bold/Italic/BoldItalic OTFs in that directory."
        )

    for variant, params in VARIANTS.items():
        for style, src_name in STYLES:
            src = os.path.join(args.src, src_name)
            out = os.path.join(OUT_ROOT, variant, f"{variant}-{style}.otf")
            build(src, out, variant, style, params["adv_delta"], params["space"])


if __name__ == "__main__":
    main()
