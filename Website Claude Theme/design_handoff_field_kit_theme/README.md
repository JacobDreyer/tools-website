# Handoff: Field Kit Theme (option 4a — "Registration Marks")

## Overview
A blueprint/schematic-styled theme for a personal scripts & tools launcher: search bar, category filter chips, and a card grid listing each tool. Option 4a is a paper-blueprint look with corner registration marks, a technical title block, and a footer bar — read as a drafting sheet.

## About the Design Files
The file in this bundle (`4a-field-kit-theme.html`) is a **design reference** extracted from an HTML prototype — it shows intended look, structure, and copy, not production code to paste in as-is. Recreate this design in your project's existing environment (React, Vue, plain JS, etc.) using its established component patterns, state management, and build tooling. If no frontend framework exists yet, pick whatever's most appropriate for the project.

## Fidelity
**High-fidelity.** Colors, typography, spacing, and layout below are final — implement pixel-for-pixel using your codebase's styling approach (CSS modules, Tailwind, styled-components, etc.), not necessarily inline styles as shown.

## Screen: Tool Launcher Grid
**Purpose:** Personal dashboard listing scripts/tools, filterable by category and free-text search.

**Layout:**
- Root container: fixed max width in the mock is 1180px but should be fluid/responsive in production — treat as the content column.
- Background: `oklch(97% 0.008 90)` (near-white warm paper), 1px border `oklch(80% 0.03 245)`.
- A repeating grid-line background pattern across the whole container: two `repeating-linear-gradient`s (horizontal + vertical) at `oklch(80% 0.05 245 / 0.15)`, 1px lines every 40px — this is the "blueprint graph paper" texture, decorative, `pointer-events:none`, sits behind all content.
- Four L-shaped corner registration marks, 16×16px, 2px strokes in `oklch(45% 0.08 245)`, inset 14px from each corner (two sides of the L touching the container edges).
- Header band: padding `34px 44px 20px`, bottom border 1px `oklch(80% 0.05 245 / 0.5)`. Flex row, space-between, items aligned to bottom.
  - Title "Field Kit": 40px Courier Prime, bold (700), color `oklch(30% 0.1 245)`.
  - Subtitle: "DWG NO. FK-04 — PERSONAL TOOLING — SCALE 1:1", 12px Courier Prime, semibold, letter-spacing 0.1em, color `oklch(45% 0.08 245)`.
  - Right-aligned info stamp box: bordered box (1px, `oklch(45% 0.08 245)`), padding `8px 12px`, 11px Courier Prime semibold, color `oklch(35% 0.09 245)`, three stacked lines: "DRAWN BY: ME", "REV: C", "{count} ITEMS".
- Search row: padding `22px 44px 0`. A small "⊕" glyph (12px, colored `oklch(45% 0.08 245)`) then a text input, flex:1, 14px Courier Prime, transparent background, 1px border `oklch(60% 0.06 245 / 0.6)`, padding `11px 14px`, text color `oklch(30% 0.1 245)`. Placeholder: "Search schematic...".
- Category chip row: padding `16px 44px 0`, flex-wrap, gap 8px. Chips are plain text pills, 13px Courier Prime. Active chip: filled `oklch(35% 0.09 245)` background, `oklch(97% 0.008 90)` text. Inactive: transparent, `oklch(40% 0.08 245)` text, 1px border `oklch(45% 0.08 245 / 0.6)`. Categories: All, Backup, Media, Text, Dev, Network, System.
- Card grid: padding `26px 44px 60px`, CSS grid 3 columns, gap 16px.
  - Each card: 1px border `oklch(60% 0.06 245 / 0.6)`, padding 16px, relative position.
  - A small 10×2px tick mark sits at top-left (top:-1px, left:14px) in `oklch(45% 0.08 245)` — a subtle "dimension line" detail.
  - Tool name: 15px Courier Prime bold, uppercase, color `oklch(28% 0.1 245)`.
  - Description: 13px Courier Prime, color `oklch(42% 0.08 245)`, line-height 1.5, margin-top 8px.
  - Footer row inside card: margin-top 14px, 11px Courier Prime, letter-spacing 0.04em, color `oklch(48% 0.08 245)`, top border 1px dotted `oklch(55% 0.06 245)`, padding-top 8px, flex space-between: left = "REF/{category}", right = language tag (e.g. "py", "sh", "js", "go", "rs").
- Footer bar: absolutely positioned at container bottom, full width, top border 2px `oklch(45% 0.08 245)`, padding `10px 44px`, flex space-between, 10px Courier Prime semibold, letter-spacing 0.08em, color `oklch(45% 0.08 245)`. Left: "FIELD KIT — TOOLING INDEX". Right: "SHEET 1 OF 1".

## Interactions & Behavior
- **Search input**: filters the tool list by substring match against tool name and description (case-insensitive), live as you type.
- **Category chips**: single-select. Clicking a chip sets the active category filter; "All" clears it. Active state is visual only (filled vs outlined), no animation needed.
- **Combined filter**: a tool shows if it matches BOTH the active category (or category is "All") and the search substring (or search is empty).
- No card click-through behavior was specified in the mock — cards are visual only; wire up navigation/launch actions per your app's needs (e.g. clicking a card should run/open that tool).
- No responsive breakpoints were designed — the 3-column grid should probably collapse to 2 then 1 column on narrower viewports.

## State Management
- `searchQuery: string`
- `activeCategory: string` (default `"All"`)
- `filteredTools = tools.filter(t => (activeCategory === "All" || t.category === activeCategory) && (searchQuery === "" || matches name/description))`
- Tool list data shape: `{ name: string, desc: string, cat: string, tag: string }`

## Design Tokens

**Colors:**
- Background (paper): `oklch(97% 0.008 90)`
- Container border / grid lines: `oklch(80% 0.03 245)` / `oklch(80% 0.05 245 / 0.15)`
- Primary ink (headings): `oklch(30% 0.1 245)`
- Secondary ink (subtitle, labels): `oklch(45% 0.08 245)`
- Body text: `oklch(42% 0.08 245)`
- Card border: `oklch(60% 0.06 245 / 0.6)`
- Active chip fill: `oklch(35% 0.09 245)`
- Footer bar accent: `oklch(45% 0.08 245)`

**Typography:**
- Font: "Courier Prime" (Google Font, weights 400 + 700). Fallback: monospace.
- Title: 40px / 700
- Subtitle/labels: 12px / 600, letter-spacing 0.1em
- Card title: 15px / 700, uppercase
- Body copy: 13px / 400, line-height 1.5
- Micro labels (footer, tags): 10–11px / 600, letter-spacing 0.04–0.08em

**Spacing:**
- Container padding: 44px horizontal
- Section vertical rhythm: 20–26px between blocks
- Card grid gap: 16px
- Card internal padding: 16px

**Borders:** All 1px solid except container corner marks and footer top border (2px).

**Border radius:** None — sharp corners throughout (drafting-sheet aesthetic).

## Assets
None — no icons or images used. The "⊕" and "◄/►" glyphs are plain Unicode characters, not icon assets.

## Files
- `4a-field-kit-theme.html` — extracted markup + inline styles for this exact screen, taken from the working prototype `Script Launcher Themes.dc.html` (option id `4a`) in the design project. Use as the visual/structural reference only; it's a template fragment (with `{{ }}` placeholders for dynamic data), not runnable code.
