# MarsWalk 2.0 — Visual Identity Design System
## Cinematic Editorial Planetary Exploration Interface

**Document Version:** 1.0.0  
**Project:** MarsWalk 2.0 — Project Atlas  
**Workspace:** `E:\Python\NASA-Spaceapps\Marswalk`  
**Authors:** Creative Director, Senior Product Designer, Three.js Interface Engineer, Frontend Architect  

---

## 1. Visual Philosophy & Reference Synthesis

The MarsWalk 2.0 visual identity synthesizes three aesthetic traditions into a cohesive, serious planetary exploration and mission-rehearsal interface:

```
┌─────────────────────────────────┐   ┌─────────────────────────────────┐   ┌─────────────────────────────────┐
│     REFERENCE 1: AEROSPACE      │   │     REFERENCE 2: PLANETARY      │   │       REFERENCE 3: ASPERA       │
│      STARTUP LANDING PAGE       │   │           ONBOARDING            │   │       EDITORIAL AESTHETIC       │
├─────────────────────────────────┤   ├─────────────────────────────────┤   ├─────────────────────────────────┤
│ • Deep midnight navy / black    │   │ • Nearly black starfield void   │   │ • Elegant oversized serif type  │
│ • Bold oversized typography     │   │ • Dominant planetary hero       │   │ • Refined serif / sans pairing  │
│ • Cinematic planetary focus     │   │ • Restrained scientific labels  │   │ • Subtle translucent glass      │
│ • Contrast coral/crimson accent │   │ • Generous negative space       │   │ • Delicate hairline separators  │
│ • Distinctive vertical selector │   │ • Atmospheric entry feeling     │   │ • Art-directed composition      │
└─────────────────────────────────┘   └─────────────────────────────────┘   └─────────────────────────────────┘
                                          │
                                          ▼
                      ┌────────────────────────────────────────┐
                      │    MARSWALK 2.0 ORIGINAL IDENTITY     │
                      │                                        │
                      │ • Foundation: Deep midnight space      │
                      │ • Brand Accent: Luminous Martian Coral │
                      │ • Secondary Accent: Soft Lavender/Rose │
                      │ • Display Font: Refined High-Contrast  │
                      │   Editorial Serif                      │
                      │ • UI & Telemetry: Modern Sans & Mono   │
                      │ • Scientific Integrity: Authoritative  │
                      │   data colors preserved                │
                      └────────────────────────────────────────┘
```

---

## 2. Design Tokens (`:root` CSS Custom Properties)

