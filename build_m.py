#!/usr/bin/env python3
"""Build the experimental OpenDyslexic M and MT variants.

M is a clean four-style family that combines upstream v0.99 glyph outlines
with the kerning tables from the older v0.92 build:

  - Regular:    v0.99 outlines + v0.92 Regular GPOS kerning (3760 pairs)
  - Bold:       v0.99 outlines + v0.92 Bold GPOS kerning   (~5504 pairs)
  - Italic:     v0.99 Italic as-is (already kerned, 4020 pairs)
  - BoldItalic: v0.99 BoldItalic as-is (already kerned, 2096 pairs)

MT applies the same global tightening to each M cut:

  - Non-uppercase glyphs: advance -60 units, outlines shifted left by 30
    (symmetric tightening). Uppercase glyphs are spared so kerned uppercase
    pairs (AVATAR, TITAN) don't over-collapse.
  - Space glyph: advance 847 -> 620.

On both variants the `liga`/`dlig`/`rlig` GSUB features are disabled so typed
`fi`/`fl` sequences render as separate glyphs. The `name` table is rewritten
to "OpenDyslexic M" / "OpenDyslexic MT".

Usage:
    python3 build_m.py [--v99 DIR] [--v92 DIR]

Requires fontTools. By default:
    --v99 ./src/0.99/     upstream v0.99 OTFs
    --v92 ./src/0.92-nv/  older v0.92 TTFs (source of Regular + Bold kerning)

Outputs go to ./public/fonts/M/ and ./public/fonts/MT/.
"""

from __future__ import annotations
import argparse
import os
import unicodedata
from fontTools.ttLib import TTFont

REPO_ROOT = os.path.dirname(os.path.abspath(__file__))
DEFAULT_V99_DIR = os.path.join(REPO_ROOT, "src", "0.99")
DEFAULT_V92_DIR = os.path.join(REPO_ROOT, "src", "0.92-nv")
OUT_ROOT = os.path.join(REPO_ROOT, "public", "fonts")

# (style_name, v99_filename, v92_kerning_source or None)
STYLES = [
    ("Regular",    "OpenDyslexic-Regular.otf",    "NV_OpenDyslexic-Regular.ttf"),
    ("Bold",       "OpenDyslexic-Bold.otf",       "NV_OpenDyslexic-Bold.ttf"),
    ("Italic",     "OpenDyslexic-Italic.otf",     None),
    ("BoldItalic", "OpenDyslexic-BoldItalic.otf", None),
]

NEOT_ADV_DELTA = -60
NEOT_SHIFT = -30
NEOT_SPACE = 620


def transplant_kerning(target: TTFont, source_path: str) -> None:
    """Copy GPOS/kern from the font at source_path into target. The source is
    first subsetted down to the glyphs common to both fonts so rules referencing
    glyphs absent from target are dropped cleanly."""
    from fontTools.subset import Subsetter, Options
    source = TTFont(source_path)
    common = sorted(set(source.getGlyphOrder()) & set(target.getGlyphOrder()))
    opts = Options()
    opts.layout_features = ["kern"]
    opts.notdef_outline = True
    opts.glyph_names = True
    subsetter = Subsetter(options=opts)
    subsetter.populate(glyphs=common)
    subsetter.subset(source)
    if "GPOS" in source:
        target["GPOS"] = source["GPOS"]
    if "kern" in source:
        target["kern"] = source["kern"]


def disable_ligatures(font: TTFont) -> None:
    if "GSUB" not in font:
        return
    for fr in font["GSUB"].table.FeatureList.FeatureRecord:
        if fr.FeatureTag in ("liga", "dlig", "rlig"):
            fr.Feature.LookupListIndex = []
            fr.Feature.LookupCount = 0


def rename_family(font: TTFont, tag: str) -> None:
    for rec in font["name"].names:
        s = rec.toUnicode()
        if "OpenDyslexic" not in s:
            continue
        after = s.split("OpenDyslexic", 1)[1]
        if after.lstrip().startswith(tag):
            continue
        s2 = s.replace("OpenDyslexic", f"OpenDyslexic {tag}", 1)
        try:
            rec.string = (
                s2.encode("utf-16-be") if rec.platformID == 3
                else s2.encode("mac-roman", errors="replace")
            )
        except Exception:
            rec.string = s2.encode("utf-8", errors="replace")


def shift_cff_glyph(charStrings, gname: str, dx: int) -> None:
    cs = charStrings[gname]
    cs.decompile()
    prog = cs.program
    i, args = 0, []
    while i < len(prog) and not isinstance(prog[i], str):
        args.append(prog[i]); i += 1
    if i >= len(prog):
        return
    op = prog[i]
    if op == "rmoveto" and len(args) >= 2:
        prog[i - 2] = args[-2] + dx
    elif op == "hmoveto" and len(args) >= 1:
        prog[i - 1] = args[-1] + dx
    elif op == "vmoveto":
        prog[: i + 1] = [dx, args[-1], "rmoveto"]
    cs.program = prog


def is_uppercase_glyph(gname: str, cmap_rev: dict[str, int]) -> bool:
    cp = cmap_rev.get(gname)
    if cp is None:
        return False
    try:
        return unicodedata.category(chr(cp)) == "Lu"
    except ValueError:
        return False


def apply_neot(font: TTFont) -> None:
    """Tighten non-uppercase metrics; narrow space; leave uppercase alone."""
    cmap_rev = {g: cp for cp, g in font.getBestCmap().items()}
    charStrings = font["CFF "].cff.topDictIndex[0].CharStrings
    hmtx = font["hmtx"]
    new_metrics = {}
    for gname, (aw, lsb) in hmtx.metrics.items():
        if gname == "space":
            new_metrics[gname] = (NEOT_SPACE, lsb)
            continue
        if is_uppercase_glyph(gname, cmap_rev):
            new_metrics[gname] = (aw, lsb)
            continue
        shift_cff_glyph(charStrings, gname, NEOT_SHIFT)
        new_metrics[gname] = (max(0, aw + NEOT_ADV_DELTA), lsb + NEOT_SHIFT)
    hmtx.metrics = new_metrics


def build_neo(v99_path: str, v92_path: str | None, out_path: str, tag: str) -> None:
    font = TTFont(v99_path)
    if v92_path:
        transplant_kerning(font, v92_path)
    disable_ligatures(font)
    rename_family(font, tag)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    font.save(out_path)
    print(f"wrote {out_path}")


def build_neot(neo_path: str, out_path: str) -> None:
    font = TTFont(neo_path)
    apply_neot(font)
    rename_family(font, "MT")  # rename_family is idempotent against re-prefixing
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    font.save(out_path)
    print(f"wrote {out_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--v99", default=DEFAULT_V99_DIR)
    parser.add_argument("--v92", default=DEFAULT_V92_DIR)
    args = parser.parse_args()

    for style, v99_name, v92_name in STYLES:
        v99 = os.path.join(args.v99, v99_name)
        v92 = os.path.join(args.v92, v92_name) if v92_name else None
        if not os.path.isfile(v99):
            raise SystemExit(f"Missing upstream source: {v99}")
        if v92 and not os.path.isfile(v92):
            raise SystemExit(f"Missing v0.92 kerning source: {v92}")
        m_out = os.path.join(OUT_ROOT, "M", f"M-{style}.otf")
        mt_out = os.path.join(OUT_ROOT, "MT", f"MT-{style}.otf")
        build_neo(v99, v92, m_out, "M")
        build_neot(m_out, mt_out)


if __name__ == "__main__":
    main()
