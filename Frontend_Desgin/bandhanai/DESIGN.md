---
name: BandhanAI
colors:
  surface: '#131314'
  surface-dim: '#131314'
  surface-bright: '#3a393a'
  surface-container-lowest: '#0e0e0f'
  surface-container-low: '#1c1b1c'
  surface-container: '#201f20'
  surface-container-high: '#2a2a2b'
  surface-container-highest: '#353436'
  on-surface: '#e5e2e3'
  on-surface-variant: '#d7c3ae'
  inverse-surface: '#e5e2e3'
  inverse-on-surface: '#313031'
  outline: '#9f8e7a'
  outline-variant: '#524534'
  surface-tint: '#ffb955'
  primary: '#ffc880'
  on-primary: '#452b00'
  primary-container: '#f5a623'
  on-primary-container: '#644000'
  inverse-primary: '#835500'
  secondary: '#c8c6c8'
  on-secondary: '#303032'
  secondary-container: '#474649'
  on-secondary-container: '#b7b4b7'
  tertiary: '#9bd9ff'
  on-tertiary: '#00344a'
  tertiary-container: '#3ac2ff'
  on-tertiary-container: '#004d6a'
  error: '#ffb4ab'
  on-error: '#690005'
  error-container: '#93000a'
  on-error-container: '#ffdad6'
  primary-fixed: '#ffddb4'
  primary-fixed-dim: '#ffb955'
  on-primary-fixed: '#291800'
  on-primary-fixed-variant: '#633f00'
  secondary-fixed: '#e5e1e4'
  secondary-fixed-dim: '#c8c6c8'
  on-secondary-fixed: '#1b1b1d'
  on-secondary-fixed-variant: '#474649'
  tertiary-fixed: '#c4e7ff'
  tertiary-fixed-dim: '#7cd0ff'
  on-tertiary-fixed: '#001e2c'
  on-tertiary-fixed-variant: '#004c69'
  background: '#131314'
  on-background: '#e5e2e3'
  surface-variant: '#353436'
typography:
  display-lg:
    fontFamily: Sora
    fontSize: 32px
    fontWeight: '600'
    lineHeight: '1.2'
    letterSpacing: -0.02em
  headline-md:
    fontFamily: Sora
    fontSize: 20px
    fontWeight: '500'
    lineHeight: '1.4'
    letterSpacing: -0.01em
  body-base:
    fontFamily: DM Sans
    fontSize: 14px
    fontWeight: '400'
    lineHeight: '1.6'
  body-sm:
    fontFamily: DM Sans
    fontSize: 13px
    fontWeight: '400'
    lineHeight: '1.5'
  data-mono:
    fontFamily: JetBrains Mono
    fontSize: 12px
    fontWeight: '500'
    lineHeight: '1.4'
    letterSpacing: 0.02em
  label-caps:
    fontFamily: JetBrains Mono
    fontSize: 10px
    fontWeight: '700'
    lineHeight: '1'
    letterSpacing: 0.05em
rounded:
  sm: 0.125rem
  DEFAULT: 0.25rem
  md: 0.375rem
  lg: 0.5rem
  xl: 0.75rem
  full: 9999px
spacing:
  unit: 4px
  container-padding: 24px
  gutter: 16px
  stack-sm: 8px
  stack-md: 16px
  stack-lg: 32px
---

## Brand & Style

The design system is engineered for high-performance AI CRM environments where speed and clarity are paramount. It adopts a **Minimalist-Technical** aesthetic, blending the precision of developer tools like Raycast with the refined polish of modern SaaS interfaces like Linear. 

The brand personality is that of a "Smart Colleague"—expert, dependable, and unobtrusive. It avoids all decorative flourishes, robot imagery, and stock photography in favor of structural integrity and data-driven beauty. The UI is designed for high information density, ensuring that power users can scan vast amounts of multi-tenant data without cognitive overload.

**Key Visual Principles:**
- **Utility First:** Every pixel must serve a functional purpose.
- **Subtle Command:** Use of deep blacks and sharp amber accents to direct attention without fatigue.
- **Modern Professionalism:** A focus on layout, typography, and purposeful motion rather than illustrations or gradients.

## Colors

The palette is strictly dark-mode, optimized for long-duration focus. 

