"use client";

import Link from "next/link";
import { ArrowRight, Brain, Github, Layers, Shield, Sparkles, Wand2, Zap } from "lucide-react";

const PIPELINE = [
  { label: "Prompt", color: "from-violet-500 to-violet-600",   glow: "rgba(124,58,237,0.6)",  icon: "✦" },
  { label: "Enhance",color: "from-cyan-500 to-cyan-600",      glow: "rgba(6,182,212,0.6)",   icon: "⟡" },
  { label: "Style",  color: "from-pink-500 to-pink-600",      glow: "rgba(236,72,153,0.6)",  icon: "◈" },
  { label: "Generate",color:"from-orange-500 to-orange-600",  glow: "rgba(249,115,22,0.6)",  icon: "⬡" },
  { label: "Quality", color:"from-emerald-500 to-emerald-600",glow: "rgba(16,185,129,0.6)",  icon: "✓" },
];

const FEATURES = [
  {
    icon: Brain,
    accent: "violet",
    title: "Multi-Agent AI Pipeline",
    description: "Four autonomous agents collaborate — PromptEnhancer, StyleSelector, Generator, QualityValidator — orchestrated by a DAG execution engine.",
    tags: ["Ollama", "SDXL-Turbo", "ModelScope"],
  },
  {
    icon: Layers,
    accent: "cyan",
    title: "Custom DSA Engine",
    description: "Every data structure hand-crafted: MinHeap scheduler, O(1) LRU cache, Trie autocomplete, Token Bucket rate limiter, Bloom Filter deduplication.",
    tags: ["MinHeap", "LRU Cache", "Trie", "Bloom Filter"],
  },
  {
    icon: Zap,
    accent: "pink",
    title: "Production Architecture",
    description: "Async FastAPI backend, Celery workers, Redis queues, PostgreSQL, ONNX inference on CoreML — built to scale horizontally.",
    tags: ["FastAPI", "Celery", "Redis", "PostgreSQL"],
  },
  {
    icon: Shield,
    accent: "orange",
    title: "100% Open Source",
    description: "Zero paid APIs. Runs entirely on your hardware with local Ollama + diffusers. MIT licensed. No hidden costs, no vendor lock-in.",
    tags: ["MIT License", "Local AI", "No API Keys"],
  },
];

const ACCENT = {
  violet: { bg: "bg-violet-500/10", border: "border-violet-500/20", text: "text-violet-400", glow: "0 0 30px rgba(124,58,237,0.3)" },
  cyan:   { bg: "bg-cyan-500/10",   border: "border-cyan-500/20",   text: "text-cyan-400",   glow: "0 0 30px rgba(6,182,212,0.3)" },
  pink:   { bg: "bg-pink-500/10",   border: "border-pink-500/20",   text: "text-pink-400",   glow: "0 0 30px rgba(236,72,153,0.3)" },
  orange: { bg: "bg-orange-500/10", border: "border-orange-500/20", text: "text-orange-400", glow: "0 0 30px rgba(249,115,22,0.3)" },
};

const STATS = [
  { val: "6",    label: "DSA Algorithms" },
  { val: "4",    label: "AI Agents" },
  { val: "0",    label: "API Keys Needed" },
  { val: "∞",   label: "Generations" },
];

