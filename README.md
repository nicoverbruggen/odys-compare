# odys-compare

An experimental comparison harness for evaluating OpenDyslexic variants in an e-reader-like layout. Built to decide which version of OpenDyslexic to include in [`ebook-fonts`](https://github.com/nicoverbruggen/ebook-fonts).

## Background

The upstream OpenDyslexic project (abbiecod.es) shipped **v0.99** with its hand-tuned letter-pair kerning stripped from the **Regular** and **Bold** styles. The change landed in commit [`7d7f63c`](https://forge.hackers.town/antijingoist/opendyslexic/commit/7d7f63c) ("adjustments in positions") on 2025-02-09. The commit also reworked glyph widths and sidebearings, so the kerning removal is consistent with the metrics change rather than a simple regression — but the commit message doesn't mention it.

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
| 5 | **OpenDyslexic Neo** | Clean four-style rebuild: v0.99 Regular & Bold with kerning transplanted from v0.92; Italic & Bold Italic taken from v0.99 as-is. |
| 6 | **OpenDyslexic Neo T** | Neo with tightened metrics: −60u global advance (uppercase spared so kerned uppercase pairs don't over-collapse), space narrowed 847 → 620. |

All six variants ship Regular, Bold, Italic, and Bold Italic cuts.

Other controls:

- **size** / **line-height** sliders
- **justify** checkbox (off reveals true per-glyph spacing without the browser's word-stretching)
- **body** dropdown — renders the whole body text in Regular/Italic/Bold/Bold Italic
- **space** key to cycle variants

## Running it

```sh
cd od-compare/public
python3 -m http.server 8765
```

Then open http://localhost:8765/. For deployment, `nixpacks.toml` is configured to serve `public/` with PHP's built-in server.

## How the experimental variants were built

### Neo and Neo T

See `build_neo.py` in the repo root. It expects upstream v0.99 OTFs in `src/0.99/` and the older v0.92 TTFs in `src/0.92-nv/` (used as the kerning source for Regular and Bold). Running `python3 build_neo.py` produces all eight cuts into `public/fonts/Neo/` and `public/fonts/NeoT/`.

Per cut:

- **Regular / Bold**: v0.99 glyph outlines; GPOS/kern transplanted from the v0.92 equivalent (subsetted to the glyphs that exist in v0.99 so no dangling rules).
- **Italic / Bold Italic**: v0.99 as-is (already kerned upstream, 4020 and 2096 pairs respectively).

For Neo T, each cut is additionally tightened:

- Each non-uppercase glyph: advance −60 units (on 1000 UPM), outlines shifted left by 30 units (symmetric tightening).
- Uppercase glyphs (Unicode category `Lu`): metrics left untouched. Kerned uppercase pairs (e.g. `qT=−490`) would over-collapse if combined with global tightening.
- Space glyph: advance 847 → 620.

Ligatures (`liga`/`dlig`/`rlig`) are disabled on every Neo and Neo T cut, matching the T/UT treatment.

### T and UT

See `build_tight.py` in the repo root for the full reproducible pipeline. Drop the four upstream v0.99 `OpenDyslexic-*.otf` files into `src/0.99/` and run `python3 build_tight.py` — it writes all eight cuts into `public/fonts/T/` and `public/fonts/UT/`. Applied to upstream v0.99 (all four cuts), kernless:

- T: every glyph (including uppercase) has advance shortened by 90 units, outlines shifted −45. Space 847 → 560.
- UT: same idea, −150 units and space 847 → 480. Pushes the kernless tightening about as far as it can go before pairs start to collide.

Uppercase tightening is safe in both T and UT because there's no kerning to stack with. Both variants preserve upstream's kernless design intent and only change metrics.

For consistency across the family, kerning is also stripped from the Italic and Bold Italic cuts (upstream v0.99 ships them kerned, but T/UT are explicitly a kernless design). The `fi` and `fl` ligature substitutions are also disabled in all four cuts — the `liga` GSUB feature is cleared so typed `fi`/`fl` sequences render as separate glyphs.

In the Italic and Bold Italic cuts, the quote glyphs (`"` `'` and their curly/low variants) are skewed −12° and padded by 120 units of advance so they lean against the italic body slant and don't crowd adjacent letters.

## Findings / recommendation

For `ebook-fonts` (justified e-reader columns):

- **A** (upstream) produces visible rivers of whitespace in justified text — browsers stretch word-spacing to compensate for the missing letter-pair tightening.
- **B** (older v0.92) reads cleanly but uses older glyph shapes.
- **Neo** matches B's typographic color with the newer v0.99 glyph refinements. Effectively a clean upgrade over B.
- **Neo T**, **T**, and **UT** are the three "tighter spacing" answers, differing in philosophy: Neo T keeps and respects the restored kerning; T and UT keep upstream's kernless intent and just shorten metrics, with UT being the more aggressive cut.

## Credits & license

OpenDyslexic is designed by **Abbie Gonzalez** ([abbiecod.es](https://abbiecod.es/), [upstream repo](https://forge.hackers.town/antijingoist/opendyslexic)). The A and B variants here are unmodified builds of her work (v0.99 and v0.92 respectively); Neo, Neo T, T, and UT are experimental derivatives produced by the build scripts in this repository.

All fonts — original and derivative — are distributed under the **SIL Open Font License, Version 1.1**. See `LICENSE` for the full text.

## Files

```
od-compare/
├── README.md            (this file)
├── LICENSE              (SIL OFL 1.1)
├── build_tight.py       (reproducible T/UT build pipeline)
├── build_neo.py         (reproducible Neo/Neo T build pipeline)
├── nixpacks.toml        (deployment config — serves public/)
├── src/
│   ├── 0.99/            (drop upstream v0.99 OpenDyslexic-*.otf here)
│   └── 0.92-nv/         (older v0.92 TTFs, kerning source for Neo R/B)
└── public/              (served webroot)
    ├── index.html       (the comparison page)
    ├── index.js         (page logic)
    └── fonts/
        ├── A/*.ttf      (variant 1: upstream v0.99)
        ├── B/*.ttf      (variant 2: older v0.92)
        ├── T/*.otf      (variant 3: kernless tightened)
        ├── UT/*.otf     (variant 4: kernless ultra-tight)
        ├── Neo/*.otf    (variant 5: Neo family)
        └── NeoT/*.otf   (variant 6: Neo T family)
```
