# od-compare

A/B/C/... comparison harness for evaluating OpenDyslexic variants in an e-reader-like layout. Built to answer: should `ebook-fonts` stay on the current kerned v0.92 build, or upgrade to upstream's v0.99?

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

Serves a sepia, ~720px-wide e-reader mockup with a chapter of sample text and a kerning-pair reference grid. Six font variants can be toggled live via buttons or keys `1`–`6`:

| # | Variant | What it is |
| - | ------- | ---------- |
| 1 | **OpenDyslexic A** | Upstream v0.99 as shipped (kernless Regular). |
| 2 | **OpenDyslexic B** | Legacy v0.92, what `ebook-fonts` currently ships. Full 3760-pair kerning. |
| 3 | **OpenDyslexic C** | Experimental: v0.99 glyphs + B's 3760 kerning pairs grafted back in. Isolates glyphs-vs-kerning. |
| 4 | **OpenDyslexic Neo** | Clean four-style rebuild: v0.99 Regular & Bold with restored kerning; Italic & Bold Italic reused from kobo-font-fix. |
| 5 | **OpenDyslexic Neo T** | Neo with tightened metrics: −60u global advance (uppercase spared so kerned uppercase pairs don't over-collapse), space narrowed 847 → 620. |
| 6 | **OpenDyslexic T** | Upstream v0.99 kernless glyphs, tightened uniformly: −90u global advance (including uppercase, since no kerning to double-penalize), space 847 → 560. |

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

## The Neo family

Built fonts live at `/home/nico/Desktop/od-neo/`:

```
NV_OpenDyslexic-Neo-Regular.ttf      (3760 kern pairs)
NV_OpenDyslexic-Neo-Bold.ttf         (5504 kern pairs)
NV_OpenDyslexic-Neo-Italic.ttf       (4020 kern pairs, unchanged)
NV_OpenDyslexic-Neo-BoldItalic.ttf   (2096 kern pairs, unchanged)

NV_OpenDyslexic-Neo-T-*.ttf          (same four, tightened)
```

### How Neo Regular was built

1. Start from upstream `/home/nico/Desktop/od/OpenDyslexic-Regular.otf` (v0.99 CFF).
2. Extract kern pairs from `NV_OpenDyslexic-Regular.ttf` in the `ebook-fonts` repo (v0.92, 3760 pairs, glyph-name based).
3. Strip the single-pair v0.99 GPOS table; rebuild `kern` feature from the v0.92 pairs. All 3760 glyph-name references resolved in A — nothing skipped.
4. Convert OTF → TTF via `otf2ttf` (fontTools).
5. Rewrite `name` table: family `NV OpenDyslexic Neo`, PostScript `NVOpenDyslexicNeo-Regular`.

### How Neo Bold was built

Same recipe, with kerning sourced from `/home/nico/Desktop/classic/NV_OpenDyslexic-Bold.ttf` (5504/5505 pairs survived).

### Neo T (tight variant)

Applied to each Neo TTF:

- Each non-uppercase glyph: advance −60 units (on 1000 UPM), outlines shifted left by 30 units. Symmetric tightening on both sidebearings.
- Uppercase glyphs (Unicode category `Lu`, 495 of them): metrics left untouched. Kerned uppercase pairs (e.g. `qT=−490`) would over-collapse if combined with global tightening.
- Space glyph: advance 847 → 620.

### OpenDyslexic T

Variant 6 only — separate deliverable. Applied to v0.99 Regular (kernless):

- All glyphs including uppercase: advance −90 units, outlines shifted −45. Uppercase tightening is safe here because there's no kerning to stack with.
- Space: advance 847 → 560.
- No kerning added; preserves upstream's kernless design intent.

## Findings / recommendation

For `ebook-fonts` (justified e-reader columns):

- **A** (upstream) produces visible rivers of whitespace in justified text — browsers stretch word-spacing to compensate for the missing letter-pair tightening.
- **B** (current `ebook-fonts` build) reads cleanly but uses older glyph shapes.
- **C** / **Neo** match B's typographic color with the newer v0.99 glyph refinements. Effectively a clean upgrade over B.
- **Neo T** and **T** are the two "tighter spacing" answers, differing in philosophy: Neo T keeps and respects the restored kerning; T keeps upstream's kernless intent and just shortens metrics.

## Files

```
od-compare/
├── README.md            (this file)
├── index.html           (the comparison page)
└── fonts/
    ├── A-*.ttf          (variant 1: upstream v0.99)
    ├── B-*.ttf          (variant 2: ebook-fonts v0.92)
    ├── C-Regular.ttf    (variant 3: A + B kerning)
    ├── Neo-*.ttf        (variant 4: Neo family)
    ├── NeoT-*.ttf       (variant 5: Neo T family)
    └── T-Regular.ttf    (variant 6: kernless tightened)
```