export default function HomePage() {
  return (
    <main className="relative min-h-screen bg-space overflow-hidden">

      {/* ── Animated background orbs ─────────────────────── */}
      <div className="pointer-events-none fixed inset-0 overflow-hidden">
        <div className="orb w-[700px] h-[700px] bg-violet-600/20 top-[-200px] left-[-200px] animate-float-a" style={{ filter: "blur(120px)" }} />
        <div className="orb w-[500px] h-[500px] bg-cyan-500/15 bottom-[-100px] right-[-150px] animate-float-b" style={{ filter: "blur(100px)" }} />
        <div className="orb w-[400px] h-[400px] bg-pink-500/10 top-[40%] right-[20%] animate-float-c" style={{ filter: "blur(90px)" }} />
        <div className="orb w-[300px] h-[300px] bg-orange-500/10 bottom-[20%] left-[15%] animate-float-a" style={{ filter: "blur(80px)", animationDelay: "-5s" }} />
      </div>

      {/* ── Grid overlay ─────────────────────────────────── */}
      <div className="pointer-events-none fixed inset-0 grid-bg opacity-60" />

      {/* ── Nav ──────────────────────────────────────────── */}
      <nav className="relative z-20 flex items-center justify-between px-6 md:px-12 py-5">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-violet-500 to-cyan-500 flex items-center justify-center shadow-lg" style={{ boxShadow: "0 0 20px rgba(124,58,237,0.5)" }}>
            <Sparkles size={16} className="text-white" />
          </div>
          <span className="font-bold text-lg tracking-tight">
            Idea<span className="text-gradient">Vault</span>
          </span>
        </div>

        <div className="flex items-center gap-2">
          <Link href="/gallery" className="hidden sm:flex text-sm text-white/50 hover:text-white px-4 py-2 rounded-xl transition-colors hover:bg-white/5">
            Gallery
          </Link>
          <a href="https://github.com" target="_blank" rel="noreferrer" className="hidden sm:flex items-center gap-1.5 text-sm text-white/50 hover:text-white px-4 py-2 rounded-xl transition-colors hover:bg-white/5">
            <Github size={15} /> GitHub
          </a>
          <Link href="/generate" className="btn-cta flex items-center gap-2 rounded-xl px-5 py-2.5 text-sm">
            <Wand2 size={15} /> Start Creating
          </Link>
        </div>
      </nav>

      {/* ── Hero ─────────────────────────────────────────── */}
      <section className="relative z-10 flex flex-col items-center text-center px-6 pt-20 pb-32 gap-8">

        {/* Badge */}
        <div className="animate-appear delay-1 inline-flex items-center gap-2.5 rounded-full border border-violet-500/30 bg-violet-500/10 px-5 py-2 text-sm text-violet-300 backdrop-blur-sm">
          <span className="relative flex h-2 w-2">
            <span className="animate-ping absolute h-full w-full rounded-full bg-violet-400 opacity-75" />
            <span className="relative rounded-full h-2 w-2 bg-violet-400" />
          </span>
          Open Source · Runs 100% Locally · MIT License
        </div>

        {/* Headline */}
        <div className="animate-appear delay-2 space-y-2">
          <h1 className="text-5xl md:text-7xl lg:text-8xl font-black tracking-tight leading-none">
            Enter the World
          </h1>
          <h1 className="text-5xl md:text-7xl lg:text-8xl font-black tracking-tight leading-none text-gradient">
            of AI Creation
          </h1>
        </div>

        {/* Sub */}
        <p className="animate-appear delay-3 max-w-2xl text-lg md:text-xl text-white/45 leading-relaxed">
          Describe anything. IdeaVault&apos;s multi-agent pipeline enhances your prompt, selects the optimal model, generates stunning visuals, and quality-checks — all autonomously.
        </p>

        {/* CTAs */}
        <div className="animate-appear delay-4 flex flex-col sm:flex-row gap-4">
          <Link href="/generate" className="btn-cta flex items-center justify-center gap-2.5 rounded-2xl px-10 py-4 text-base">
            <Wand2 size={20} /> Start Generating
            <ArrowRight size={18} />
          </Link>
          <a href="https://github.com" target="_blank" rel="noreferrer"
            className="flex items-center justify-center gap-2.5 rounded-2xl border border-white/10 bg-white/5 hover:bg-white/10 hover:border-white/20 text-white/70 hover:text-white font-semibold px-10 py-4 text-base transition-all backdrop-blur-sm">
            <Github size={20} /> View Source
          </a>
        </div>

        {/* Stats */}
        <div className="animate-appear delay-5 grid grid-cols-2 sm:grid-cols-4 gap-4 mt-4 w-full max-w-2xl">
          {STATS.map(({ val, label }) => (
            <div key={label} className="glass rounded-2xl py-4 px-2 text-center">
              <div className="text-3xl font-black text-gradient">{val}</div>
              <div className="text-xs text-white/40 mt-1">{label}</div>
            </div>
          ))}
        </div>
      </section>

      {/* ── Pipeline visualizer ───────────────────────────── */}
      <section className="relative z-10 px-6 pb-24">
        <div className="max-w-4xl mx-auto">
          <div className="text-center mb-12 animate-appear delay-1">
            <p className="text-xs text-white/30 uppercase tracking-[0.3em] mb-3">How it works</p>
            <h2 className="text-3xl md:text-4xl font-bold">
              The <span className="text-gradient">AI Pipeline</span>
            </h2>
          </div>

          <div className="glass rounded-3xl p-8 border-glow">
            <div className="flex flex-col md:flex-row items-center justify-between gap-4">
              {PIPELINE.map((step, i) => (
                <div key={step.label} className="flex md:flex-col items-center gap-3 md:gap-2 flex-1">
                  <div className="relative flex-shrink-0">
                    {/* Pulse ring */}
                    <div className="absolute inset-0 rounded-2xl animate-ping opacity-30"
                      style={{ background: `radial-gradient(${step.glow}, transparent)`, animationDuration: `${2 + i * 0.3}s` }} />
                    <div className={`relative w-14 h-14 rounded-2xl bg-gradient-to-br ${step.color} flex items-center justify-center text-xl font-bold text-white shadow-lg`}
                      style={{ boxShadow: `0 0 25px ${step.glow}, 0 0 50px ${step.glow}33` }}>
                      {step.icon}
                    </div>
                  </div>
                  <div className="text-center md:text-center">
                    <div className="text-sm font-semibold text-white">{step.label}</div>
                    <div className="text-xs text-white/30">Step {i + 1}</div>
                  </div>
                  {i < PIPELINE.length - 1 && (
                    <div className="hidden md:block flex-1 h-px bg-gradient-to-r from-white/20 to-white/5 mx-1" />
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* ── Features ─────────────────────────────────────── */}
      <section className="relative z-10 px-6 pb-32">
        <div className="max-w-6xl mx-auto">
          <div className="text-center mb-14 animate-appear delay-1">
            <p className="text-xs text-white/30 uppercase tracking-[0.3em] mb-3">What&apos;s inside</p>
            <h2 className="text-3xl md:text-4xl font-bold">
              Built for <span className="text-gradient">Production</span>
            </h2>
          </div>

          <div className="grid md:grid-cols-2 gap-5">
            {FEATURES.map(({ icon: Icon, accent, title, description, tags }, i) => {
              const a = ACCENT[accent as keyof typeof ACCENT];
              return (
                <div key={title}
                  className={`animate-appear glass rounded-3xl p-7 group hover:border-opacity-50 transition-all duration-500 cursor-default delay-${i + 1}`}
                  style={{ animationDelay: `${i * 0.1}s` }}
                  onMouseEnter={e => { (e.currentTarget as HTMLElement).style.boxShadow = a.glow; }}
                  onMouseLeave={e => { (e.currentTarget as HTMLElement).style.boxShadow = ""; }}>
                  <div className={`w-12 h-12 rounded-2xl ${a.bg} border ${a.border} flex items-center justify-center mb-5 group-hover:scale-110 transition-transform`}>
                    <Icon size={22} className={a.text} />
                  </div>
                  <h3 className="text-lg font-bold text-white mb-2">{title}</h3>
                  <p className="text-sm text-white/45 leading-relaxed mb-4">{description}</p>
                  <div className="flex flex-wrap gap-2">
                    {tags.map(t => (
                      <span key={t} className={`text-xs px-2.5 py-1 rounded-full ${a.bg} ${a.text} border ${a.border}`}>{t}</span>
                    ))}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </section>

      {/* ── CTA Banner ───────────────────────────────────── */}
      <section className="relative z-10 px-6 pb-24">
        <div className="max-w-3xl mx-auto text-center glass rounded-3xl p-12 border-glow">
          <div className="text-4xl mb-4">🎨</div>
          <h2 className="text-3xl md:text-4xl font-black mb-4">
            Ready to <span className="text-gradient">create?</span>
          </h2>
          <p className="text-white/40 mb-8 max-w-md mx-auto">No API keys. No cloud costs. Just pure AI generation running on your machine.</p>
          <Link href="/generate" className="btn-cta inline-flex items-center gap-3 rounded-2xl px-10 py-4 text-base">
            <Sparkles size={20} /> Open the Studio
          </Link>
        </div>
      </section>

      {/* ── Footer ───────────────────────────────────────── */}
      <footer className="relative z-10 border-t border-white/5 px-6 py-8 text-center text-sm text-white/25">
        IdeaVault · MIT License · Built with FastAPI, Next.js, and local AI
      </footer>
    </main>
  );
}
