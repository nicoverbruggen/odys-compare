#!/usr/bin/env python3
"""Build the experimental OpenDyslexic T and UT variants.

Both are kernless, metrics-tightened derivatives of upstream OpenDyslexic v0.99.
T is moderately tight (-90u advance, space 847->560).
UT is aggressively tight (-150u advance, space 847->480).

Italic and BoldItalic are *synthesized* from the Regular/Bold sources via a
horizontal shear (SLANT_DEG). The upstream Italic/BoldItalic files are not
used.

Steps applied to every cut (Regular, Bold, Italic, BoldItalic):
  1. Shrink every glyph's advance width by ADV_DELTA and shift outlines left
     by |ADV_DELTA|/2 so tightening is symmetric on both sidebearings. For
     Italic/BoldItalic a shear of SLANT_DEG is also applied in the same pass.
     Digits and punctuation (Unicode categories N* and P*) are exempt and
     keep their upstream metrics and outline positions — so punctuation stays
     upright inside the slanted body.
  2. Narrow the space glyph to SPACE_ADV.
  3. Strip all kerning (GPOS PairPos lookups + legacy `kern` table).
  4. Disable the `liga`/`dlig`/`rlig` GSUB features so fi/fl sequences render
     as separate glyphs.
  5. For Italic/BoldItalic only: pad quote glyphs with QUOTE_PAD units of
     advance (half on each side) so quoted passages breathe; flip the italic
     flags in `head`/`OS/2`/`post` and relabel the subfamily name records.
  6. Add PUNCT_PAD units of *leading* space before period/comma/colon/
     semicolon/exclam/question/ellipsis so they don't hug the preceding word.
  7. Rewrite the `name` table so the family reads "OpenDyslexic T" / "UT"
     (PostScript names use no-space form, e.g. "OpenDyslexicT-Regular").

Usage:
    python3 build_tight.py [--src DIR]

Requires fontTools. By default source OTFs are read from ./src/0.99/ (drop
the Regular and Bold upstream v0.99 OpenDyslexic OTFs there). Outputs go to
./public/fonts/T/ and ./public/fonts/UT/.
"""

from __future__ import annotations
import argparse
import math
import os
import unicodedata
from fontTools.ttLib import TTFont
from fontTools.pens.t2CharStringPen import T2CharStringPen
from fontTools.pens.transformPen import TransformPen

REPO_ROOT = os.path.dirname(os.path.abspath(__file__))
DEFAULT_SRC_DIR = os.path.join(REPO_ROOT, "src", "0.99")
OUT_ROOT = os.path.join(REPO_ROOT, "public", "fonts")

# (output style, upstream source, italic?)
STYLES = [
    ("Regular",    "OpenDyslexic-Regular.otf", False),
    ("Bold",       "OpenDyslexic-Bold.otf",    False),
    ("Italic",     "OpenDyslexic-Regular.otf", True),
    ("BoldItalic", "OpenDyslexic-Bold.otf",    True),
]

# Italic cuts remap subfamily name records from their roman source string.
STYLE_REMAP = {
    "Italic":     ("Regular", "Italic"),
    "BoldItalic": ("Bold",    "Bold Italic"),
}
STYLE_NAMEIDS = {2, 4, 6, 17}   # subfamily, full name, postscript, typographic subfamily

VARIANTS = {
    "T":  {"adv_delta": -90,  "space": 560},
    "UT": {"adv_delta": -150, "space": 480},
}

SLANT_DEG = 12         # synthetic-italic forward shear

QUOTE_GLYPHS = (
    "quoteleft", "quoteright", "quotedblleft", "quotedblright",
    "quotesinglbase", "quotedblbase", "quotesingle", "quotedbl",
)
QUOTE_PAD = 60        # total extra advance per quote glyph (half each side)

PUNCT_PAD_GLYPHS = (
    "period", "comma", "colon", "semicolon",
    "exclam", "question", "ellipsis",
)
PUNCT_PAD = 80        # units of extra advance added entirely on the left side


