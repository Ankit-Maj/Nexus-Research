import React, { useState, useEffect, useRef, useCallback } from "react";
import {
  Search, Database, AlertTriangle, Download, CheckCircle, Activity,
  RefreshCw, X, FileUp, Sparkles, Play, Eye, LogOut, User, Lock,
  History, ChevronRight, Shield, Zap, Globe, FileText, BarChart2,
  Terminal, Cpu, BookOpen, TrendingUp, AlertCircle, Clock, Hash,
  ChevronDown, ChevronUp, ExternalLink, Copy, Check, Layers,
} from "lucide-react";

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

// ── Auth helpers ──────────────────────────────────────────────────────────────
const getToken  = () => localStorage.getItem("auth_token");
const setToken  = (t) => localStorage.setItem("auth_token", t);
const clearToken = () => localStorage.removeItem("auth_token");
const authHeaders = (extra = {}) => {
  const t = getToken();
  return t ? { Authorization: `Bearer ${t}`, ...extra } : { ...extra };
};

// ── Tiny primitives ───────────────────────────────────────────────────────────
const StatusDot = ({ active }) => (
  <span className={`inline-block w-1.5 h-1.5 rounded-full ${active ? "bg-crimson-500 animate-pulse" : "bg-zinc-600"}`} />
);

const LoadingDots = () => (
  <span className="inline-flex items-center gap-0.5 ml-1">
    <span className="w-1 h-1 rounded-full bg-crimson-400 dot-1" />
    <span className="w-1 h-1 rounded-full bg-crimson-400 dot-2" />
    <span className="w-1 h-1 rounded-full bg-crimson-400 dot-3" />
  </span>
);

const StatusBadge = ({ status, label }) => {
  const cls = {
    started:   "badge-started",
    completed: "badge-completed",
    warning:   "badge-warning",
    error:     "badge-error",
    info:      "badge-info",
  }[status] || "badge-info";
  return (
    <span className={`inline-flex items-center px-1.5 py-0.5 rounded text-[9px] font-bold uppercase tracking-wider ${cls}`}>
      {label || status}
    </span>
  );
};

const GlassCard = ({ children, className = "", hover = true, glow = false }) => (
  <div className={`glass-card rounded-xl ${glow ? "glow-red" : ""} ${hover ? "" : "!transition-none"} ${className}`}>
    {children}
  </div>
);

const SectionDivider = ({ label }) => (
  <div className="flex items-center gap-3 py-1">
    <div className="h-px flex-1 bg-gradient-to-r from-transparent via-zinc-800 to-transparent" />
    {label && <span className="text-[9px] font-bold uppercase tracking-widest text-zinc-600">{label}</span>}
    <div className="h-px flex-1 bg-gradient-to-r from-transparent via-zinc-800 to-transparent" />
  </div>
);

const ConfidenceBar = ({ score, label }) => (
  <div className="space-y-1">
    {label && <div className="flex justify-between text-[10px] text-zinc-500">
      <span>{label}</span><span className="text-zinc-400">{Math.round(score * 100)}%</span>
    </div>}
    <div className="h-0.5 bg-surface-700 rounded-full overflow-hidden">
      <div className="conf-bar" style={{ width: `${score * 100}%` }} />
    </div>
  </div>
);

// ── Auth Screen ───────────────────────────────────────────────────────────────
function AuthScreen({ onLogin }) {
  const [tab, setTab] = useState("login");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setError(""); setLoading(true);
    try {
      if (tab === "register") {
        const res = await fetch(`${API_BASE}/auth/register`, {
          method: "POST", headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ username, password }),
        });
        if (!res.ok) throw new Error((await res.json()).detail || "Registration failed.");
        setTab("login"); setError("Account created — sign in to continue.");
        setLoading(false); return;
      }
      const form = new URLSearchParams();
      form.append("username", username); form.append("password", password);
      const res = await fetch(`${API_BASE}/auth/login`, {
        method: "POST", headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body: form,
      });
      if (!res.ok) throw new Error((await res.json()).detail || "Login failed.");
      const data = await res.json();
      setToken(data.access_token); onLogin(username);
    } catch (err) { setError(err.message); }
    finally { setLoading(false); }
  };

  return (
    <div className="flex h-screen w-screen bg-cinematic items-center justify-center noise-overlay relative overflow-hidden">
      {/* Ambient glow */}
      <div className="absolute top-1/3 left-1/2 -translate-x-1/2 -translate-y-1/2 w-96 h-96 rounded-full bg-crimson-900/10 blur-3xl pointer-events-none" />

      <div className="relative z-10 w-full max-w-sm animate-fade-in">
        <div className="glass-panel rounded-2xl p-8 border border-zinc-800/60">
          {/* Logo */}
          <div className="flex items-center gap-3 mb-8">
            <div className="w-10 h-10 rounded-xl bg-crimson-900/60 border border-crimson-700/40 flex items-center justify-center glow-red">
              <Cpu className="w-5 h-5 text-crimson-400" />
            </div>
            <div>
              <div className="text-sm font-bold text-zinc-100 tracking-wide">NEXUS RESEARCH</div>
              <div className="text-[10px] text-crimson-500 font-semibold tracking-widest uppercase">Intelligence Platform</div>
            </div>
          </div>

          {/* Tab */}
          <div className="flex bg-surface-900 border border-zinc-800/60 rounded-lg p-0.5 mb-6">
            {["login","register"].map(t => (
              <button key={t} onClick={() => { setTab(t); setError(""); }}
                className={`flex-1 py-1.5 text-xs font-semibold rounded-md transition-all cursor-pointer ${
                  tab === t ? "bg-crimson-800/60 text-crimson-200 border border-crimson-700/40" : "text-zinc-500 hover:text-zinc-300"
                }`}>
                {t === "login" ? "Sign In" : "Register"}
              </button>
            ))}
          </div>

          <form onSubmit={submit} className="space-y-4">
            {[
              { icon: User, label: "Username", type: "text", val: username, set: setUsername, min: 3 },
              { icon: Lock, label: "Password", type: "password", val: password, set: setPassword, min: 6 },
            ].map(({ icon: Icon, label, type, val, set, min }) => (
              <div key={label}>
                <label className="text-[10px] font-bold text-zinc-500 uppercase tracking-widest block mb-1.5">{label}</label>
                <div className="command-input flex items-center gap-2 rounded-lg px-3 py-2.5">
                  <Icon className="w-3.5 h-3.5 text-zinc-600 shrink-0" />
                  <input type={type} value={val} onChange={e => set(e.target.value)}
                    required minLength={min}
                    className="bg-transparent border-none outline-none flex-1 text-zinc-200 text-sm placeholder-zinc-700"
                    placeholder={type === "password" ? "••••••••" : `min ${min} chars`} />
                </div>
              </div>
            ))}

            {error && (
              <p className={`text-xs px-3 py-2 rounded-lg border ${
                error.includes("created") ? "text-green-400 bg-green-950/30 border-green-800/40"
                  : "text-crimson-300 bg-crimson-950/30 border-crimson-800/40"
              }`}>{error}</p>
            )}

            <button type="submit" disabled={loading}
              className="w-full bg-crimson-800 hover:bg-crimson-700 disabled:bg-surface-700 disabled:text-zinc-600 text-crimson-100 font-bold text-sm py-2.5 rounded-lg transition-all cursor-pointer border border-crimson-700/50 hover:border-crimson-600/60 hover:shadow-glow-red mt-1">
              {loading ? "Authenticating..." : tab === "login" ? "Access Platform" : "Create Account"}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}

