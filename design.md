# NEXUS — Design System Reference

> Design language for the NEXUS AI Research Intelligence Platform.  
> Theme: enterprise AI intelligence workstation — cinematic, dark, precise.

---

## Design Philosophy

The interface is designed to feel like a **cyber research command center** — not a generic SaaS dashboard. Every visual decision reinforces the idea that the user is operating a powerful, trustworthy intelligence system.

**Guiding principles:**
- **Atmosphere over decoration** — depth and restraint over flashy effects
- **Hierarchy over density** — clear information layers, not information overload
- **Explainability** — every agent action, retrieval score, and confidence value is visible
- **Operational feel** — the UI should feel alive and responsive to the pipeline state

---

## Color Palette

### Core Surfaces

| Token | Value | Usage |
|---|---|---|
| `--bg-primary` | `#09090b` | Page background |
| `--bg-secondary` | `#111113` | Sidebar, panels |
| `--bg-panel` | `rgba(14,14,16,0.82)` | Glass panels |
| `--bg-card` | `rgba(18,18,20,0.70)` | Cards, list items |
| `--surface-800` | `#18181b` | Elevated surfaces |
| `--surface-700` | `#1c1c1f` | Input backgrounds |
| `--surface-600` | `#27272a` | Borders, dividers |

### Accent — Crimson

| Token | Hex | Usage |
|---|---|---|
| `crimson-400` | `#f87171` | Error states, high-risk badges |
| `crimson-500` | `#ef4444` | Active status dots, icons |
| `crimson-600` | `#dc2626` | Primary accent, glow source |
| `crimson-700` | `#b91c1c` | Active borders, button backgrounds |
| `crimson-800` | `#991b1b` | Button fill, panel accents |
| `crimson-900` | `#7f1d1d` | Subtle backgrounds |
| `crimson-950` | `#450a0a` | Deep tint backgrounds |

### Text

| Token | Hex | Usage |
|---|---|---|
| `zinc-50` | `#fafafa` | Primary headings |
| `zinc-100` | `#f4f4f5` | Body text |
| `zinc-300` | `#d4d4d8` | Secondary text |
| `zinc-400` | `#a1a1aa` | Muted body |
| `zinc-500` | `#71717a` | Labels, captions |
| `zinc-600` | `#52525b` | Placeholder text |
| `zinc-700` | `#3f3f46` | Disabled text |

### Semantic Colors

| State | Color | Usage |
|---|---|---|
| Success / Completed | `#86efac` (green-300) | Completed agent badges, integrity scores |
| Warning | `#fde68a` (yellow-200) | Medium risk, weak evidence |
| Error / High Risk | `#fca5a5` (red-300) | Errors, contradictions, high risk |
| Info | `#93c5fd` (blue-300) | Info badges |
| Active / Running | `#ef4444` (crimson-500) | Pulsing dots, active pipeline nodes |

---

## Typography

### Font Stack

```css
font-family: 'Inter', system-ui, sans-serif;        /* UI text */
font-family: 'JetBrains Mono', 'Fira Code', monospace; /* Code, IDs, scores */
```

Inter is loaded from Google Fonts. JetBrains Mono is used for all monospaced content: session IDs, report IDs, retrieval scores, timestamps, chunk content.

### Scale

| Role | Size | Weight | Color |
|---|---|---|---|
| Page title | `text-xl` (20px) | 700 | `zinc-100` |
| Section header | `text-base` (16px) | 700 | `zinc-200` |
| Card title | `text-sm` (14px) | 600 | `zinc-200` |
| Body | `text-sm` (14px) | 400 | `zinc-400` |
| Label | `text-[10px]` | 700 | `zinc-600` (uppercase, tracked) |
| Caption / meta | `text-[9px]–text-[11px]` | 400–600 | `zinc-600` |
| Monospace | `text-[11px]` | 400–500 | `zinc-400` |

Labels use `uppercase tracking-widest` consistently throughout the UI to create a terminal/instrument aesthetic.

---

## Spacing & Layout

### Grid

The layout is a three-column flex row:
```
[Sidebar 288px] [Main flex-1] [Inspector 320px (conditional)]
```

- Sidebar is fixed width, never collapses on desktop
- Main area scrolls independently
- Inspector slides in from the right when a citation is active

### Spacing Rhythm

- Panel padding: `p-4` or `p-5`
- Card padding: `p-3` or `p-4`
- Section gaps: `space-y-4` or `space-y-5`
- Label-to-content gap: `mb-1.5`
- Icon-to-text gap: `gap-2`

---

## Glassmorphism

### Glass Panel (heavy)
Used for: main content areas, auth card, modals.
```css
background: rgba(14,14,16,0.82);
backdrop-filter: blur(16px) saturate(1.4);
border: 1px solid rgba(255,255,255,0.055);
box-shadow: 0 4px 32px -4px rgba(0,0,0,0.55),
            inset 0 1px 0 rgba(255,255,255,0.04);
```

### Glass Card (light)
Used for: list items, feature cards, sidebar sections.
```css
background: rgba(18,18,20,0.70);
backdrop-filter: blur(10px);
border: 1px solid rgba(255,255,255,0.05);
```
On hover:
```css
background: rgba(24,24,27,0.80);
border-color: rgba(185,28,28,0.30);
box-shadow: 0 4px 20px -4px rgba(185,28,28,0.15);
```

---

## Background System

### Cinematic Background
Applied to the root `<div>` via `.bg-cinematic`:
```css
background:
  radial-gradient(ellipse 80% 50% at 50% -10%, rgba(185,28,28,0.12) 0%, transparent 60%),
  radial-gradient(ellipse 60% 40% at 80% 80%,  rgba(120,10,10,0.08) 0%, transparent 50%),
  radial-gradient(ellipse 40% 30% at 10% 60%,  rgba(80,0,0,0.06)   0%, transparent 50%),
  #09090b;
```

