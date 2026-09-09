---
name: mithila-heritage-ui
description: Minimalist UI design system for the Saurath Sabha Gachhi website and other Mithila/Bihar heritage-themed projects. Defines a restrained four-color palette (sindoor maroon, turmeric gold, mango-leaf green, ink brown) plus background, border, typography, spacing, and component rules built around minimalism -- one accent per component, flat surfaces, generous whitespace, no gradients or shadows. Use this skill whenever designing, styling, mocking up, or writing CSS/HTML for any page, component, or style guide for this project, even if the user just says "make a button" or "style this page" without repeating the color names or the word minimalist.
---

# Mithila Heritage UI

A minimalist design system built on four colors drawn from Mithila's Madhubani
art pigments, the mango orchard (*gachhi*) setting, and the panji manuscript
tradition. The cultural reference lives in the color choices only -- the
execution stays restrained. Color is functional, not decorative; space does
most of the work.

## Color palette

| Role | Name | Hex | Usage |
|---|---|---|---|
| Primary | Sindoor maroon | `#7A1F2E` | Headings (h1/h2 only), primary buttons, key borders. Sparingly -- never a large fill. |
| Secondary | Turmeric gold | `#DD9A34` | Secondary buttons, hover/active states, small highlights. |
| Accent | Mango-leaf green | `#5B7A3A` | Links, icons, success/confirmation states. The lightest-touch color -- use least. |
| Text | Ink brown | `#3B2A1E` | Default body text color, in place of pure black. |
| Background | Warm white | `#FDFBF8` | Page and card background. Not stark `#FFFFFF` -- a touch of warmth, still reads as white. |
| Neutral | Soft grey-brown | `#E7E1D8` | Hairline borders, dividers, disabled states. |

```css
:root {
  --color-primary: #7A1F2E;   /* sindoor maroon */
  --color-secondary: #DD9A34; /* turmeric gold */
  --color-accent: #5B7A3A;    /* mango-leaf green */
  --color-text: #3B2A1E;      /* ink brown */
  --color-bg: #FDFBF8;        /* warm white */
  --color-border: #E7E1D8;    /* soft grey-brown */
}
```

## Minimalism rules (non-negotiable)

1. **One accent color per component.** Never combine maroon + gold + green on
   the same button, card, or section. Pick the single role that fits; let
   everything else recede to background, text, or border.
2. **Color is functional, not decorative.** Every colored element signals
   something specific (primary action, link, confirmation). It never appears
   just for visual variety.
3. **Generous whitespace over density.** Prefer more padding/margin and fewer
   simultaneous elements over cramming content in. When unsure, remove an
   element rather than shrink it.
4. **Flat surfaces.** No gradients, drop shadows, glows, or textures. If a
   card needs separation from the page, use a 1px `--color-border` line, not
   a shadow.
5. **Restrained typography.** One typeface family, at most two weights
   (regular + medium/semibold). No more than three font sizes visible on a
   single screen (heading / body / caption).
6. **Sparse ornamentation.** No decorative borders, no icon clutter. A single
   thin rule or a mango-leaf-green accent line is enough to signal cultural
   context -- resist repeating motifs everywhere.
7. **Check contrast, don't assume it.** Turmeric gold on white fails
   small-text contrast -- use it only on large elements (buttons, icons)
   with ink-brown or white text on top, never as small body text on a light
   background.

## Component defaults

- **Primary button:** `background: var(--color-primary); color: #FDFBF8; border: none; border-radius: 4px; padding: 0.75rem 1.5rem;` -- no shadow, no gradient.
- **Secondary button:** `background: transparent; color: var(--color-primary); border: 1px solid var(--color-primary); border-radius: 4px;`
- **Links:** `color: var(--color-accent); text-decoration: underline;` -- keep the same color on hover; the underline is enough feedback.
- **Cards:** `background: var(--color-bg); border: 1px solid var(--color-border); border-radius: 8px; padding: 1.5rem;` -- no shadow.
- **Headings:** `color: var(--color-primary)` for h1/h2 only. h3 and smaller use `var(--color-text)` -- maroon stays a headline color, not a body-heading color.

## When not to use a color

- Never fill a full section or hero background with sindoor maroon -- it is
  a heavy, saturated color. Reserve full-bleed fills for `--color-bg` and use
  maroon for text/accents on top of it.
- Never use turmeric gold as a background behind body text -- contrast fails.
- Don't add a fifth "decorative" color for variety. If a new use case needs
  color, map it onto one of the four existing roles first.

## Quick self-check before shipping a screen

- Can every colored element on the screen be named to one of the four roles?
- Is at least ~70% of the visible surface neutral (background/border/text),
  with color reserved for the portion that should draw the eye?
- Would removing one element make the layout better? If yes, remove it.
