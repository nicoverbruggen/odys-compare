# od-compare

An experimental comparison harness for evaluating OpenDyslexic variants in an e-reader-like layout. Built to decide which version of OpenDyslexic to include in [`ebook-fonts`](https://github.com/nicoverbruggen/ebook-fonts).

## Background

The upstream OpenDyslexic project (abbiecod.es) shipped **v0.99** with its hand-tuned letter-pair kerning stripped from the **Regular** and **Bold** styles. The change landed in commit [`7d7f63c`](https://github.com/antijingoist/opendyslexic) ("adjustments in positions") on 2025-02-09. The commit also reworked glyph widths and sidebearings, so the kerning removal is consistent with the metrics change rather than a simple regression — but the commit message doesn't mention it.

Concretely:

| Style       | v0.92 (old)      | v0.99 (current upstream) |
| ----------- | ---------------- | ------------------------ |
| Regular     | 3760 kern pairs  | **1 pair** (punctuation+space only) |
| Bold        | ~5500 kern pairs | **1 pair** |
| Italic      | 1409 pairs       | 4020 pairs (expanded)    |
| Bold Italic | 2096 pairs       | 2096 pairs               |

So the kerning wasn't removed as a blanket decision — Italic and Bold Italic kept (and gained) kerning. Only the upright styles were stripped.

## What this page does

Serves a sepia, ~720px-wide e-reader mockup with a chapter of sample text and a kerning-pair reference grid. Six font variants can be toggled live via buttons or keys `1`–`6`, grouped into **Classic** (keys 1–4) and **Neo** (keys 5–6):

| # | Variant | What it is |
| - | ------- | ---------- |
| 1 | **OpenDyslexic A** | Upstream v0.99 as shipped (kernless Regular). |
| 2 | **OpenDyslexic B** | Older v0.92, included for reference. Full 3760-pair kerning. |
| 3 | **OpenDyslexic T** | Upstream v0.99 kernless glyphs, tightened uniformly: −90u global advance, space 847 → 560. |
| 4 | **OpenDyslexic UT** | Same recipe as T, pushed further: −150u advance, space 847 → 480. |
| 5 | **OpenDyslexic Neo** | Clean four-style rebuild: v0.99 Regular & Bold with restored kerning; Italic & Bold Italic reused from kobo-font-fix. |
| 6 | **OpenDyslexic Neo T** | Neo with tightened metrics: −60u global advance (uppercase spared so kerned uppercase pairs don't over-collapse), space narrowed 847 → 620. |

All six variants ship Regular, Bold, Italic, and Bold Italic cuts.

Other controls:

- **size** / **line-height** sliders
- **justify** checkbox (off reveals true per-glyph spacing without the browser's word-stretching)
- **body** dropdown — renders the whole body text in Regular/Italic/Bold/Bold Italic
- **space** key to cycle variants

## Running it

```sh
cd od-compare
python3 -m http.server 8765
```

Then open http://localhost:8765/.

## How the experimental variants were built

### Neo Regular

1. Start from upstream `OpenDyslexic-Regular.otf` (v0.99 CFF).
2. Extract kern pairs from the older v0.92 Regular (3760 pairs, glyph-name based).
3. Strip the single-pair v0.99 GPOS table; rebuild `kern` feature from the v0.92 pairs. All 3760 glyph-name references resolved — nothing skipped.
4. Convert OTF → TTF via `otf2ttf` (fontTools).

### Neo Bold

Same recipe, with kerning sourced from the older Bold (5504/5505 pairs survived).

### Neo Italic / Bold Italic

Reused from the already-kerned kobo-font-fix builds (4020 and 2096 pairs respectively), which match v0.99's Italic/Bold-Italic kerning.

### Neo T

Applied to each Neo cut:

- Each non-uppercase glyph: advance −60 units (on 1000 UPM), outlines shifted left by 30 units (symmetric tightening).
- Uppercase glyphs (Unicode category `Lu`): metrics left untouched. Kerned uppercase pairs (e.g. `qT=−490`) would over-collapse if combined with global tightening.
- Space glyph: advance 847 → 620.

### T and UT

Applied to upstream v0.99 (all four cuts), kernless:

- T: every glyph (including uppercase) has advance shortened by 90 units, outlines shifted −45. Space 847 → 560.
- UT: same idea, −150 units and space 847 → 480. Pushes the kernless tightening about as far as it can go before pairs start to collide.

Uppercase tightening is safe in both T and UT because there's no kerning to stack with. Both variants preserve upstream's kernless design intent and only change metrics.

## Findings / recommendation

For `ebook-fonts` (justified e-reader columns):

- **A** (upstream) produces visible rivers of whitespace in justified text — browsers stretch word-spacing to compensate for the missing letter-pair tightening.
- **B** (older v0.92) reads cleanly but uses older glyph shapes.
- **Neo** matches B's typographic color with the newer v0.99 glyph refinements. Effectively a clean upgrade over B.
- **Neo T**, **T**, and **UT** are the three "tighter spacing" answers, differing in philosophy: Neo T keeps and respects the restored kerning; T and UT keep upstream's kernless intent and just shorten metrics, with UT being the more aggressive cut.

## Files

```
od-compare/
├── README.md            (this file)
├── index.html           (the comparison page)
└── fonts/
    ├── A-*.ttf          (variant 1: upstream v0.99)
    ├── B-*.ttf          (variant 2: older v0.92)
    ├── T-*.otf          (variant 3: kernless tightened)
    ├── UT-*.otf         (variant 4: kernless ultra-tight)
    ├── Neo-*.ttf        (variant 5: Neo family)
    └── NeoT-*.ttf       (variant 6: Neo T family)
```