// ── Workflow Pipeline Visualizer ──────────────────────────────────────────────
const PIPELINE_STAGES = [
  { id: "router",    label: "Router",    icon: Zap },
  { id: "planner",   label: "Planner",   icon: Layers },
  { id: "rewriter",  label: "Rewriter",  icon: Hash },
  { id: "retrieval", label: "Retrieval", icon: Globe },
  { id: "writer",    label: "Writer",    icon: FileText },
  { id: "validator", label: "Validator", icon: Shield },
  { id: "risk",      label: "Risk",      icon: AlertTriangle },
  { id: "compiler",  label: "Compiler",  icon: BookOpen },
];

function getStageFromTrace(trace) {
  const name = (trace.agent_name || "").toLowerCase();
  const msg  = (trace.message  || "").toLowerCase();
  if (name.includes("router"))                          return "router";
  if (name.includes("planner"))                         return "planner";
  if (name.includes("rewriter") || name.includes("query rewriter")) return "rewriter";
  if (name.includes("search") || name.includes("retrieval") || name.includes("rag")) return "retrieval";
  if (name.includes("writer") || name.includes("summarizer"))       return "writer";
  if (name.includes("validator"))                       return "validator";
  if (name.includes("risk"))                            return "risk";
  if (name.includes("compiler"))                        return "compiler";
  // fallback: check message text for rewriter
  if (msg.includes("rewritten") || msg.includes("rewriting"))       return "rewriter";
  return null;
}

function WorkflowPipeline({ traces, isResearching }) {
  // Keep the most recent status per stage (last write wins)
  const stageStatus = {};
  traces.forEach(t => {
    const s = getStageFromTrace(t);
    if (s) stageStatus[s] = t.status;
  });

  return (
    <div className="flex items-center gap-1 overflow-x-auto pb-1">
      {PIPELINE_STAGES.map((stage, i) => {
        const status = stageStatus[stage.id];
        // A stage is "active" if it started but hasn't completed/errored yet
        const isActive = status === "started";
        const isDone   = status === "completed" || status === "warning";
        const isError  = status === "error";
        const isPending = !status;
        const Icon = stage.icon;

        return (
          <React.Fragment key={stage.id}>
            <div className={`workflow-node flex flex-col items-center gap-1 px-2.5 py-2 rounded-lg border min-w-[52px] ${
              isActive  ? "active border-crimson-600/60 bg-crimson-950/30" :
              isDone    ? "completed border-green-800/40 bg-green-950/20" :
              isError   ? "border-red-900/50 bg-red-950/20" :
                          "border-zinc-800/50 bg-surface-800/40"
            }`}>
              <Icon className={`w-3 h-3 ${
                isActive  ? "text-crimson-400 animate-pulse" :
                isDone    ? "text-green-400" :
                isError   ? "text-red-400" :
                            "text-zinc-600"
              }`} />
              <span className={`text-[8px] font-bold uppercase tracking-wider ${
                isActive  ? "text-crimson-300" :
                isDone    ? "text-green-400" :
                isError   ? "text-red-400" :
                            "text-zinc-600"
              }`}>{stage.label}</span>
            </div>
            {i < PIPELINE_STAGES.length - 1 && (
              <div className={`h-px w-3 shrink-0 ${isDone ? "bg-green-800/50" : "bg-zinc-800/50"}`} />
            )}
          </React.Fragment>
        );
      })}
    </div>
  );
}

// ── Trace Console ─────────────────────────────────────────────────────────────
function TraceConsole({ traces, isResearching, traceEndRef }) {
  return (
    <section className="h-56 border-t border-zinc-900 flex flex-col bg-surface-950/90">
      <div className="h-8 px-4 border-b border-zinc-900 flex items-center justify-between shrink-0">
        <div className="flex items-center gap-2">
          <Terminal className="w-3 h-3 text-crimson-600" />
          <span className="text-[10px] font-bold uppercase tracking-widest text-zinc-500">Agent Trace Console</span>
          {isResearching && <LoadingDots />}
        </div>
        {traces.length > 0 && (
          <span className="text-[9px] font-mono text-zinc-600 bg-surface-800 px-2 py-0.5 rounded border border-zinc-800">
            {traces.length} events
          </span>
        )}
      </div>

      <div className="flex-1 overflow-y-auto p-3 space-y-1.5 font-mono text-[11px]">
        {traces.length === 0 ? (
          <div className="flex items-center justify-center h-full text-zinc-700 text-[10px]">
            Awaiting workflow execution — trace events will stream here.
          </div>
        ) : (
          traces.map((trace, idx) => (
            <div key={idx} className="flex items-start gap-2.5 group">
              <span className="text-zinc-700 shrink-0 tabular-nums">{trace.timestamp}</span>
              <div className={`w-1 h-1 rounded-full mt-1.5 shrink-0 ${
                trace.status === "completed" ? "bg-green-500" :
                trace.status === "started"   ? "bg-crimson-500 animate-pulse" :
                trace.status === "error"     ? "bg-red-500" :
                trace.status === "warning"   ? "bg-yellow-500" : "bg-zinc-600"
              }`} />
              <StatusBadge status={trace.status} label={trace.agent_name?.replace(" Agent","")} />
              <span className="text-zinc-400 flex-1 min-w-0 truncate">{trace.message}</span>
              {trace.data?.route && (
                <span className="text-crimson-400 text-[9px] shrink-0">→ {trace.data.route}</span>
              )}
              {trace.data?.integrity_score && (
                <span className="text-green-400 text-[9px] shrink-0">{trace.data.integrity_score}/10</span>
              )}
            </div>
          ))
        )}
        <div ref={traceEndRef} />
      </div>
    </section>
  );
}

