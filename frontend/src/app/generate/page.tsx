"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { Images, LogOut, Sparkles, Wand2 } from "lucide-react";
import { GenerateForm } from "../../components/forms/GenerateForm";
import { JobStatusCard } from "../../components/ui/JobStatusCard";
import type { Job } from "../../lib/api";

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export default function GeneratePage() {
  const router = useRouter();
  const [activeJob, setActiveJob] = useState<{ id: string; estimated: number } | null>(null);
  const [completedJob, setCompletedJob] = useState<Job | null>(null);

  // ── Auth guard ──────────────────────────────────────────────────
  useEffect(() => {
    if (!localStorage.getItem("nc_token")) router.replace("/login");
  }, [router]);

  // ── Cancel on tab close (keepalive fetch survives page unload) ──
  const activeJobRef = useRef(activeJob);
  activeJobRef.current = activeJob;

  useEffect(() => {
    const handleUnload = () => {
      const job = activeJobRef.current;
      if (!job) return;
      const token = localStorage.getItem("nc_token");
      if (!token) return;
      // Keep-alive flag ensures the request completes after page unload
      fetch(`${BASE_URL}/api/v1/jobs/${job.id}`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${token}` },
        keepalive: true,
      });
    };
    window.addEventListener("beforeunload", handleUnload);
    return () => window.removeEventListener("beforeunload", handleUnload);
  }, []);

  const logout = () => {
    localStorage.removeItem("nc_token");
    router.push("/login");
  };

  const handleJobQueued = (jobId: string, estimated: number) => {
    setCompletedJob(null);
    setActiveJob({ id: jobId, estimated });
  };

  const handleCancel = () => {
    setActiveJob(null);
    setCompletedJob(null);
  };

  return (
    <main className="relative min-h-screen bg-space overflow-hidden">

      {/* Background orbs */}
      <div className="pointer-events-none fixed inset-0">
        <div className="orb w-[500px] h-[500px] bg-violet-600/20 top-[-100px] left-[-100px] animate-float-a" />
        <div className="orb w-[400px] h-[400px] bg-cyan-500/10 bottom-[-100px] right-[-100px] animate-float-b" />
        <div className="orb w-[300px] h-[300px] bg-pink-500/8 top-[60%] left-[40%] animate-float-c" />
      </div>
      <div className="pointer-events-none fixed inset-0 dot-grid opacity-40" />

      {/* Top Nav */}
      <nav className="relative z-20 flex items-center justify-between px-6 py-4 border-b border-white/5 glass">
        <Link href="/" className="flex items-center gap-2">
          <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-violet-500 to-cyan-500 flex items-center justify-center">
            <Sparkles size={13} className="text-white" />
          </div>
          <span className="font-bold text-sm">
            Idea<span className="text-gradient">Vault</span>
          </span>
        </Link>

        <div className="flex items-center gap-2">
          <Link
            href="/gallery"
            className="flex items-center gap-1.5 text-sm text-white/40 hover:text-white px-3 py-2 rounded-xl hover:bg-white/5 transition-all"
          >
            <Images size={15} /> Gallery
          </Link>
          <button
            type="button"
            onClick={logout}
            className="flex items-center gap-1.5 text-sm text-white/40 hover:text-red-400 px-3 py-2 rounded-xl hover:bg-red-500/10 transition-all"
          >
            <LogOut size={15} /> Logout
          </button>
        </div>
      </nav>

      {/* Main layout */}
      <div className="relative z-10 flex h-[calc(100vh-61px)]">

        {/* Left: Form sidebar */}
        <aside className="w-full md:w-[420px] flex-shrink-0 border-r border-white/5 flex flex-col overflow-y-auto">
          <div className="px-6 pt-6 pb-4">
            <div className="flex items-center gap-3 mb-1">
              <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-violet-600 to-cyan-500 flex items-center justify-center glow-violet">
                <Wand2 size={17} className="text-white" />
              </div>
              <div>
                <h1 className="font-bold text-base">AI Studio</h1>
                <p className="text-xs text-white/30">Describe your vision</p>
              </div>
            </div>
          </div>

          <div className="px-6 pb-6 flex-1">
            <GenerateForm onJobQueued={handleJobQueued} />
          </div>
        </aside>

        {/* Right: Output canvas */}
        <section className="flex-1 flex flex-col overflow-hidden">
          <div className="px-8 py-4 border-b border-white/5 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
              <span className="text-sm text-white/50 font-medium">Output Canvas</span>
            </div>
            {completedJob?.output_url && (
              <a
                href={completedJob.output_url}
                download
                className="text-xs text-violet-400 hover:text-violet-300 border border-violet-500/30 hover:border-violet-400/50 px-3 py-1.5 rounded-lg transition-all"
              >
                Download
              </a>
            )}
          </div>

          <div className="flex-1 overflow-y-auto p-8">
            {activeJob ? (
              <div className="max-w-2xl mx-auto">
                <JobStatusCard
                  jobId={activeJob.id}
                  estimatedSeconds={activeJob.estimated}
                  onComplete={setCompletedJob}
                  onCancel={handleCancel}
                />
              </div>
            ) : (
              /* Empty canvas state */
              <div className="h-full flex flex-col items-center justify-center gap-6 text-center">
                <div className="relative">
                  <div className="absolute inset-0 rounded-full border border-violet-500/20 animate-ping" />
                  <div className="absolute -inset-4 rounded-full border border-cyan-500/10 animate-spin-slow" />
                  <div className="w-24 h-24 rounded-3xl border-2 border-dashed border-white/10 flex items-center justify-center glass">
                    <span className="text-4xl select-none">🎨</span>
                  </div>
                </div>
                <div className="space-y-2">
                  <p className="text-white/50 font-medium">Canvas is ready</p>
                  <p className="text-sm text-white/25">Describe your vision on the left and hit Generate</p>
                </div>
                <div className="flex flex-wrap justify-center gap-2 mt-2 max-w-sm">
                  {[
                    "a neon city at night",
                    "astronaut on Mars",
                    "cyberpunk samurai",
                    "ocean waves at sunset",
                  ].map((hint) => (
                    <span key={hint} className="text-xs px-3 py-1.5 rounded-full glass text-white/35 border border-white/5">
                      {hint}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>
        </section>
      </div>
    </main>
  );
}
