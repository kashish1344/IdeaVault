"use client";

import { AnimatePresence, motion } from "framer-motion";
import { useEffect, useRef, useState } from "react";
import {
  CheckCircle2,
  Clock,
  Download,
  Loader2,
  X,
  XCircle,
} from "lucide-react";
import { useCancelJob, useJobPoller } from "../../hooks/useGeneration";
import { cn, estimatedProgress, formatRelativeTime } from "../../lib/utils";
import type { Job } from "../../lib/api";

// ── Confetti particles (deterministic — no Math.random in render) ─────────────

const PARTICLES = Array.from({ length: 24 }, (_, i) => {
  const angle = (i / 24) * Math.PI * 2;
  const r = 70 + (i % 4) * 25;
  return {
    id: i,
    dx: Math.cos(angle) * r,
    dy: Math.sin(angle) * r - 20,
    color: ["#c4b5fd", "#67e8f9", "#f9a8d4", "#fbbf24", "#34d399", "#fb923c"][i % 6],
    size: 5 + (i % 3) * 2,
    delay: i * 0.025,
  };
});

// ── Status config ─────────────────────────────────────────────────────────────

const STATUS_CONFIG = {
  queued:     { icon: Clock,       label: "Queued",     badge: "bg-amber-500/15 border-amber-500/30 text-amber-300",   dot: "bg-amber-400",  barFrom: "from-amber-500",   barTo: "to-orange-500"  },
  processing: { icon: Loader2,     label: "Generating", badge: "bg-violet-500/15 border-violet-500/30 text-violet-300", dot: "bg-violet-400", barFrom: "from-violet-500",  barTo: "to-cyan-500"    },
  completed:  { icon: CheckCircle2,label: "Complete",   badge: "bg-emerald-500/15 border-emerald-500/30 text-emerald-300", dot: "bg-emerald-400", barFrom: "from-emerald-500", barTo: "to-teal-500" },
  failed:     { icon: XCircle,     label: "Failed",     badge: "bg-red-500/15 border-red-500/30 text-red-300",         dot: "bg-red-400",    barFrom: "from-red-500",     barTo: "to-rose-500"    },
  cancelled:  { icon: XCircle,     label: "Cancelled",  badge: "bg-zinc-500/15 border-zinc-500/30 text-zinc-400",      dot: "bg-zinc-500",   barFrom: "from-zinc-500",    barTo: "to-zinc-600"    },
} as const;

// ── Props ─────────────────────────────────────────────────────────────────────

interface Props {
  jobId: string;
  estimatedSeconds?: number;
  onComplete?: (job: Job) => void;
  onCancel?: () => void;
}

// ── Component ─────────────────────────────────────────────────────────────────