- **Backgrounds:** The foundation uses `#0A0A0B` (Canvas) and `#111113` (Surface/Cards). This provides a deep, ink-like backdrop that makes text pop.
- **Accents:** A sharp **Saffron/Amber (#F5A623)** is used sparingly for primary actions, focus states, and critical AI "insights." 
- **Typography:** Warm off-whites (`#FAFAFA`) are used for headers to reduce the harshness of pure white on black, while muted grays (`#A1A1AA`) handle secondary metadata.
- **Borders:** Low-contrast borders (`#27272A`) define the grid without creating visual noise.

## Typography

This design system utilizes a three-font strategy to differentiate between intent, content, and data.

1.  **Headings (Sora):** Used for page titles and section headers. Its geometric structure provides a modern, high-tech feel.
2.  **Body (DM Sans):** Selected for its exceptional legibility at small sizes. Used for all descriptive text, CRM notes, and form labels.
3.  **Data & Labels (JetBrains Mono):** Used for all monospaced elements including timestamps, numerical data, ID tags, and AI tool calls. This reinforces the "technical tool" aesthetic.

**Hierarchy Rules:**
- Use `data-mono` for any dynamic value retrieved from the database.
- Use `label-caps` for table headers and small category tags.
- Headlines should remain tight in tracking and line height to maintain a dense, compact look.

## Layout & Spacing

The layout follows a **Rigid Grid** philosophy to maximize information density while maintaining readability.

- **Grid:** A 12-column grid for desktop. Margins are fixed at 24px.
- **Density:** Information-heavy views (Tables/Feeds) use a compact 4px base unit. Forms and prose use a more generous 8px base unit to ensure focus.
- **Multi-Tenant Navigation:** A narrow (64px) sidebar for global tenant switching, paired with a wider (240px) collapsible navigation for CRM modules.
- **Tool Panels:** Right-aligned contextual panels (320px) are used for AI chat and detail views, sliding over content rather than reflowing it when possible.

## Elevation & Depth

In this design system, depth is communicated through **Tonal Layering** rather than heavy shadows.

- **Level 0 (Canvas):** `#0A0A0B`. The base background for the entire application.
- **Level 1 (Card/Surface):** `#111113`. Used for main content containers and table rows.
- **Level 2 (Overlay/Pop-over):** `#18181B`. Used for dropdowns, tooltips, and modals. These receive a subtle 1px border of `#27272A`.
- **Interactions:** Hover states on rows or cards should shift the background color slightly lighter (to `#1C1C1F`) or add a subtle glow from the amber accent, but never use traditional blurry drop shadows.

## Shapes

The shape language is "Soft-Technical." Elements use a small radius to feel modern but maintain a disciplined, architectural silhouette.

- **Buttons & Inputs:** 4px (Soft) corner radius.
- **Cards & Sections:** 8px radius for large containers.
- **Badges/Status:** Pill-shaped (fully rounded) to contrast against the predominantly rectangular grid.
- **Avatars:** Initial-based avatars should be squares with a 4px radius, using a subtle background glow based on the user's color assigned to the CRM tenant.

## Components

### Buttons & Inputs
- **Primary Action:** Solid Saffron (`#F5A623`) background with black text. High contrast, no gradient.
- **Secondary Action:** Ghost style with a 1px border of `#27272A` and off-white text.
- **Input Fields:** Darker than the surface (`#09090B`), 1px border. Focus state is a 1px Saffron border with no "outer glow" or "halo."

### Data Elements
- **Pill Status Badges:** Small, condensed text using `data-mono`. Backgrounds should be low-opacity versions of the status color (e.g., 10% green for "Active").
- **Table Rows:** High density. 32px or 40px height. Use monospaced font for all numerical columns.
- **Initial Avatars:** No photos. Use a 2-letter initial with a subtle inner glow in the tenant's brand color.

### AI & Chat Components
- **Tool Call Cards:** Collapsible cards within the chat stream. Use a dark-gray background (`#18181B`) and a monospaced "Executing..." label in the header.
- **Chat Bubbles:** No rounded chat bubbles. Use a simple left-border accent to denote the speaker (Saffron for AI, White for User) on a flat background.
- **Smart Insights:** Highlighted using a subtle vertical Saffron ribbon on the left side of a standard card.

### Lists
- Multi-tenant lists use thin dividers (`1px solid #1C1C1F`). 
- Interactive list items use a "Raycast-style" highlight: a solid background shift with no border change.