"use client";

import Link from "next/link";
import { motion } from "framer-motion";
import { ArrowLeft, Images, Loader2, Wand2 } from "lucide-react";
import { useJobs } from "../../hooks/useGeneration";
import { MediaCard } from "../../components/ui/MediaCard";

export default function GalleryPage() {
  const { data: jobs, isLoading } = useJobs(50);

  const completed = jobs?.filter((j) => j.status === "completed" && j.output_url) ?? [];
  const images = completed.filter((j) => j.media_type === "image");
  const videos = completed.filter((j) => j.media_type === "video");

  return (
    <main className="relative min-h-screen bg-space overflow-hidden">

      {/* Background */}
      <div className="pointer-events-none fixed inset-0">
        <div className="orb w-[600px] h-[600px] bg-violet-600/15 top-[-150px] right-[-150px] animate-float-b" />
        <div className="orb w-[400px] h-[400px] bg-cyan-500/10 bottom-[-100px] left-[-100px] animate-float-a" />
      </div>
      <div className="pointer-events-none fixed inset-0 dot-grid opacity-30" />

      {/* Nav */}
      <nav className="relative z-20 flex items-center justify-between px-6 md:px-10 py-4 border-b border-white/5 glass sticky top-0">
        <div className="flex items-center gap-4">
          <Link
            href="/"
            className="flex items-center gap-2 text-white/40 hover:text-white text-sm transition-colors"
          >
            <ArrowLeft size={15} />
            Home
          </Link>
          <div className="w-px h-4 bg-white/10" />
          <div className="flex items-center gap-2">
            <Images size={15} className="text-violet-400" />
            <h1 className="text-sm font-semibold text-white">
              Gallery
              {completed.length > 0 && (
                <span className="ml-2 text-xs font-normal text-white/30">
                  {completed.length} creation{completed.length !== 1 ? "s" : ""}
                </span>
              )}
            </h1>
          </div>
        </div>

        <Link
          href="/generate"
          className="flex items-center gap-1.5 text-sm btn-cta rounded-xl px-4 py-2"
        >
          <Wand2 size={14} /> Create
        </Link>
      </nav>

      <div className="relative z-10 max-w-7xl mx-auto px-6 md:px-10 py-8">

        {/* Loading */}
        {isLoading && (
          <div className="flex flex-col items-center justify-center py-32 gap-4">
            <Loader2 size={32} className="animate-spin text-violet-400/60" />
            <p className="text-sm text-white/30">Loading your creations…</p>
          </div>
        )}

        {/* Empty state */}
        {!isLoading && completed.length === 0 && (
          <motion.div
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            className="flex flex-col items-center justify-center py-32 gap-6 text-center"
          >
            <div className="relative">
              <div className="absolute inset-0 rounded-full border border-violet-500/20 animate-ping" />
              <div className="w-24 h-24 rounded-3xl border-2 border-dashed border-white/10 flex items-center justify-center glass text-4xl select-none">
                🖼
              </div>
            </div>
            <div className="space-y-2">
              <p className="text-white/50 font-medium">No creations yet</p>
              <p className="text-sm text-white/25 max-w-xs">
                Generate your first image or video to see it here.
              </p>
            </div>
            <Link
              href="/generate"
              className="btn-cta flex items-center gap-2 rounded-2xl px-6 py-3 text-sm"
            >
              <Wand2 size={16} /> Start Creating
            </Link>
          </motion.div>
        )}

        {/* Images section */}
        {!isLoading && images.length > 0 && (
          <section className="mb-10">
            {videos.length > 0 && (
              <div className="flex items-center gap-3 mb-5">
                <h2 className="text-xs font-semibold text-white/30 uppercase tracking-widest">Images</h2>
                <div className="flex-1 h-px bg-white/5" />
                <span className="text-xs text-white/20">{images.length}</span>
              </div>
            )}
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 xl:grid-cols-5 gap-3">
              {images.map((job, i) => (
                <MediaCard key={job.job_id} job={job} index={i} />
              ))}
            </div>
          </section>
        )}

        {/* Videos section */}
        {!isLoading && videos.length > 0 && (
          <section>
            <div className="flex items-center gap-3 mb-5">
              <h2 className="text-xs font-semibold text-white/30 uppercase tracking-widest">Videos</h2>
              <div className="flex-1 h-px bg-white/5" />
              <span className="text-xs text-white/20">{videos.length}</span>
            </div>
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-3">
              {videos.map((job, i) => (
                <MediaCard key={job.job_id} job={job} index={i} />
              ))}
            </div>
          </section>
        )}
      </div>
    </main>
  );
}