export function JobStatusCard({ jobId, estimatedSeconds = 30, onComplete, onCancel }: Props) {
  const { data: job, isLoading } = useJobPoller(jobId);
  const cancelMutation = useCancelJob(jobId);

  // Tick every second while active so the progress bar is smooth
  const [, setTick] = useState(0);
  useEffect(() => {
    if (job?.status !== "queued" && job?.status !== "processing") return;
    const id = setInterval(() => setTick((t) => t + 1), 1000);
    return () => clearInterval(id);
  }, [job?.status]);

  // Fire onComplete exactly once
  const completedRef = useRef(false);
  useEffect(() => {
    if (job?.status === "completed" && !completedRef.current) {
      completedRef.current = true;
      onComplete?.(job);
    }
  }, [job, onComplete]);

  // Show confetti burst on completion
  const [showConfetti, setShowConfetti] = useState(false);
  const confettiShownRef = useRef(false);
  useEffect(() => {
    if (job?.status === "completed" && !confettiShownRef.current) {
      confettiShownRef.current = true;
      setShowConfetti(true);
      const t = setTimeout(() => setShowConfetti(false), 1800);
      return () => clearTimeout(t);
    }
  }, [job?.status]);

  // Cancel confirmation state
  const [cancelPending, setCancelPending] = useState(false);
  useEffect(() => {
    if (!cancelPending) return;
    const t = setTimeout(() => setCancelPending(false), 3500);
    return () => clearTimeout(t);
  }, [cancelPending]);

  const handleCancel = async () => {
    if (!cancelPending) { setCancelPending(true); return; }
    await cancelMutation.mutateAsync();
    setCancelPending(false);
    onCancel?.();
  };

  // ── Loading skeleton ────────────────────────────────────────────

  if (isLoading || !job) {
    return (
      <div className="glass rounded-3xl p-6 space-y-4 border border-white/7">
        <div className="flex items-center gap-3">
          <div className="shimmer w-10 h-10 rounded-2xl" />
          <div className="flex-1 space-y-2">
            <div className="shimmer h-3 rounded-full w-1/3" />
            <div className="shimmer h-2 rounded-full w-1/2" />
          </div>
        </div>
        <div className="shimmer h-2 rounded-full w-full" />
      </div>
    );
  }

  const config = STATUS_CONFIG[job.status] ?? STATUS_CONFIG.queued;
  const Icon = config.icon;
  const progress = estimatedProgress(job.status, job.created_at, estimatedSeconds, job.started_at);
  const isActive = job.status === "queued" || job.status === "processing";

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ type: "spring", stiffness: 280, damping: 28 }}
      className="relative glass rounded-3xl overflow-hidden border-glow"
    >
      {/* Confetti burst */}
      <AnimatePresence>
        {showConfetti && (
          <div className="pointer-events-none absolute inset-0 flex items-center justify-center z-20 overflow-hidden">
            {PARTICLES.map((p) => (
              <motion.div
                key={p.id}
                initial={{ opacity: 1, x: 0, y: 0, scale: 0 }}
                animate={{ opacity: 0, x: p.dx, y: p.dy, scale: 1, rotate: 360 }}
                transition={{ duration: 1.4, ease: "easeOut", delay: p.delay }}
                className="absolute rounded-full"
                style={{ width: p.size, height: p.size, background: p.color }}
              />
            ))}
          </div>
        )}
      </AnimatePresence>

      {/* ── Header ── */}
      <div className="px-6 pt-6 pb-4 flex items-center justify-between gap-3">
        <div className="flex items-center gap-3 min-w-0">
          <div className={cn("w-10 h-10 rounded-2xl border flex-shrink-0 flex items-center justify-center", config.badge)}>
            <Icon size={18} className={cn(job.status === "processing" && "animate-spin")} />
          </div>
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <span className={cn("w-1.5 h-1.5 rounded-full flex-shrink-0", config.dot, job.status === "processing" && "animate-pulse")} />
              <span className="text-sm font-bold text-white">{config.label}</span>
            </div>
            <span className="text-xs text-white/30">{formatRelativeTime(job.created_at)}</span>
          </div>
        </div>

        <div className="flex items-center gap-2 flex-shrink-0">
          <div className={cn("text-xs px-3 py-1 rounded-full border font-medium", config.badge)}>
            {job.media_type}
          </div>

          {/* Cancel button */}
          {isActive && (
            <AnimatePresence mode="wait">
              {cancelPending ? (
                <motion.div
                  key="confirm"
                  initial={{ opacity: 0, scale: 0.9 }}
                  animate={{ opacity: 1, scale: 1 }}
                  exit={{ opacity: 0, scale: 0.9 }}
                  className="flex items-center gap-1"
                >
                  <button
                    type="button"
                    onClick={handleCancel}
                    disabled={cancelMutation.isPending}
                    className="text-xs px-2.5 py-1 rounded-lg bg-red-500/20 border border-red-500/40 text-red-400 hover:bg-red-500/30 transition-all font-semibold"
                  >
                    {cancelMutation.isPending ? "…" : "Confirm"}
                  </button>
                  <button
                    type="button"
                    onClick={() => setCancelPending(false)}
                    className="text-xs px-2 py-1 rounded-lg bg-white/5 border border-white/10 text-white/40 hover:text-white/70 transition-all"
                  >
                    Keep
                  </button>
                </motion.div>
              ) : (
                <motion.button
                  key="cancel"
                  type="button"
                  initial={{ opacity: 0, scale: 0.9 }}
                  animate={{ opacity: 1, scale: 1 }}
                  exit={{ opacity: 0, scale: 0.9 }}
                  onClick={handleCancel}
                  title="Cancel job"
                  className="w-7 h-7 rounded-lg bg-white/5 border border-white/10 flex items-center justify-center text-white/30 hover:text-red-400 hover:bg-red-500/10 hover:border-red-500/30 transition-all"
                >
                  <X size={13} />
                </motion.button>
              )}
            </AnimatePresence>
          )}
        </div>
      </div>

      {/* ── Prompt ── */}
      <div className="px-6 pb-4">
        <p className="text-sm text-white/55 leading-relaxed line-clamp-2 italic">
          &ldquo;{job.raw_prompt}&rdquo;
        </p>
      </div>

      {/* ── Progress bar (active jobs only) ── */}
      {isActive && (
        <div className="px-6 pb-5 space-y-2">
          <div className="relative h-2 w-full rounded-full bg-white/[6%] overflow-hidden">
            <motion.div
              className={cn("h-full rounded-full bg-gradient-to-r", config.barFrom, config.barTo)}
              initial={{ width: "0%" }}
              animate={{ width: `${progress}%` }}
              transition={{ duration: 1.0, ease: "linear" }}
            />
            {/* Shimmer sweep inside the filled portion */}
            {job.status === "processing" && (
              <motion.div
                className="absolute top-0 left-0 h-full w-12 bg-gradient-to-r from-transparent via-white/30 to-transparent rounded-full"
                animate={{ x: ["-48px", `${Math.max(progress, 10)}vw`] }}
                transition={{ duration: 2, repeat: Infinity, ease: "easeInOut", repeatDelay: 0.5 }}
              />
            )}
          </div>
          <div className="flex justify-between text-xs text-white/30">
            <span className="tabular-nums">{progress}% complete</span>
            <span>~{estimatedSeconds}s total</span>
          </div>

          {/* Wave bars */}
          {job.status === "processing" && (
            <div className="flex items-center justify-center gap-1 pt-1">
              {[0, 1, 2, 3, 4].map((i) => (
                <div key={i} className={`wave-bar h-4 delay-wave-${i}`} />
              ))}
              <span className="text-xs text-white/30 ml-2">AI is creating…</span>
            </div>
          )}
        </div>
      )}

      {/* ── Output ── */}
      {job.status === "completed" && job.output_url && (
        <div className="px-6 pb-6 space-y-3">
          {job.media_type === "image" ? (
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ delay: 0.15, type: "spring", stiffness: 200 }}
              className="relative rounded-2xl overflow-hidden border border-white/10"
              style={{ boxShadow: "0 0 40px rgba(139,92,246,0.25), 0 0 80px rgba(6,182,212,0.1)" }}
            >
              <img src={job.output_url} alt={job.raw_prompt} className="w-full object-cover" />
              <div className="absolute inset-0 bg-gradient-to-t from-black/50 to-transparent pointer-events-none" />
              <a
                href={job.output_url}
                download
                className="absolute bottom-3 right-3 flex items-center gap-1.5 rounded-xl bg-black/60 hover:bg-black/80 backdrop-blur px-3 py-1.5 text-xs text-white/80 hover:text-white transition-all border border-white/10 hover:border-white/20"
                onClick={(e) => e.stopPropagation()}
              >
                <Download size={12} /> Save
              </a>
            </motion.div>
          ) : (
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ delay: 0.15 }}
              className="rounded-2xl overflow-hidden border border-white/10"
              style={{ boxShadow: "0 0 40px rgba(6,182,212,0.25)" }}
            >
              <video src={job.output_url} controls className="w-full" />
            </motion.div>
          )}

          {/* Quality score */}
          {job.quality_score != null && (
            <div className="flex items-center justify-between text-xs text-white/35">
              <div className="flex items-center gap-2">
                <div className="flex gap-0.5">
                  {Array.from({ length: 10 }).map((_, i) => (
                    <motion.div
                      key={i}
                      initial={{ scale: 0 }}
                      animate={{ scale: 1 }}
                      transition={{ delay: 0.3 + i * 0.04, type: "spring", stiffness: 400 }}
                      className={cn(
                        "w-1.5 h-1.5 rounded-full",
                        i < Math.round(job.quality_score ?? 0) ? "bg-violet-400" : "bg-white/10",
                      )}
                    />
                  ))}
                </div>
                <span className="text-white/50 font-medium">{job.quality_score.toFixed(1)}/10</span>
              </div>
              {job.model_id && (
                <span className="truncate max-w-[45%] text-white/25">{job.model_id}</span>
              )}
            </div>
          )}
        </div>
      )}

      {/* ── Error ── */}
      {job.status === "failed" && job.error_message && (
        <div className="px-6 pb-6">
          <div className="rounded-xl bg-red-500/10 border border-red-500/20 px-4 py-3">
            <p className="text-xs text-red-400 leading-relaxed">{job.error_message}</p>
          </div>
        </div>
      )}

      {/* ── Cancelled ── */}
      {job.status === "cancelled" && (
        <div className="px-6 pb-6">
          <div className="rounded-xl bg-zinc-500/10 border border-zinc-500/20 px-4 py-3">
            <p className="text-xs text-zinc-400">Job was cancelled.</p>
          </div>
        </div>
      )}

      {/* ── Enhanced prompt collapsible ── */}
      {job.enhanced_prompt && (
        <details className="group border-t border-white/5">
          <summary className="px-6 py-3 text-xs text-white/25 cursor-pointer hover:text-white/45 transition-colors select-none list-none flex items-center gap-2">
            <span className="group-open:rotate-90 transition-transform inline-block">›</span>
            View enhanced prompt
          </summary>
          <p className="px-6 pb-4 text-xs text-white/40 italic leading-relaxed">{job.enhanced_prompt}</p>
        </details>
      )}
    </motion.div>
  );
}
