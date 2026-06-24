"use client";

import { AnimatePresence, motion } from "framer-motion";
import { useState } from "react";
import { Download, Play, Star, X, ZoomIn } from "lucide-react";
import * as Dialog from "@radix-ui/react-dialog";
import type { Job } from "../../lib/api";
import { cn, formatRelativeTime } from "../../lib/utils";

interface Props {
  job: Job;
  index?: number;
}

export function MediaCard({ job, index = 0 }: Props) {
  if (job.status !== "completed" || !job.output_url) return null;

  const [open, setOpen] = useState(false);
  const isVideo = job.media_type === "video";

  return (
    <>
      {/* Card */}
      <motion.div
        initial={{ opacity: 0, scale: 0.95, y: 8 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        transition={{ delay: Math.min(index * 0.04, 0.4), type: "spring", stiffness: 300, damping: 28 }}
        className="group relative rounded-2xl overflow-hidden border border-white/10 bg-zinc-900 hover:border-violet-500/40 transition-all duration-300 cursor-pointer"
        onClick={() => setOpen(true)}
      >
        {/* Media */}
        <div className="aspect-square relative overflow-hidden">
          {isVideo ? (
            <video
              src={job.output_url}
              className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"
              muted
              loop
              playsInline
              onMouseEnter={(e) => (e.currentTarget as HTMLVideoElement).play()}
              onMouseLeave={(e) => (e.currentTarget as HTMLVideoElement).pause()}
            />
          ) : (
            <img
              src={job.output_url}
              alt={job.raw_prompt}
              className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"
              loading="lazy"
            />
          )}

          {/* Hover overlay */}
          <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-black/20 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300">
            <div className="absolute inset-0 flex items-center justify-center">
              <div className="w-10 h-10 rounded-full bg-white/15 backdrop-blur border border-white/20 flex items-center justify-center">
                <ZoomIn size={16} className="text-white" />
              </div>
            </div>
            <div className="absolute bottom-3 left-3 right-3 flex justify-between items-end">
              <a
                href={job.output_url}
                download
                className="rounded-lg bg-white/10 hover:bg-white/20 backdrop-blur p-2 transition-colors"
                aria-label="Download"
                onClick={(e) => e.stopPropagation()}
              >
                <Download size={13} className="text-white" />
              </a>
              {isVideo && (
                <span className="rounded-lg bg-violet-600/80 backdrop-blur px-2 py-1 flex items-center gap-1">
                  <Play size={9} className="text-white" fill="white" />
                  <span className="text-white text-xs font-medium">Video</span>
                </span>
              )}
            </div>
          </div>

          {/* Quality badge */}
          {job.quality_score != null && (
            <div className="absolute top-2 right-2 rounded-full bg-black/60 backdrop-blur flex items-center gap-1 px-2 py-0.5 border border-white/10">
              <Star size={9} className="text-amber-400 fill-amber-400" />
              <span className="text-white text-xs font-medium">{job.quality_score.toFixed(1)}</span>
            </div>
          )}
        </div>

        {/* Info */}
        <div className="p-3 space-y-1">
          <p className="text-xs text-white/70 line-clamp-2 leading-relaxed">{job.raw_prompt}</p>
          <div className="flex items-center justify-between">
            <span className="text-xs text-white/30">{formatRelativeTime(job.created_at)}</span>
            <span
              className={cn(
                "text-xs px-2 py-0.5 rounded-full",
                job.quality_preset === "ultra"    && "bg-violet-500/20 text-violet-400",
                job.quality_preset === "standard" && "bg-blue-500/20 text-blue-400",
                job.quality_preset === "draft"    && "bg-white/10 text-white/40",
              )}
            >
              {job.quality_preset}
            </span>
          </div>
        </div>
      </motion.div>

      {/* Lightbox */}
      <Dialog.Root open={open} onOpenChange={setOpen}>
        <Dialog.Portal>
          <Dialog.Overlay asChild>
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="fixed inset-0 z-50 bg-black/85 backdrop-blur-md"
            />
          </Dialog.Overlay>

          <Dialog.Content
            className="fixed inset-0 z-50 flex items-center justify-center p-4 md:p-8"
            aria-describedby={undefined}
          >
            <Dialog.Title className="sr-only">{job.raw_prompt}</Dialog.Title>

            <AnimatePresence>
              {open && (
                <motion.div
                  initial={{ opacity: 0, scale: 0.92, y: 20 }}
                  animate={{ opacity: 1, scale: 1, y: 0 }}
                  exit={{ opacity: 0, scale: 0.92, y: 20 }}
                  transition={{ type: "spring", stiffness: 300, damping: 28 }}
                  className="relative max-w-4xl w-full max-h-[90vh] flex flex-col glass rounded-3xl overflow-hidden border border-white/10"
                  style={{ boxShadow: "0 0 80px rgba(139,92,246,0.2), 0 40px 80px rgba(0,0,0,0.6)" }}
                >
                  {/* Close button */}
                  <Dialog.Close asChild>
                    <button
                      type="button"
                      aria-label="Close lightbox"
                      className="absolute top-4 right-4 z-10 w-9 h-9 rounded-xl bg-black/60 backdrop-blur border border-white/15 flex items-center justify-center text-white/60 hover:text-white hover:bg-black/80 transition-all"
                    >
                      <X size={16} />
                    </button>
                  </Dialog.Close>

                  {/* Media */}
                  <div className="flex-1 overflow-hidden min-h-0">
                    {isVideo ? (
                      <video
                        src={job.output_url!}
                        controls
                        autoPlay
                        className="w-full h-full object-contain bg-black"
                      />
                    ) : (
                      <img
                        src={job.output_url!}
                        alt={job.raw_prompt}
                        className="w-full h-full object-contain bg-black"
                      />
                    )}
                  </div>

                  {/* Footer info */}
                  <div className="px-6 py-4 border-t border-white/5 flex items-center justify-between gap-4">
                    <div className="min-w-0 flex-1">
                      <p className="text-sm text-white/70 line-clamp-1">{job.raw_prompt}</p>
                      <div className="flex items-center gap-3 mt-1">
                        {job.quality_score != null && (
                          <span className="flex items-center gap-1 text-xs text-amber-400">
                            <Star size={11} className="fill-amber-400" />
                            {job.quality_score.toFixed(1)}/10
                          </span>
                        )}
                        <span className="text-xs text-white/30">{formatRelativeTime(job.created_at)}</span>
                        {job.model_id && (
                          <span className="text-xs text-white/25 truncate max-w-[120px]">{job.model_id}</span>
                        )}
                      </div>
                    </div>
                    <a
                      href={job.output_url!}
                      download
                      className="flex items-center gap-2 text-sm text-white/70 hover:text-white border border-white/15 hover:border-white/30 px-4 py-2 rounded-xl transition-all flex-shrink-0"
                    >
                      <Download size={14} /> Download
                    </a>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </Dialog.Content>
        </Dialog.Portal>
      </Dialog.Root>
    </>
  );
}