def excluded_glyphs(font: TTFont) -> set[str]:
    """Glyph names whose Unicode codepoint is a digit or punctuation — kept untouched."""
    out = set()
    for cp, gname in font.getBestCmap().items():
        cat = unicodedata.category(chr(cp))
        if cat[:1] in ("N", "P"):
            out.add(gname)
    return out


def shift_cff_outlines(font: TTFont, dx: int, slant: float, skip: set[str]) -> None:
    """Redraw every non-skipped glyph through a translate+shear transform.

    Pen-based redraw is required (rather than patching the top-level moveto):
    upstream OpenDyslexic stores every outline in a shared subroutine, so
    the CharString is just `[width, subr_idx, callsubr]` with no moveto to
    patch. `glyph.draw(tpen)` expands the subroutine calls.

    Must run *after* `retarget_metrics` so the pen reads the final advance
    width from hmtx. Subroutine sharing is lost; the resulting OTF is larger.
    """
    cs = font["CFF "].cff.topDictIndex[0].CharStrings
    glyphSet = font.getGlyphSet()
    hmtx = font["hmtx"]
    for gname in list(cs.keys()):
        if gname in skip:
            continue
        glyph = glyphSet[gname]
        aw, _ = hmtx[gname]
        pen = T2CharStringPen(aw, glyphSet)
        tpen = TransformPen(pen, (1, 0, slant, 1, dx, 0))
        glyph.draw(tpen)
        cs[gname] = pen.getCharString(
            private=cs[gname].private, globalSubrs=cs[gname].globalSubrs
        )


def retarget_metrics(font: TTFont, adv_delta: int, space_adv: int, shift: int, skip: set[str]) -> None:
    hmtx = font["hmtx"]
    new = {}
    for gname, (aw, lsb) in hmtx.metrics.items():
        if gname == "space":
            new[gname] = (space_adv, lsb)
        elif gname in skip:
            new[gname] = (aw, lsb)
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