All design tokens are centralized in [`web/styles.css`](file:///E:/Python/NASA-Spaceapps/Marswalk/web/styles.css) under `:root`.

### 2.1 Color Palette

#### Space Foundation & Surfaces
```css
--bg-space-void: #03060c;           /* Deepest outer space void */
--bg-space-navy: #060a14;           /* Deep midnight space foundation */
--bg-surface-glass: rgba(8, 14, 26, 0.72);    /* Frosted translucent panel */
--bg-surface-elevated: rgba(12, 19, 35, 0.88); /* Floating HUD drawers & modals */
--bg-surface-card: rgba(16, 26, 48, 0.55);    /* Data stat cards */
--bg-surface-input: rgba(6, 11, 22, 0.85);    /* Text inputs & selects */
--bg-surface-hover: rgba(255, 255, 255, 0.05); /* Hover highlight */
```

#### Brand & Editorial Accents
```css
--accent-coral: #ff453a;            /* Primary brand accent: confident Martian coral */
--accent-coral-glow: rgba(255, 69, 58, 0.32); /* Radiant button and beacon glow */
--accent-coral-subtle: rgba(255, 69, 58, 0.12); /* Selected pill backgrounds */
--accent-crimson: #e63946;          /* Deep warning / emergency crimson */
--accent-lavender: #c4b5fd;         /* Editorial secondary accent (subdued lavender) */
--accent-rose: #fda4af;             /* Editorial tertiary accent (subdued rose) */
```

#### Scientific Data Colors (Preserved for Research Integrity)
```css
--data-telemetry-cyan: #00e5ff;     /* IAU coordinates, camera altitude, pitch */
--data-route-green: #00e676;        /* Conservative least-effort route */
--data-route-amber: #ffa726;        /* Balanced trade-off route */
--data-route-purple: #b388ff;       /* Science-first detour route */
--data-hazard-red: #ff1744;         /* Disruption hazards & blocked corridors */
```

#### Text Hierarchy
```css
--text-primary: #f8fafc;            /* Crisp primary white text (WCAG AAA on dark) */
--text-secondary: #94a3b8;          /* Slate secondary descriptions */
--text-tertiary: #64748b;           /* Muted metadata and PDS citations */
--text-accent: #ff5252;             /* Coral highlighted labels */
--text-code: #7dd3fc;               /* Tabular numbers and coordinate displays */
```

#### Hairlines, Borders & Shadows
```css
--border-hairline: rgba(255, 255, 255, 0.07);
--border-subtle: rgba(255, 255, 255, 0.12);
--border-medium: rgba(255, 255, 255, 0.22);
--border-coral: rgba(255, 69, 58, 0.45);
--border-cyan: rgba(0, 229, 255, 0.35);

--glass-blur: blur(18px);
--glass-blur-heavy: blur(28px);

--shadow-elevation-1: 0 4px 20px rgba(0, 0, 0, 0.5);
--shadow-elevation-2: 0 12px 40px rgba(0, 0, 0, 0.7);
--shadow-glow-coral: 0 0 28px rgba(255, 69, 58, 0.28);
--shadow-glow-cyan: 0 0 20px rgba(0, 229, 255, 0.25);
```

---

## 3. Typography Hierarchy & Font Pairing

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ DISPLAY HEADLINES: Refined Editorial Serif                                  │
│   "A NEW WORLD. WITHIN REACH."                                              │
│   Font Family: 'Cinzel', 'Playfair Display', 'EB Garamond', Georgia, serif  │
├─────────────────────────────────────────────────────────────────────────────┤
│ CONTROLS, LABELS & NARRATIVE: Modern Geometric Sans                         │
│   "Interactive planetary exploration, terrain-adjusted routing..."          │
│   Font Family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif       │
├─────────────────────────────────────────────────────────────────────────────┤
│ TELEMETRY, RUN IDS & TIMELINES: High-Precision Tabular Mono                 │
│   18.4447°N, 77.4508°E • ALT: 2,400 m • 3,149.2 m • 01:53:00               │
│   Font Family: 'JetBrains Mono', 'SF Mono', Consolas, monospace             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Centralized Font Tokens
```css
--font-display: 'Cinzel', 'Playfair Display', 'Bodoni MT', 'Didot', 'Georgia', serif;
--font-sans: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
--font-mono: 'JetBrains Mono', 'SF Mono', Menlo, Consolas, monospace;
```

> [!TIP]
> **Aspera Font Replacement Note**  
> If the specific proprietary typeface from the Aspera reference is identified in a subsequent milestone, update `--font-display` in `:root`. All headlines, landing copy, and modal titles will inherit the change automatically without editing application JavaScript or markup.

---

## 4. Component Design Patterns

### 4.1 Landing Hero Composition
- **Full Viewport Stage:** Positioned directly over the Three.js 3D canvas so the rotating Mars globe serves as an authentic background.
- **Minimal Header:**
  - Left: Brand mark `MARSWALK` with coral accent and `PROJECT ATLAS` subtitle.
  - Center: Minimal navigation (`Explore`, `Missions`, `About`, `How it works`).
  - Right: `Launch Atlas &rarr;` quick action.
- **Hero Typography:**
  - Category kicker: `[01 / EXPEDITION ARCHITECTURE]`.
  - Display headline: `A NEW WORLD.<br><span class="editorial-italic">WITHIN REACH.</span>`
  - Supporting narrative: Accurately explains MarsWalk as a planetary exploration and mission-rehearsal system.
  - Primary CTA: `Explore Mars &rarr;` (triggers onboarding or enters atlas).
  - Secondary CTA: `How it works` (triggers guided planetary onboarding).
- **Vertical Destination Selector:**
  - Inspired by Reference 1: Curated destination list (`01 Jezero Crater`, `02 Olympus Mons`, `03 Valles Marineris`, `04 Gale Crater`) with latitude, longitude, and direct camera preview affordance.

### 4.2 Planetary Onboarding (3 Concise Steps)
- **Step 1 — Explore:** The Global Mars Atlas (IAU 2000 Sphere, 2,000+ gazetteer features, Viking & MOLA imagery).
- **Step 2 — Investigate:** Surveyed Jezero Crater & 20 m CTX Elevation Model (difference between optical imagery and elevation grids).
- **Step 3 — Rehearse:** Mission Waypoints, A* Least-Cost Routing & Disruption Gauntlet (stress tests, recovery, auditable workspaces).
- **Controls:** Step indicator dots, `Back`, `Continue`, `Skip`, and `Enter Atlas`.
- **Durability:** Persists `marswalk_onboarding_v1 = 'completed'` in `localStorage`. Reopenable anytime via the HUD header guide button.

### 4.3 Atlas Workstation Restyling
- **HUD Header:** Glassmorphic navigation strip with brand mark, search bar, basemap selector, guide button, and return-to-landing affordance.
- **Inspector Drawer:** Deep translucent panel (`--bg-surface-elevated`) with coral section tags (`[01 MISSION PROFILE]`, `[02 ROUTE TELEMETRY]`, `[03 OPERATIONAL TIMELINE]`, etc.).
- **Telemetry Bar:** Floating bottom-left strip rendering live coordinates, camera altitude, pitch, and basemap layer in monospace tabular digits.

---

## 5. Responsive Breakpoint Rules

| Breakpoint | Target Screen | Layout Adaptations |
| :--- | :--- | :--- |
| **Desktop Ultra** | $1920 \times 1080$ | 2-column hero with full vertical destination selector, generous negative space, expanded inspector drawer. |
| **Desktop Standard** | $1366 \times 768$ | Hero typography scaled via `clamp()`, vertical selector compact, side inspector max-height scrollable. |
| **Tablet** | $\approx 1024\text{ px}$ | Hero stacks or reflows, vertical selector horizontal, inspector collapsible to floating pill. |
| **Mobile** | $\approx 390\text{ px}$ | Minimal hero headline, single primary CTA, onboarding full-screen card, inspector drawer collapses into bottom sheet. |

---

## 6. Scientific Integrity & Attribution

- **Terrain Attribution:** USGS Astrogeology Science Center / MRO CTX Jezero Crater DTM at 20 m/pixel resolution (Fergason et al., 2020; DOI: 10.5066/P906QQT8).
- **Coordinate Reference System:** ESRI:103885 (IAU 2000 Mars Sphere, $R = 3,396,190\text{ m}$).
- **Operational Boundaries:** Modeled routes represent macro-slope terrain calculations and must never be cited as certified operational paths for human astronauts or rovers.
