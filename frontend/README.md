# NEXUS Frontend

React 19 + Vite + Tailwind CSS frontend for the NEXUS AI Research Intelligence Platform.

## Stack

- **React 19** with hooks
- **Vite 8** (build tool + dev server)
- **Tailwind CSS v3** with custom crimson/surface design tokens
- **Lucide React** for icons
- No additional UI library dependencies — all components are hand-built

## Development

```bash
npm install
npm run dev        # http://localhost:5173
```

Set the backend URL if not running on localhost:

```bash
VITE_API_URL=http://your-backend:8000 npm run dev
```

## Build

```bash
npm run build      # outputs to dist/
npm run preview    # preview production build locally
```

## Environment

| Variable | Default | Description |
|---|---|---|
| `VITE_API_URL` | `http://localhost:8000` | Backend API base URL |

## Component Structure

All components live in `src/App.jsx` as a single-file application:

| Component | Purpose |
|---|---|
| `AuthScreen` | Login / register with JWT token management |
| `App` | Root component, state management, API calls |
| `Sidebar` | Session config, file upload, retrieval mode, report length |
| `WorkflowPipeline` | Live 8-stage pipeline visualizer driven by trace events |
| `TraceConsole` | Streaming agent execution log with status indicators |
| `ReportView` | Full report renderer with collapsible sections, TOC, metrics |
| `SourceInspector` | Retrieval debugger panel with confidence bars and score breakdown |
| `HistoryModal` | Past report browser |
| `EmptyState` | Onboarding state with example queries |
| `CollapsibleSection` | Reusable collapsible report section |
| `MarkdownSection` | Lightweight markdown renderer with interactive citation buttons |
| `CitationButton` | Inline citation `[N]` button that opens the source inspector |
| `ConfidenceBar` | Animated score bar for retrieval/validation confidence |
| `StatusBadge` | Color-coded agent status pill |
| `GlassCard` | Base glass-morphism card primitive |
| `SectionDivider` | Labeled horizontal rule for sidebar grouping |
| `LoadingDots` | Animated three-dot loading indicator |

## Design Tokens

Defined in `tailwind.config.js` and `src/index.css`. See `design.md` in the project root for the full design system reference.

## Auth Flow

1. On mount, `App` checks `localStorage` for a stored JWT and validates it against `GET /auth/me`.
2. If valid, the user is admitted directly. If not, `AuthScreen` is shown.
3. All API calls inject `Authorization: Bearer <token>` via `authHeaders()`.
4. The download link passes the token as `?token=` query param for direct browser navigation.
5. Logout clears `localStorage` and resets all state.
