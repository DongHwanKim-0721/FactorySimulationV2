# FactorySimulation Design Tokens

Status: ACTIVE
Updated: 2026-07-06

## Atmosphere

FactorySimulation is an operations console for planners. The UI should feel calm, scan-friendly, and work-focused: dense enough for repeated use, restrained in decoration, and clear about deterministic outputs. The signature is slate workspace chrome with light report surfaces and one blue action accent.

## Color

Existing Tkinter prototype tokens, extracted from `app.py`:

- `--color-app-bg`: `#e8edf3`, main application background.
- `--color-toolbar-bg`: `#1f2937`, top toolbar background.
- `--color-toolbar-button-bg`: `#334155`, toolbar button background.
- `--color-toolbar-button-hover`: `#475569`, toolbar button hover.
- `--color-toolbar-button-pressed`: `#0f172a`, toolbar button pressed.
- `--color-toolbar-text`: `#f8fafc`, toolbar title and button text.
- `--color-panel-bg`: `#f8fafc`, panel and form surface.
- `--color-panel-border`: `#cbd5e1`, panel border.
- `--color-panel-title`: `#0f172a`, panel title text.
- `--color-body-text`: `#334155`, body and form text.
- `--color-muted-text`: `#475569`, secondary text.
- `--color-status-bg`: `#dbe3ec`, status bar background.
- `--color-focus`: `#93c5fd`, focus ring.
- `--color-tab-bg`: `#e2e8f0`, inactive tab background.
- `--color-tab-hover`: `#f1f5f9`, tab hover.
- `--color-tab-selected`: `#ffffff`, selected tab background.

Rules:

- Use the blue/slate accent family already present in the app.
- Do not add purple gradients, glow effects, beige/brass palettes, or pure black text.
- For new Tkinter planning UI, prefer existing ttk platform controls and existing style names before adding new colors.

## Typography

- `--font-ui`: Arial, system fallback, existing app default.
- `--type-body`: 10 px, weight 400, line-height native Tkinter.
- `--type-toolbar-title`: 16 px, weight 700, line-height native Tkinter.
- `--type-panel-title`: 11 px, weight 700, line-height native Tkinter.
- `--type-label`: 10 px, weight 400, line-height native Tkinter.

Rules:

- Keep form labels concise.
- Use title weight only for window and panel titles.
- Do not introduce display typography in operational screens.

## Spacing

Base unit: 4 px.

- `--space-1`: 4 px.
- `--space-2`: 8 px.
- `--space-3`: 12 px.
- `--space-4`: 16 px.
- `--space-5`: 20 px.
- `--space-6`: 24 px.

Existing component spacing:

- `--toolbar-padding`: 12 px horizontal, 8 px vertical.
- `--toolbar-button-padding`: 10 px horizontal, 6 px vertical.
- `--panel-padding`: 12 px.
- `--dialog-padding-x`: 22 px.
- `--dialog-padding-y`: 14 px.
- `--status-padding`: 10 px horizontal, 4 px vertical.

Rules:

- Use 4 px multiples for padding, gaps, and grid spacing.
- Use compact vertical rhythm for data-entry forms.

## Components

- Toolbar: `--color-toolbar-bg`, `--color-toolbar-text`, `--toolbar-padding`.
- Toolbar button: `--color-toolbar-button-bg`, hover `--color-toolbar-button-hover`, pressed `--color-toolbar-button-pressed`, text `--color-toolbar-text`, focus `--color-focus`.
- Panel frame: `--color-panel-bg`, border `--color-panel-border`, padding `--panel-padding`.
- Form label: `--type-label`, text `--color-body-text`.
- Entry fields: native ttk entry chrome, width stable per field type.
- Primary action: native ttk button placed first in the action row.
- Status summary: read-only text, compact lines, no decorative badges.

Rules:

- Do not nest cards inside cards.
- Use rows, separators, labels, and read-only text areas for dense planning data.
- Empty state text should say exactly what is missing or required.

## Motion

No animation for the planning launcher. The route/canvas prototype keeps its existing animation behavior. Reduced motion requires no special handling for the launcher because it has no motion.

## Depth

Depth strategy is borders and tonal surfaces. Do not add drop shadows, glow, glass effects, or floating decorative panels.

## Anti-Slop Lock

- Zero em-dashes in visible strings.
- No purple/blue gradient backgrounds.
- No Inter/Roboto switch unless the existing app changes first.
- No fake screenshots or decorative logo walls.
- No AI cliches in user-visible copy.