// ── Source Inspector ──────────────────────────────────────────────────────────
function SourceInspector({ citation, onClose }) {
  const [copied, setCopied] = useState(false);
  const copy = () => {
    navigator.clipboard.writeText(citation.content);
    setCopied(true); setTimeout(() => setCopied(false), 2000);
  };

  const scores = [
    { label: "Hybrid Score",  val: citation.score || 0 },
    { label: "Vector Score",  val: citation.vector_score || 0 },
    { label: "BM25 Score",    val: citation.bm25_score || 0 },
  ];

  return (
    <aside className="w-80 border-l border-zinc-900 flex flex-col bg-surface-950/95 animate-slide-left shrink-0">
      <div className="h-12 px-4 border-b border-zinc-900 flex items-center justify-between shrink-0">
        <div className="flex items-center gap-2">
          <Eye className="w-3.5 h-3.5 text-crimson-500" />
          <span className="text-[10px] font-bold uppercase tracking-widest text-zinc-400">Retrieval Inspector</span>
        </div>
        <button onClick={onClose} className="p-1 hover:bg-surface-700 rounded text-zinc-600 hover:text-zinc-300 transition-colors cursor-pointer">
          <X className="w-3.5 h-3.5" />
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {/* Source meta */}
        <div className="space-y-2">
          <div className="text-[9px] font-bold uppercase tracking-widest text-zinc-600">Source</div>
          <div className="text-sm font-semibold text-zinc-200 truncate" title={citation.source_name}>
            {citation.source_name}
          </div>
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-[9px] px-1.5 py-0.5 bg-surface-700 text-zinc-400 rounded border border-zinc-800 uppercase font-bold">
              {citation.source_type}
            </span>
            {citation.extraction_method && (
              <span className={`text-[9px] px-1.5 py-0.5 rounded border font-bold uppercase ${
                citation.extraction_method === "OCR"
                  ? "bg-yellow-950/30 text-yellow-400 border-yellow-800/40"
                  : "bg-surface-700 text-zinc-400 border-zinc-800"
              }`}>{citation.extraction_method}</span>
            )}
          </div>
          {citation.metadata?.url && (
            <a href={citation.metadata.url} target="_blank" rel="noreferrer"
              className="flex items-center gap-1 text-[10px] text-crimson-400 hover:text-crimson-300 transition-colors break-all">
              <ExternalLink className="w-2.5 h-2.5 shrink-0" />{citation.metadata.url}
            </a>
          )}
          {citation.metadata?.page && (
            <div className="text-[10px] text-zinc-500">Page {citation.metadata.page}</div>
          )}
        </div>

        <SectionDivider label="Retrieval Scores" />

        {/* Score bars */}
        <div className="space-y-3">
          {scores.map(({ label, val }) => (
            <ConfidenceBar key={label} label={label} score={val} />
          ))}
        </div>

        <SectionDivider label="Chunk Content" />

        {/* Chunk text */}
        <div className="bg-surface-900 border border-zinc-800/60 rounded-lg p-3 text-[11px] text-zinc-300 font-mono leading-relaxed select-text max-h-64 overflow-y-auto">
          {citation.content}
        </div>
      </div>

      <div className="p-3 border-t border-zinc-900 shrink-0">
        <button onClick={copy}
          className="w-full flex items-center justify-center gap-2 bg-surface-800 hover:bg-surface-700 border border-zinc-800 hover:border-zinc-700 text-zinc-300 text-xs font-semibold py-2 rounded-lg transition-all cursor-pointer">
          {copied ? <Check className="w-3.5 h-3.5 text-green-400" /> : <Copy className="w-3.5 h-3.5" />}
          {copied ? "Copied" : "Copy Chunk"}
        </button>
      </div>
    </aside>
  );
}

// ── Report Renderer ───────────────────────────────────────────────────────────
function CitationButton({ id, isActive, onClick }) {
  return (
    <button onClick={() => onClick(id)}
      className={`inline-flex items-center mx-0.5 px-1.5 py-0.5 text-[10px] font-bold rounded cursor-pointer transition-all ${
        isActive
          ? "bg-crimson-700 text-crimson-100 shadow-glow-red border border-crimson-600/60"
          : "bg-surface-700/80 text-crimson-400 hover:bg-crimson-900/40 border border-crimson-900/40 hover:border-crimson-700/50"
      }`}
      title="Inspect source">
      [{id}]
    </button>
  );
}

function renderWithCitations(text, activeCitationId, onCitationClick) {
  if (!text) return null;
  const parts = text.split(/(\[\d+\])/g);
  return parts.map((part, i) => {
    const m = part.match(/\[(\d+)\]/);
    if (m) {
      const id = parseInt(m[1]);
      return <CitationButton key={i} id={id} isActive={activeCitationId === id} onClick={onCitationClick} />;
    }
    return <span key={i}>{part}</span>;
  });
}

function MarkdownSection({ text, activeCitationId, onCitationClick }) {
  const lines = text.split("\n");
  return (
    <div className="space-y-1">
      {lines.map((line, idx) => {
        const t = line.trim();
        if (!t) return <div key={idx} className="h-2" />;
        if (t.startsWith("### ")) return <h4 key={idx} className="text-sm font-bold text-zinc-200 mt-4 mb-1.5">{t.slice(4)}</h4>;
        if (t.startsWith("## "))  return <h3 key={idx} className="text-base font-bold text-zinc-100 mt-5 mb-2 border-b border-zinc-800/60 pb-1">{t.slice(3)}</h3>;
        if (t.startsWith("# "))   return <h2 key={idx} className="text-lg font-bold text-zinc-50 mt-6 mb-2">{t.slice(2)}</h2>;
        if (t.startsWith("- ") || t.startsWith("* ")) return (
          <li key={idx} className="text-zinc-400 ml-4 list-disc list-outside text-sm leading-relaxed">
            {renderWithCitations(t.slice(2), activeCitationId, onCitationClick)}
          </li>
        );
        if (t.startsWith("**") && t.endsWith("**")) return (
          <p key={idx} className="text-zinc-300 font-semibold text-sm">{t.slice(2,-2)}</p>
        );
        return (
          <p key={idx} className="text-zinc-400 text-sm leading-relaxed">
            {renderWithCitations(line, activeCitationId, onCitationClick)}
          </p>
        );
      })}
    </div>
  );
}

function CollapsibleSection({ title, confidence, latency, children, defaultOpen = true }) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div className="glass-card rounded-xl overflow-hidden section-reveal">
      <button onClick={() => setOpen(o => !o)}
        className="w-full flex items-center justify-between px-5 py-4 hover:bg-surface-700/20 transition-colors cursor-pointer">
        <div className="flex items-center gap-3">
          <div className="w-0.5 h-4 bg-crimson-700 rounded-full" />
          <span className="text-sm font-bold text-zinc-200">{title}</span>
          {confidence != null && (
            <span className="text-[9px] px-1.5 py-0.5 bg-surface-700 text-zinc-500 rounded border border-zinc-800 font-mono">
              {Math.round(confidence * 100)}% conf
            </span>
          )}
          {latency != null && latency > 0 && (
            <span className="text-[9px] text-zinc-700 font-mono">{latency.toFixed(0)}ms</span>
          )}
        </div>
        {open ? <ChevronUp className="w-3.5 h-3.5 text-zinc-600" /> : <ChevronDown className="w-3.5 h-3.5 text-zinc-600" />}
      </button>
      {open && <div className="px-5 pb-5">{children}</div>}
    </div>
  );
}