A subtle top-center crimson bloom creates depth without being distracting. Additional ambient glow divs (blurred, pointer-events-none) are placed behind key UI regions.

### Noise Overlay
`.noise-overlay::after` adds a 3.5% opacity SVG fractal noise texture over the background to break up flat surfaces and add tactile depth.

---

## Glow System

| Class | Value | Usage |
|---|---|---|
| `.glow-red` | `box-shadow: 0 0 30px -4px rgba(220,38,38,0.22)` | Brand icon, active elements |
| `.glow-red-focus` | `0 0 0 1px rgba(220,38,38,0.5), 0 0 24px -4px rgba(220,38,38,0.25)` | Focused inputs |
| `.shadow-glow-red` | `0 0 30px -4px rgba(220,38,38,0.25)` | Active citation buttons |
| `.shadow-glow-red-lg` | `0 0 60px -8px rgba(220,38,38,0.30)` | Large glow regions |

Glows are always crimson-tinted. No blue, purple, or neon glows anywhere in the system.

---

## Animation System

All animations are CSS keyframe-based (no Framer Motion dependency).

### Keyframes

| Name | Duration | Usage |
|---|---|---|
| `fadeIn` | 0.4s ease | Panel/modal entry |
| `slideUp` | 0.35s ease | Section reveal, card entry |
| `slideLeft` | 0.3s ease | Inspector panel slide-in |
| `glowPulse` | 2s infinite | Brand icon, active state glow |
| `shimmer` | 1.8s linear | Skeleton loading bars |
| `dotBounce` | 1.2s infinite | Three-dot loading indicator |
| `borderFlow` | 3s linear | Animated border accent |
| `scanLine` | 3s linear | Reserved for future use |

### Usage Rules

- Entry animations (`fadeIn`, `slideUp`) fire once on mount — not on every re-render
- `animate-pulse` (Tailwind built-in) is used for status dots and active pipeline nodes
- Shimmer skeletons appear during the research loading state
- No `transition-all` on large layout elements — only targeted `transition-colors`, `transition-border`, `transition-shadow`

---

## Component Patterns

### Status Badge
Color-coded pill for agent execution status.
```
started   → crimson background, red text
completed → green background, green text
warning   → yellow background, yellow text
error     → deep red background, red text
info      → blue background, blue text
```

### Workflow Pipeline Node
Each of the 8 pipeline stages renders as a small card:
- **Idle**: `border-zinc-800/50 bg-surface-800/40`, grey icon
- **Active**: `border-crimson-600/60 bg-crimson-950/30`, crimson pulsing icon, `box-shadow` glow
- **Completed**: `border-green-800/40 bg-green-950/20`, green icon
- **Error**: `border-red-900/50 bg-red-950/20`, red icon

### Confidence Bar
A 3px tall bar using `linear-gradient(90deg, #991b1b, #dc2626)`. Width is set via inline style as `score * 100%`. Transitions with `transition: width 0.6s ease`.

### Command Input
The query bar uses `.command-input` which has:
- Dark near-black background
- Subtle white border at rest
- Crimson border + outer glow on `:focus-within`
- No rounded pill shape — rectangular with `rounded-xl` for a terminal feel

### Collapsible Section
Report sections are collapsible with a chevron toggle. The section header shows:
- Left accent bar (2px crimson vertical line)
- Section title
- Confidence score badge (font-mono, muted)
- Generation latency (font-mono, very muted)

---

## Icon Usage

All icons are from **Lucide React**. Icon sizing:
- Navigation / header: `w-3.5 h-3.5`
- Card icons: `w-4 h-4`
- Feature icons: `w-4 h-4` to `w-5 h-5`
- Inline / label icons: `w-3 h-3`

Icon colors follow the text hierarchy — never use a bright icon color without a semantic reason.

---

## Sidebar Structure

```
[Brand logo + name]
─────────────────────
[User badge + history button]
── SESSION ──────────────────
[Session ID input]
── DOCUMENTS ────────────────
[File upload zone]
[Uploaded files list]
── RETRIEVAL MODE ───────────
[2×2 mode grid]
── REPORT LENGTH ────────────
[Short / Medium / Detailed toggle]
─────────────────────
[Status dot + version]
```

`SectionDivider` components with uppercase labels create clear visual grouping between sidebar sections.

---

## Report Layout

```
[Title card — gradient, report ID, metadata strip]
[Metrics strip — 5 KPI cards: latency, LLM calls, searches, chunks, retries]
[Executive Summary — left crimson border accent]
[Section 1 — collapsible]
[Section 2 — collapsible]
...
[Risks & Challenges — collapsible]
[Integrity Audit — collapsible]
[Sources Appendix — collapsible, closed by default]
```

The floating TOC button in the title card opens a dropdown with jump links to each section.

---

## Responsive Behavior

The current layout is optimized for desktop (1280px+). On smaller screens:
- The sidebar remains visible but may overlap content below ~900px
- The source inspector panel pushes content left — on narrow screens it may need to be made a modal overlay
- Report sections are single-column and scroll naturally

Full mobile responsiveness is a planned improvement.

---

## What Not To Do

- **No neon colors** — no `#00ff00`, no electric blue, no hot pink
- **No `transition-all`** on layout elements — causes jank
- **No flat backgrounds** — always use the cinematic gradient or glass surfaces
- **No indigo/purple** — the palette is strictly crimson + zinc + surface
- **No excessive animation** — one animation per element, purposeful only
- **No `text-xs` for body copy** — minimum `text-sm` for readable content
- **No unstyled `<button>`** — always include hover, active, disabled states