def pad_quotes(font: TTFont, slant: float) -> None:
    """Pad quote glyphs with QUOTE_PAD units of advance, half on each side.

    Quotes are in the skip set so the body-pass shear didn't touch them; we
    apply the same shear here so italic quotes lean with the rest of the
    text rather than standing upright inside it.
    """
    cs = font["CFF "].cff.topDictIndex[0].CharStrings
    glyphSet = font.getGlyphSet()
    hmtx = font["hmtx"]
    for gname in QUOTE_GLYPHS:
        if gname not in cs:
            continue
        glyph = glyphSet[gname]
        aw, lsb = hmtx[gname]
        new_aw = aw + QUOTE_PAD
        pen = T2CharStringPen(new_aw, glyphSet)
        tpen = TransformPen(pen, (1, 0, slant, 1, QUOTE_PAD // 2, 0))
        glyph.draw(tpen)
        cs[gname] = pen.getCharString(
            private=cs[gname].private, globalSubrs=cs[gname].globalSubrs
        )
        hmtx[gname] = (new_aw, lsb + QUOTE_PAD // 2)


def pad_punctuation(font: TTFont) -> None:
    """Add PUNCT_PAD units of leading whitespace to sentence-ending punctuation."""
    cs = font["CFF "].cff.topDictIndex[0].CharStrings
    glyphSet = font.getGlyphSet()
    hmtx = font["hmtx"]
    for gname in PUNCT_PAD_GLYPHS:
        if gname not in cs:
            continue
        glyph = glyphSet[gname]
        aw, lsb = hmtx[gname]
        new_aw = aw + PUNCT_PAD
        pen = T2CharStringPen(new_aw, glyphSet)
        tpen = TransformPen(pen, (1, 0, 0, 1, PUNCT_PAD, 0))
        glyph.draw(tpen)
        cs[gname] = pen.getCharString(
            private=cs[gname].private, globalSubrs=cs[gname].globalSubrs
        )
        hmtx[gname] = (new_aw, lsb + PUNCT_PAD)


def _set_name(rec, s: str) -> None:
    try:
        rec.string = (
            s.encode("utf-16-be") if rec.platformID == 3
            else s.encode("mac-roman", errors="replace")
        )
    except Exception:
        rec.string = s.encode("utf-8", errors="replace")


def rename_family(font: TTFont, variant_tag: str) -> None:
    """Insert variant_tag into the family portion of every name record.

    Display names use a space separator ("OpenDyslexic T Bold"); the
    PostScript name (NameID 6) uses the no-space form required by the
    PostScript spec ("OpenDyslexicT-Bold").
    """
    for rec in font["name"].names:
        s = rec.toUnicode()
        if "OpenDyslexic" not in s:
            continue
        sep = "" if rec.nameID == 6 else " "
        replacement = f"OpenDyslexic{sep}{variant_tag}"
        # Avoid double-prefixing if already done.
        after = s.split("OpenDyslexic", 1)[1]
        if after.lstrip("-").lstrip().startswith(variant_tag):
            continue
        _set_name(rec, s.replace("OpenDyslexic", replacement, 1))


def apply_italic_flags(font: TTFont, from_style: str, to_style: str) -> None:
    """Mark the font as italic in name/head/OS2/post tables.

    Display name records replace e.g. "Regular" → "Italic" or "Bold" →
    "Bold Italic". The PostScript name (NameID 6) uses the compact form
    ("OpenDyslexicT-BoldItalic"). head.macStyle and OS/2.fsSelection get
    their italic bits set, and post.italicAngle records the slant.
    """
    to_ps = to_style.replace(" ", "")
    for rec in font["name"].names:
        if rec.nameID not in STYLE_NAMEIDS:
            continue
        s = rec.toUnicode()
        if rec.nameID == 6:
            s2 = s.replace(f"-{from_style}", f"-{to_ps}")
        else:
            s2 = s.replace(from_style, to_style)
        if s2 != s:
            _set_name(rec, s2)

    font["head"].macStyle |= 0x02
    os2 = font["OS/2"]
    os2.fsSelection = (os2.fsSelection & ~0x40) | 0x01   # set italic, clear regular
    font["post"].italicAngle = float(-SLANT_DEG)


def build(src: str, out: str, variant: str, style: str,
          adv_delta: int, space_adv: int, italic: bool) -> None:
    font = TTFont(src)
    skip = excluded_glyphs(font)
    shift = -abs(adv_delta) // 2
    slant = math.tan(math.radians(SLANT_DEG)) if italic else 0.0
    retarget_metrics(font, adv_delta, space_adv, shift, skip)
    shift_cff_outlines(font, shift, slant, skip)
    strip_kerning(font)
    disable_ligatures(font)
    if italic:
        pad_quotes(font, slant)
    pad_punctuation(font)
    rename_family(font, variant)
    if italic:
        from_style, to_style = STYLE_REMAP[style]
        apply_italic_flags(font, from_style, to_style)
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

    needed = sorted({src for _, src, _ in STYLES})
    missing = [n for n in needed if not os.path.isfile(os.path.join(args.src, n))]
    if missing:
        raise SystemExit(
            f"Missing upstream source OTFs in {args.src}:\n  "
            + "\n  ".join(missing)
            + "\n\nDownload OpenDyslexic v0.99 from https://forge.hackers.town/antijingoist/opendyslexic"
              " and place the Regular and Bold OTFs in that directory."
        )

    for variant, params in VARIANTS.items():
        for style, src_name, italic in STYLES:
            src = os.path.join(args.src, src_name)
            out = os.path.join(OUT_ROOT, variant, f"{variant}-{style}.otf")
            build(src, out, variant, style,
                  params["adv_delta"], params["space"], italic)


if __name__ == "__main__":
    main()