function ReportView({ report, activeCitationId, onCitationClick }) {
  const [tocOpen, setTocOpen] = useState(false);

  return (
    <article className="space-y-4 animate-fade-in">
      {/* Title card */}
      <div className="relative overflow-hidden rounded-xl border border-zinc-800/60 bg-gradient-to-br from-surface-800/80 via-surface-900/60 to-surface-950/80 p-6">
        <div className="absolute top-0 right-0 w-64 h-64 bg-crimson-900/8 rounded-full blur-3xl pointer-events-none" />
        <div className="relative z-10">
          <div className="flex items-center gap-2 mb-3">
            <span className="text-[9px] font-bold uppercase tracking-widest text-crimson-600 border border-crimson-900/50 px-2 py-0.5 rounded">
              Intelligence Report
            </span>
            <span className="text-[9px] text-zinc-600 font-mono">{report.id}</span>
          </div>
          <h2 className="text-xl font-bold text-zinc-100 leading-tight mb-3">{report.title}</h2>
          {report.rewritten_query && report.rewritten_query !== report.query && (
            <div className="text-[10px] text-zinc-600 mb-3 font-mono">
              <span className="text-zinc-700">Rewritten: </span>{report.rewritten_query}
            </div>
          )}
          <div className="flex flex-wrap items-center gap-4 text-[10px] text-zinc-500">
            <span className="flex items-center gap-1"><Clock className="w-3 h-3" />{report.created_at?.split("T")[0]}</span>
            <span className="flex items-center gap-1"><Shield className="w-3 h-3 text-green-500" />
              <span className="text-green-400 font-semibold">{report.validation?.overall_integrity_score}/10.0</span> integrity
            </span>
            <span className="flex items-center gap-1"><Hash className="w-3 h-3" />{report.citations?.length} sources</span>
            {report.metrics && (
              <span className="flex items-center gap-1"><Activity className="w-3 h-3" />{report.metrics.total_latency_ms?.toFixed(0)}ms</span>
            )}
          </div>
        </div>

        {/* Floating TOC toggle */}
        <button onClick={() => setTocOpen(o => !o)}
          className="absolute top-4 right-4 flex items-center gap-1.5 text-[9px] font-bold uppercase tracking-wider text-zinc-600 hover:text-zinc-400 border border-zinc-800 hover:border-zinc-700 px-2 py-1 rounded transition-all cursor-pointer bg-surface-900/60">
          <BookOpen className="w-3 h-3" /> TOC
        </button>

        {tocOpen && (
          <div className="absolute top-12 right-4 z-20 bg-surface-900 border border-zinc-800 rounded-lg p-3 min-w-48 shadow-panel animate-fade-in">
            {report.sections?.map((s, i) => (
              <button key={i} onClick={() => { document.getElementById(`sec-${i}`)?.scrollIntoView({ behavior: "smooth" }); setTocOpen(false); }}
                className="block w-full text-left text-[10px] text-zinc-400 hover:text-crimson-300 py-1 px-2 rounded hover:bg-surface-800 transition-colors cursor-pointer truncate">
                {i + 1}. {s.title}
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Metrics strip */}
      {report.metrics && (
        <div className="grid grid-cols-5 gap-2">
          {[
            { label: "Latency",   val: `${report.metrics.total_latency_ms?.toFixed(0)}ms`, icon: Clock },
            { label: "LLM Calls", val: report.metrics.llm_calls, icon: Cpu },
            { label: "Searches",  val: report.metrics.tavily_calls, icon: Globe },
            { label: "Chunks",    val: report.metrics.rag_chunks_retrieved, icon: Database },
            { label: "Retries",   val: report.metrics.retry_count, icon: RefreshCw },
          ].map(({ label, val, icon: Icon }) => (
            <div key={label} className="glass-card rounded-lg p-3 text-center">
              <Icon className="w-3 h-3 text-zinc-600 mx-auto mb-1" />
              <div className="text-sm font-bold text-zinc-300 font-mono">{val ?? "—"}</div>
              <div className="text-[9px] text-zinc-600 uppercase tracking-wider">{label}</div>
            </div>
          ))}
        </div>
      )}

      {/* Executive Summary */}
      <div className="glass-card rounded-xl p-5 border-l-2 border-crimson-800/60">
        <div className="flex items-center gap-2 mb-3">
          <TrendingUp className="w-4 h-4 text-crimson-500" />
          <span className="text-xs font-bold uppercase tracking-widest text-crimson-400">Executive Summary</span>
        </div>
        <p className="text-zinc-300 text-sm leading-relaxed">{report.executive_summary}</p>
      </div>

      {/* Sections */}
      {report.sections?.map((section, i) => (
        <div key={i} id={`sec-${i}`}>
          <CollapsibleSection
            title={section.title}
            confidence={section.confidence_score}
            latency={section.generation_latency_ms}>
            <MarkdownSection
              text={section.content}
              activeCitationId={activeCitationId}
              onCitationClick={onCitationClick} />
          </CollapsibleSection>
        </div>
      ))}

      {/* Risk Assessment */}
      {report.risk_assessment && (
        <CollapsibleSection title="Risks & Challenges Assessment">
          <p className="text-zinc-400 text-sm mb-4 leading-relaxed">{report.risk_assessment.summary}</p>
          <div className="space-y-2">
            {report.risk_assessment.risks?.map((risk, i) => (
              <div key={i} className="flex items-start gap-3 p-3 bg-surface-900/60 rounded-lg border border-zinc-800/50">
                <span className={`text-[9px] font-bold px-2 py-0.5 rounded border uppercase shrink-0 mt-0.5 ${
                  risk.level === "HIGH"   ? "bg-red-950/40 text-red-400 border-red-900/50" :
                  risk.level === "MEDIUM" ? "bg-yellow-950/30 text-yellow-400 border-yellow-900/40" :
                                           "bg-green-950/30 text-green-400 border-green-900/40"
                }`}>{risk.level}</span>
                <div className="flex-1 min-w-0">
                  <div className="text-xs font-semibold text-zinc-300">{risk.impact}</div>
                  {risk.mitigation && (
                    <div className="text-[11px] text-zinc-500 mt-1">
                      <span className="text-crimson-500 font-semibold">Mitigation: </span>{risk.mitigation}
                    </div>
                  )}
                  {risk.confidence_score != null && (
                    <div className="mt-1.5"><ConfidenceBar score={risk.confidence_score} /></div>
                  )}
                </div>
              </div>
            ))}
          </div>
        </CollapsibleSection>
      )}

      {/* Validation */}
      {report.validation && (
        <CollapsibleSection title="Integrity & Verification Audit">
          <div className="flex items-center gap-4 mb-4 p-3 bg-surface-900/60 rounded-lg border border-zinc-800/50">
            <div className="w-12 h-12 rounded-full bg-green-950/40 border border-green-800/40 flex items-center justify-center shrink-0">
              <span className="text-base font-bold text-green-400">{report.validation.overall_integrity_score}</span>
            </div>
            <div>
              <div className="text-xs font-bold text-zinc-300">Fact-Check Score</div>
              <div className="text-[10px] text-zinc-500 mt-0.5">Validated by Validator Agent against source evidence.</div>
              <div className="mt-1.5 w-48"><ConfidenceBar score={report.validation.overall_integrity_score / 10} /></div>
            </div>
          </div>
          <div className="space-y-2">
            {report.validation.findings?.map((f, i) => (
              <div key={i} className="p-3 bg-surface-900/40 rounded-lg border border-zinc-800/40 text-xs">
                <div className="flex items-center gap-2 mb-1 flex-wrap">
                  <StatusBadge status={
                    f.finding_type === "CONTRADICTION" ? "error" :
                    f.finding_type === "WEAK_EVIDENCE" ? "warning" : "completed"
                  } label={f.finding_type} />
                  <span className="text-zinc-500">Source: <span className="text-zinc-300 font-semibold">{f.source}</span></span>
                  {f.confidence_score != null && (
                    <span className="text-[9px] text-zinc-600 font-mono">{Math.round(f.confidence_score * 100)}% conf</span>
                  )}
                </div>
                <p className="text-zinc-400 leading-relaxed">{f.description}</p>
              </div>
            ))}
          </div>
        </CollapsibleSection>
      )}

      {/* Citations */}
      <CollapsibleSection title="Sources Appendix" defaultOpen={false}>
        <div className="space-y-3">
          {report.citations?.map((cit, i) => (
            <div key={i} className="flex items-start gap-3 p-3 bg-surface-900/40 rounded-lg border border-zinc-800/40 text-xs">
              <button onClick={() => onCitationClick(cit.citation_id)}
                className={`w-6 h-6 rounded border flex items-center justify-center font-bold shrink-0 transition-all cursor-pointer ${
                  activeCitationId === cit.citation_id
                    ? "bg-crimson-700 border-crimson-600 text-crimson-100 shadow-glow-red"
                    : "bg-surface-700 border-zinc-700 text-crimson-400 hover:bg-crimson-900/40 hover:border-crimson-700/50"
                }`}>{cit.citation_id}</button>
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2 flex-wrap mb-1">
                  <span className="font-semibold text-zinc-300">{cit.source_name}</span>
                  <span className="text-[9px] px-1 bg-surface-700 text-zinc-500 rounded uppercase border border-zinc-800">{cit.source_type}</span>
                  {cit.extraction_method === "OCR" && (
                    <span className="text-[9px] px-1 bg-yellow-950/30 text-yellow-500 rounded uppercase border border-yellow-900/40">OCR</span>
                  )}
                  {cit.page && <span className="text-zinc-600">p.{cit.page}</span>}
                </div>
                {cit.url && (
                  <a href={cit.url} target="_blank" rel="noreferrer"
                    className="text-[10px] text-crimson-500 hover:text-crimson-400 block mb-1 truncate">{cit.url}</a>
                )}
                {cit.retrieval_scores && (
                  <div className="flex gap-3 mb-1.5">
                    {[
                      ["H", cit.retrieval_scores.hybrid_score],
                      ["V", cit.retrieval_scores.vector_score],
                      ["B", cit.retrieval_scores.bm25_score],
                    ].map(([k, v]) => (
                      <span key={k} className="text-[9px] font-mono text-zinc-600">
                        {k}:<span className="text-zinc-400">{v?.toFixed(3)}</span>
                      </span>
                    ))}
                  </div>
                )}
                <p className="text-zinc-500 italic text-[11px] leading-relaxed">
                  "{cit.snippet?.length > 180 ? cit.snippet.slice(0, 180) + "…" : cit.snippet}"
                </p>
              </div>
            </div>
          ))}
        </div>
      </CollapsibleSection>
    </article>
  );
}

// ── History Modal ─────────────────────────────────────────────────────────────
function HistoryModal({ reports, onLoad, onClose }) {
  return (
    <div className="absolute inset-0 z-50 bg-surface-950/90 backdrop-blur-sm flex items-center justify-center p-8 animate-fade-in">
      <div className="glass-panel rounded-2xl w-full max-w-md max-h-[65vh] flex flex-col border border-zinc-800/60 shadow-panel">
        <div className="flex items-center justify-between p-5 border-b border-zinc-900">
          <div className="flex items-center gap-2">
            <History className="w-4 h-4 text-crimson-500" />
            <span className="text-sm font-bold text-zinc-200">Report History</span>
          </div>
          <button onClick={onClose} className="p-1 hover:bg-surface-700 rounded text-zinc-600 hover:text-zinc-300 transition-colors cursor-pointer">
            <X className="w-4 h-4" />
          </button>
        </div>
        <div className="flex-1 overflow-y-auto p-4 space-y-2">
          {reports.length === 0 ? (
            <p className="text-zinc-600 text-xs text-center py-8">No reports found.</p>
          ) : reports.map((r, i) => (
            <button key={i} onClick={() => onLoad(r.report_id)}
              className="w-full text-left p-3 glass-card rounded-lg hover:border-crimson-800/40 transition-all cursor-pointer">
              <div className="flex items-center justify-between mb-1">
                <span className="text-[10px] font-mono text-crimson-500">{r.report_id}</span>
                <span className="text-[9px] text-zinc-600">{r.created_at?.split("T")[0]}</span>
              </div>
              <p className="text-[11px] text-zinc-400 truncate">Session: {r.session_id}</p>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}

// ── Empty State ───────────────────────────────────────────────────────────────
function EmptyState({ onExampleClick }) {
  const examples = [
    "Tesla financial growth audit 2025",
    "Latest EV battery technology advancements",
    "AI market risks in Silicon Valley 2025",
  ];
  return (
    <div className="flex flex-col items-center justify-center h-full text-center px-8 py-16 animate-fade-in">
      <div className="relative mb-8">
        <div className="w-20 h-20 rounded-2xl bg-surface-800/80 border border-zinc-800/60 flex items-center justify-center mx-auto">
          <Cpu className="w-8 h-8 text-crimson-700" />
        </div>
        <div className="absolute -inset-4 bg-crimson-900/8 rounded-3xl blur-xl pointer-events-none" />
      </div>
      <h3 className="text-base font-bold text-zinc-300 mb-2">Intelligence System Ready</h3>
      <p className="text-xs text-zinc-600 max-w-sm leading-relaxed mb-8">
        Enter a research query to activate the multi-agent orchestration pipeline. The system will route, retrieve, synthesize, and compile a structured intelligence report.
      </p>
      <div className="grid grid-cols-3 gap-3 max-w-lg w-full mb-8">
        {[
          { icon: Zap,      title: "Auto-Routing",    desc: "Intelligent retrieval mode selection" },
          { icon: Layers,   title: "Parallel Agents", desc: "Concurrent section generation" },
          { icon: Shield,   title: "Validation",      desc: "Source integrity verification" },
        ].map(({ icon: Icon, title, desc }) => (
          <div key={title} className="glass-card rounded-xl p-4 text-left">
            <Icon className="w-4 h-4 text-crimson-600 mb-2" />
            <div className="text-[11px] font-bold text-zinc-300 mb-0.5">{title}</div>
            <div className="text-[10px] text-zinc-600 leading-snug">{desc}</div>
          </div>
        ))}
      </div>
      <div className="space-y-1.5 w-full max-w-sm">
        <div className="text-[9px] font-bold uppercase tracking-widest text-zinc-700 mb-2">Example Queries</div>
        {examples.map(ex => (
          <button key={ex} onClick={() => onExampleClick(ex)}
            className="w-full text-left text-[11px] text-zinc-500 hover:text-crimson-300 px-3 py-2 rounded-lg border border-zinc-900 hover:border-crimson-900/50 hover:bg-crimson-950/20 transition-all cursor-pointer flex items-center gap-2">
            <ChevronRight className="w-3 h-3 text-zinc-700 shrink-0" />{ex}
          </button>
        ))}
      </div>
    </div>
  );
}

// ── Sidebar ───────────────────────────────────────────────────────────────────
function Sidebar({
  currentUser, sessionId, setSessionId, uploadedFiles, isUploading,
  onFileUpload, mode, setMode, length, setLength, isResearching,
  onLogout, onHistory,
}) {
  return (
    <aside className="w-72 border-r border-zinc-900 flex flex-col bg-surface-950/80 shrink-0">
      {/* Brand */}
      <div className="p-5 border-b border-zinc-900 flex items-center gap-3">
        <div className="w-8 h-8 rounded-lg bg-crimson-900/50 border border-crimson-800/40 flex items-center justify-center glow-red shrink-0">
          <Cpu className="w-4 h-4 text-crimson-400" />
        </div>
        <div className="flex-1 min-w-0">
          <div className="text-sm font-bold text-zinc-100 tracking-wide">NEXUS</div>
          <div className="text-[9px] text-crimson-600 font-bold tracking-widest uppercase">Research Intelligence</div>
        </div>
        <button onClick={onLogout} title="Sign out"
          className="p-1.5 hover:bg-surface-700 rounded text-zinc-700 hover:text-crimson-400 transition-colors cursor-pointer shrink-0">
          <LogOut className="w-3.5 h-3.5" />
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-5">
        {/* User */}
        <div className="flex items-center gap-2 bg-surface-900/60 border border-zinc-800/50 rounded-lg px-3 py-2">
          <div className="w-6 h-6 rounded-full bg-crimson-900/50 border border-crimson-800/40 flex items-center justify-center shrink-0">
            <User className="w-3 h-3 text-crimson-400" />
          </div>
          <span className="text-xs font-semibold text-zinc-300 truncate flex-1">{currentUser}</span>
          <button onClick={onHistory} title="Report history"
            className="p-1 hover:bg-surface-700 rounded text-zinc-600 hover:text-crimson-400 transition-colors cursor-pointer">
            <History className="w-3 h-3" />
          </button>
        </div>

        <SectionDivider label="Session" />

        {/* Session ID */}
        <div>
          <label className="text-[9px] font-bold uppercase tracking-widest text-zinc-600 block mb-1.5">Session ID</label>
          <div className="flex items-center gap-1.5 bg-surface-900/60 border border-zinc-800/50 rounded-lg px-2.5 py-2">
            <Database className="w-3 h-3 text-zinc-700 shrink-0" />
            <input type="text" value={sessionId} onChange={e => setSessionId(e.target.value)}
              className="bg-transparent border-none outline-none flex-1 text-zinc-400 text-[11px] font-mono min-w-0"
              placeholder="session_id..." />
            <button onClick={() => setSessionId("session_" + Math.random().toString(36).slice(2, 9))}
              className="p-0.5 hover:bg-surface-700 rounded text-zinc-700 hover:text-zinc-400 transition-colors cursor-pointer shrink-0">
              <RefreshCw className="w-2.5 h-2.5" />
            </button>
          </div>
        </div>

        <SectionDivider label="Documents" />

        {/* Upload */}
        <div>
          <label className="text-[9px] font-bold uppercase tracking-widest text-zinc-600 block mb-1.5">RAG Sources</label>
          <div className="relative border border-dashed border-zinc-800 hover:border-crimson-800/50 rounded-xl p-4 text-center transition-colors bg-surface-900/30 cursor-pointer group">
            <input type="file" multiple onChange={onFileUpload} accept=".pdf,.docx,.txt,.md"
              className="absolute inset-0 opacity-0 cursor-pointer" disabled={isUploading} />
            <FileUp className="w-5 h-5 mx-auto mb-1.5 text-zinc-700 group-hover:text-crimson-600 transition-colors" />
            <span className="text-[11px] text-zinc-500 block font-medium">
              {isUploading ? "Ingesting..." : "Drop files or click"}
            </span>
            <span className="text-[9px] text-zinc-700 block mt-0.5">PDF · DOCX · TXT · MD</span>
          </div>

          {uploadedFiles.length > 0 && (
            <div className="mt-2 space-y-1 max-h-28 overflow-y-auto">
              {uploadedFiles.map((f, i) => (
                <div key={i} className="flex items-center gap-2 px-2.5 py-1.5 bg-surface-900/50 rounded-lg border border-zinc-800/40 text-[10px]">
                  <FileText className="w-3 h-3 text-crimson-600 shrink-0" />
                  <span className="truncate text-zinc-400 flex-1">{f}</span>
                  <span className="text-[8px] text-green-500 font-bold shrink-0">✓</span>
                </div>
              ))}
            </div>
          )}
        </div>

        <SectionDivider label="Retrieval Mode" />

        {/* Mode */}
        <div className="grid grid-cols-2 gap-1.5">
          {[
            { id: "AUTO",   label: "Auto",   desc: "Agent decides", icon: Zap },
            { id: "HYBRID", label: "Hybrid", desc: "Web + Docs",    icon: Layers },
            { id: "WEB",    label: "Web",    desc: "Tavily search", icon: Globe },
            { id: "RAG",    label: "Docs",   desc: "Uploaded files",icon: Database },
          ].map(({ id, label, desc, icon: Icon }) => (
            <button key={id} onClick={() => setMode(id)}
              className={`p-2.5 rounded-lg border text-left transition-all cursor-pointer ${
                mode === id
                  ? "border-crimson-700/50 bg-crimson-950/30 text-crimson-200"
                  : "border-zinc-800/50 hover:border-zinc-700/60 bg-surface-900/30 text-zinc-500 hover:text-zinc-400"
              }`}>
              <Icon className={`w-3 h-3 mb-1 ${mode === id ? "text-crimson-400" : "text-zinc-700"}`} />
              <div className="text-[10px] font-bold">{label}</div>
              <div className="text-[9px] text-zinc-700 mt-0.5">{desc}</div>
            </button>
          ))}
        </div>

        <SectionDivider label="Report Length" />

        {/* Length */}
        <div className="flex bg-surface-900/60 border border-zinc-800/50 rounded-lg p-0.5">
          {["Short","Medium","Detailed"].map(l => (
            <button key={l} onClick={() => setLength(l)}
              className={`flex-1 py-1.5 text-[10px] font-bold rounded-md transition-all cursor-pointer ${
                length === l
                  ? "bg-crimson-800/60 text-crimson-200 border border-crimson-700/40"
                  : "text-zinc-600 hover:text-zinc-400"
              }`}>{l}</button>
          ))}
        </div>
      </div>

      {/* Footer */}
      <div className="p-4 border-t border-zinc-900 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <StatusDot active={isResearching} />
          <span className="text-[10px] font-semibold text-zinc-600">
            {isResearching ? "Workflow Active" : "Standby"}
          </span>
        </div>
        <span className="text-[9px] text-zinc-700 font-mono">v2.0.0</span>
      </div>
    </aside>
  );
}

// ── Main App ──────────────────────────────────────────────────────────────────
function App() {
  const [currentUser, setCurrentUser] = useState(null);
  const [authChecked, setAuthChecked] = useState(false);

  const [sessionId, setSessionId] = useState("");
  const [query, setQuery] = useState("");
  const [mode, setMode] = useState("AUTO");
  const [length, setLength] = useState("Medium");
  const [uploadedFiles, setUploadedFiles] = useState([]);
  const [isUploading, setIsUploading] = useState(false);
  const [isResearching, setIsResearching] = useState(false);

  const [report, setReport] = useState(null);
  const [traces, setTraces] = useState([]);
  const [activeCitation, setActiveCitation] = useState(null);
  const [activeCitationId, setActiveCitationId] = useState(null);

  const [showHistory, setShowHistory] = useState(false);
  const [historyReports, setHistoryReports] = useState([]);

  const traceEndRef = useRef(null);
  const queryInputRef = useRef(null);

  // ── Auth check on mount ───────────────────────────────────────────────────
  useEffect(() => {
    const token = getToken();
    if (token) {
      fetch(`${API_BASE}/auth/me`, { headers: authHeaders() })
        .then(r => r.ok ? r.json() : null)
        .then(d => { if (d) setCurrentUser(d.username); else clearToken(); })
        .catch(() => clearToken())
        .finally(() => setAuthChecked(true));
    } else { setAuthChecked(true); }
  }, []);

  useEffect(() => {
    if (currentUser) setSessionId("session_" + Math.random().toString(36).slice(2, 9));
  }, [currentUser]);

  useEffect(() => {
    if (traceEndRef.current) traceEndRef.current.scrollIntoView({ behavior: "smooth" });
  }, [traces]);

  const handleLogout = () => {
    clearToken(); setCurrentUser(null); setReport(null);
    setTraces([]); setUploadedFiles([]);
  };

  // ── Upload ────────────────────────────────────────────────────────────────
  const handleFileUpload = async (e) => {
    const files = Array.from(e.target.files);
    if (!files.length) return;
    setIsUploading(true);
    const fd = new FormData();
    fd.append("session_id", sessionId);
    files.forEach(f => fd.append("files", f));
    try {
      const res = await fetch(`${API_BASE}/upload`, { method: "POST", headers: authHeaders(), body: fd });
      if (!res.ok) throw new Error((await res.json()).detail || "Upload failed");
      const data = await res.json();
      setUploadedFiles(p => [...p, ...data.files]);
    } catch (err) { alert(`Upload Error: ${err.message}`); }
    finally { setIsUploading(false); }
  };

  // ── Research ──────────────────────────────────────────────────────────────
  const triggerResearch = async () => {
    if (!query.trim()) return;
    setIsResearching(true); setReport(null); setTraces([]);
    setActiveCitation(null); setActiveCitationId(null);
    try {
      const res = await fetch(`${API_BASE}/research`, {
        method: "POST",
        headers: authHeaders({ "Content-Type": "application/json" }),
        body: JSON.stringify({ query, retrieval_mode: mode, length, session_id: sessionId }),
      });
      if (!res.ok) throw new Error((await res.json()).detail || "Research failed.");

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const parts = buffer.split("\n\n");
        buffer = parts.pop() || "";
        for (const part of parts) {
          if (!part.trim()) continue;
          if (part.startsWith("event: report")) {
            const jsonStr = part.replace("event: report\ndata: ", "").trim();
            setReport(JSON.parse(jsonStr));
            continue;
          }
          if (part.startsWith("data: ")) {
            try {
              const obj = JSON.parse(part.replace("data: ", "").trim());
              setTraces(p => [...p, obj]);
            } catch {}
          }
        }
      }
    } catch (err) { alert(`Research Error: ${err.message}`); }
    finally { setIsResearching(false); }
  };

  // ── Citation click ────────────────────────────────────────────────────────
  const handleCitationClick = useCallback(async (citationId) => {
    if (!report) return;
    setActiveCitationId(citationId);
    const key = `${report.id}_${citationId}`;
    try {
      const res = await fetch(`${API_BASE}/sources/${key}`, { headers: authHeaders() });
      if (!res.ok) throw new Error();
      setActiveCitation(await res.json());
    } catch {
      const cit = report.citations?.find(c => c.citation_id === citationId);
      if (cit) setActiveCitation({
        source_name: cit.source_name, source_type: cit.source_type,
        content: cit.snippet, score: cit.confidence_score || 1.0,
        vector_score: cit.retrieval_scores?.vector_score || 0,
        bm25_score: cit.retrieval_scores?.bm25_score || 0,
        extraction_method: cit.extraction_method || "DIRECT",
        metadata: { page: cit.page, url: cit.url },
      });
    }
  }, [report]);

  // ── History ───────────────────────────────────────────────────────────────
  const loadHistory = async () => {
    try {
      const res = await fetch(`${API_BASE}/history/reports`, { headers: authHeaders() });
      if (res.ok) setHistoryReports(await res.json());
    } catch {}
    setShowHistory(true);
  };

  const loadHistoricalReport = async (reportId) => {
    try {
      const res = await fetch(`${API_BASE}/history/reports/${reportId}`, { headers: authHeaders() });
      if (!res.ok) throw new Error("Not found");
      setReport(await res.json()); setShowHistory(false);
    } catch (e) { alert(e.message); }
  };

  // ── Auth gate ─────────────────────────────────────────────────────────────
  if (!authChecked) return (
    <div className="flex h-screen w-screen bg-surface-950 items-center justify-center">
      <div className="flex items-center gap-2 text-zinc-600 text-xs">
        <RefreshCw className="w-4 h-4 animate-spin" /> Authenticating...
      </div>
    </div>
  );
  if (!currentUser) return <AuthScreen onLogin={u => setCurrentUser(u)} />;

  // ── Main layout ───────────────────────────────────────────────────────────
  return (
    <div className="flex h-screen w-screen bg-cinematic font-sans text-zinc-100 overflow-hidden relative">
      {/* Ambient background glow */}
      <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[800px] h-[300px] bg-crimson-950/20 blur-3xl pointer-events-none z-0" />

      {/* History modal */}
      {showHistory && (
        <HistoryModal reports={historyReports} onLoad={loadHistoricalReport} onClose={() => setShowHistory(false)} />
      )}

      {/* Sidebar */}
      <Sidebar
        currentUser={currentUser} sessionId={sessionId} setSessionId={setSessionId}
        uploadedFiles={uploadedFiles} isUploading={isUploading} onFileUpload={handleFileUpload}
        mode={mode} setMode={setMode} length={length} setLength={setLength}
        isResearching={isResearching} onLogout={handleLogout} onHistory={loadHistory}
      />

      {/* Main */}
      <main className="flex-1 flex flex-col min-w-0 relative z-10">
        {/* Header */}
        <header className="h-12 border-b border-zinc-900 px-5 flex items-center justify-between bg-surface-950/60 shrink-0">
          <div className="flex items-center gap-2">
            <Activity className="w-3.5 h-3.5 text-crimson-700" />
            <span className="text-[10px] font-bold uppercase tracking-widest text-zinc-600">Research Workspace</span>
          </div>
          <div className="flex items-center gap-3">
            {isResearching && (
              <div className="flex items-center gap-1.5 text-[10px] text-crimson-400 font-semibold">
                <span className="w-1.5 h-1.5 rounded-full bg-crimson-500 animate-pulse" />
                Pipeline Active
              </div>
            )}
            {report && (
              <a href={`${API_BASE}/download/${report.id}?token=${getToken()}`}
                className="flex items-center gap-1.5 bg-surface-800 hover:bg-surface-700 border border-zinc-800 hover:border-zinc-700 text-zinc-300 text-[10px] font-semibold px-3 py-1.5 rounded-lg transition-all cursor-pointer">
                <Download className="w-3 h-3" /> Export MD
              </a>
            )}
          </div>
        </header>

        {/* Scrollable content */}
        <div className="flex-1 overflow-y-auto">
          <div className="p-5 space-y-4">

            {/* Command bar */}
            <div className="command-input rounded-xl p-4">
              <div className="flex items-start gap-3">
                <div className="w-9 h-9 rounded-lg bg-surface-800 border border-zinc-800/60 flex items-center justify-center shrink-0 mt-0.5">
                  <Search className="w-4 h-4 text-crimson-600" />
                </div>
                <div className="flex-1 min-w-0">
                  <input ref={queryInputRef} type="text" value={query}
                    onChange={e => setQuery(e.target.value)}
                    onKeyDown={e => e.key === "Enter" && !isResearching && triggerResearch()}
                    disabled={isResearching}
                    placeholder="Enter research query or intelligence mission..."
                    className="w-full bg-transparent border-none text-zinc-200 font-medium placeholder-zinc-700 outline-none text-sm" />
                </div>
                <button onClick={triggerResearch} disabled={isResearching || !query.trim()}
                  className="flex items-center gap-2 bg-crimson-800 hover:bg-crimson-700 disabled:bg-surface-700 disabled:text-zinc-600 text-crimson-100 font-bold text-xs py-2 px-4 rounded-lg transition-all cursor-pointer border border-crimson-700/50 hover:border-crimson-600/60 shrink-0">
                  {isResearching
                    ? <><RefreshCw className="w-3.5 h-3.5 animate-spin" /> Running</>
                    : <><Play className="w-3.5 h-3.5 fill-current" /> Execute</>}
                </button>
              </div>

              {/* Pipeline visualization */}
              {(isResearching || traces.length > 0) && (
                <div className="mt-3 pt-3 border-t border-zinc-900/60">
                  <WorkflowPipeline traces={traces} isResearching={isResearching} />
                </div>
              )}
            </div>

            {/* Report / empty state */}
            {report ? (
              <ReportView report={report} activeCitationId={activeCitationId} onCitationClick={handleCitationClick} />
            ) : isResearching ? (
              <div className="flex flex-col items-center justify-center py-20 space-y-4">
                <div className="relative">
                  <div className="w-12 h-12 rounded-xl bg-surface-800 border border-crimson-900/40 flex items-center justify-center">
                    <Cpu className="w-5 h-5 text-crimson-600 animate-pulse" />
                  </div>
                  <div className="absolute -inset-3 bg-crimson-900/10 rounded-2xl blur-xl" />
                </div>
                <div className="text-center">
                  <div className="text-sm font-bold text-zinc-300 mb-1">Orchestrating Research Pipeline</div>
                  <div className="text-xs text-zinc-600">Multi-agent system is active — monitor trace console below</div>
                </div>
                {/* Shimmer skeleton */}
                <div className="w-full max-w-lg space-y-2 mt-4">
                  {[80, 60, 90, 50].map((w, i) => (
                    <div key={i} className={`h-3 rounded shimmer`} style={{ width: `${w}%` }} />
                  ))}
                </div>
              </div>
            ) : (
              <EmptyState onExampleClick={q => { setQuery(q); queryInputRef.current?.focus(); }} />
            )}
          </div>
        </div>

        {/* Trace console */}
        <TraceConsole traces={traces} isResearching={isResearching} traceEndRef={traceEndRef} />
      </main>

      {/* Source inspector panel */}
      {activeCitation && (
        <SourceInspector
          citation={activeCitation}
          onClose={() => { setActiveCitation(null); setActiveCitationId(null); }}
        />
      )}
    </div>
  );
}

export default App;
