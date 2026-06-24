"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { AnimatePresence, motion } from "framer-motion";
import { ImageIcon, Loader2, Sparkles, Video, Wand2, X } from "lucide-react";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { useAutocomplete, useGenerateImage, useGenerateVideo } from "../../hooks/useGeneration";
import { cn } from "../../lib/utils";

const schema = z.object({
  prompt: z.string().min(3).max(2000),
  media_type: z.enum(["image", "video"]),
  quality_preset: z.enum(["draft", "standard", "ultra"]),
  style_hints: z.array(z.string()).max(10),
  duration_seconds: z.number().int().min(2).max(8),
});

type FormData = z.infer<typeof schema>;

interface Props { onJobQueued: (jobId: string, estimated: number) => void; }

// Quality preset: label / gen time description / model note
const QUALITY = [
  {
    value: "draft",
    label: "Draft",
    genTime: "~10s",
    desc: "Fast, lower detail",
    color: "text-emerald-400",
    dot: "bg-emerald-400",
  },
  {
    value: "standard",
    label: "Standard",
    genTime: "~30s",
    desc: "Balanced quality",
    color: "text-violet-400",
    dot: "bg-violet-400",
  },
  {
    value: "ultra",
    label: "Ultra",
    genTime: "~90s",
    desc: "Best quality, slow",
    color: "text-pink-400",
    dot: "bg-pink-400",
  },
] as const;

// Video duration options (seconds). num_frames = duration * 8fps, capped by model.
// modelscope max 24 frames → 3 s cap. zeroscope max 36 frames → 4 s cap for standard,
// user sees actual cap when playing back. We still let them pick up to 8 s and
// the backend clamps gracefully.
const DURATIONS = [2, 4, 6, 8] as const;

export function GenerateForm({ onJobQueued }: Props) {
  const [styleInput, setStyleInput] = useState("");
  const [showSuggestions, setShowSuggestions] = useState(false);

  const imageMutation = useGenerateImage();
  const videoMutation = useGenerateVideo();
  const isLoading = imageMutation.isPending || videoMutation.isPending;

  const { register, handleSubmit, watch, setValue, formState: { errors } } = useForm<FormData>({
    resolver: zodResolver(schema),
    defaultValues: {
      media_type: "image",
      quality_preset: "standard",
      style_hints: [],
      duration_seconds: 4,
    },
  });

  const promptValue = watch("prompt") ?? "";
  const suggestions = useAutocomplete(promptValue);
  const styleHints = watch("style_hints") ?? [];
  const mediaType = watch("media_type");
  const quality = watch("quality_preset");
  const duration = watch("duration_seconds");

  const onSubmit = async (data: FormData) => {
    const mutate = data.media_type === "video" ? videoMutation.mutateAsync : imageMutation.mutateAsync;
    try {
      const payload = {
        ...data,
        duration_seconds: data.media_type === "video" ? data.duration_seconds : undefined,
      };
      const res = await mutate(payload);
      onJobQueued(res.data.job_id, res.data.estimated_seconds ?? 30);
    } catch { /* errors rendered below */ }
  };

  const addStyleHint = (hint: string) => {
    const cleaned = hint.trim().toLowerCase();
    if (cleaned && !styleHints.includes(cleaned) && styleHints.length < 10) {
      setValue("style_hints", [...styleHints, cleaned]);
    }
    setStyleInput("");
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-5">

      {/* Media type */}
      <div className="flex rounded-2xl overflow-hidden border border-white/10 bg-white/5 p-1 gap-1">
        {(["image", "video"] as const).map(type => (
          <button
            key={type}
            type="button"
            onClick={() => setValue("media_type", type)}
            className={cn(
              "flex-1 flex items-center justify-center gap-2 py-3 rounded-xl text-sm font-semibold transition-all",
              mediaType === type
                ? "bg-gradient-to-r from-violet-600 to-violet-500 text-white shadow-lg glow-violet"
                : "text-white/40 hover:text-white/70 hover:bg-white/5"
            )}
          >
            {type === "image" ? <ImageIcon size={16} /> : <Video size={16} />}
            {type.charAt(0).toUpperCase() + type.slice(1)}
          </button>
        ))}
      </div>

      {/* Prompt */}
      <div className="relative">
        <div className={cn(
          "flex items-start gap-3 rounded-2xl p-4 transition-all border",
          "bg-white/4 border-white/10 focus-within:border-violet-500/60 focus-within:bg-violet-500/5"
        )}>
          <Sparkles size={18} className="text-violet-400 mt-0.5 shrink-0 animate-pulse" />
          <textarea
            {...register("prompt")}
            placeholder="Describe what you want to create…"
            rows={4}
            className="flex-1 bg-transparent text-white placeholder:text-white/25 resize-none outline-none text-sm leading-relaxed"
            onFocus={() => setShowSuggestions(true)}
            onBlur={() => setTimeout(() => setShowSuggestions(false), 150)}
          />
        </div>

        <AnimatePresence>
          {showSuggestions && suggestions.length > 0 && (
            <motion.div
              initial={{ opacity: 0, y: -4 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -4 }}
              className="absolute z-20 top-full mt-2 w-full rounded-2xl border border-white/10 glass overflow-hidden shadow-2xl"
            >
              <ul>
                {suggestions.map(s => (
                  <li
                    key={s}
                    onMouseDown={() => setValue("prompt", s)}
                    className="px-4 py-3 text-sm text-white/60 hover:bg-violet-600/20 hover:text-white cursor-pointer transition-colors border-b border-white/5 last:border-0"
                  >
                    {s}
                  </li>
                ))}
              </ul>
            </motion.div>
          )}
        </AnimatePresence>
        {errors.prompt && <p className="mt-1.5 text-xs text-red-400 pl-1">{errors.prompt.message}</p>}
      </div>

      {/* Quality preset */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <label className="text-xs text-white/30 uppercase tracking-widest font-semibold">Quality</label>
          <span className="text-xs text-white/20">generation speed</span>
        </div>
        <div className="grid grid-cols-3 gap-2">
          {QUALITY.map(({ value, label, genTime, desc, color, dot }) => (
            <button
              key={value}
              type="button"
              onClick={() => setValue("quality_preset", value)}
              className={cn(
                "rounded-2xl py-3 px-2 text-center border transition-all",
                quality === value
                  ? "border-violet-500/60 bg-violet-500/15 shadow-lg"
                  : "border-white/8 bg-white/4 hover:bg-white/8 hover:border-white/15"
              )}
            >
              <div className="flex items-center justify-center gap-1.5 mb-0.5">
                <span className={cn("w-1.5 h-1.5 rounded-full", quality === value ? dot : "bg-white/20")} />
                <span className={cn("text-sm font-bold", quality === value ? color : "text-white/40")}>{label}</span>
              </div>
              <div className="text-xs text-white/20 font-medium">{genTime}</div>
              <div className="text-xs text-white/15 mt-0.5 hidden sm:block">{desc}</div>
            </button>
          ))}
        </div>
      </div>

      {/* Video duration — only shown for video */}
      <AnimatePresence>
        {mediaType === "video" && (
          <motion.div
            key="duration"
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            className="overflow-hidden"
          >
            <div className="flex items-center justify-between mb-3">
              <label className="text-xs text-white/30 uppercase tracking-widest font-semibold">
                Video Duration
              </label>
              <span className="text-xs text-violet-400 font-semibold">{duration}s</span>
            </div>
            <div className="grid grid-cols-4 gap-2">
              {DURATIONS.map(d => (
                <button
                  key={d}
                  type="button"
                  onClick={() => setValue("duration_seconds", d)}
                  className={cn(
                    "rounded-xl py-2.5 text-sm font-semibold border transition-all",
                    duration === d
                      ? "border-cyan-500/60 bg-cyan-500/15 text-cyan-400"
                      : "border-white/8 bg-white/4 text-white/35 hover:bg-white/8 hover:text-white/60"
                  )}
                >
                  {d}s
                </button>
              ))}
            </div>
            <p className="mt-2 text-xs text-white/20 leading-relaxed">
              Actual clip length depends on the model — draft caps at 3 s, ultra at 4.5 s.
              Longer = slower generation.
            </p>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Style hints */}
      <div>
        <label className="text-xs text-white/30 uppercase tracking-widest font-semibold mb-3 block">Style Hints</label>
        {styleHints.length > 0 && (
          <div className="flex gap-2 flex-wrap mb-2">
            {styleHints.map(h => (
              <span key={h} className="flex items-center gap-1 rounded-full bg-violet-600/20 border border-violet-500/30 text-violet-300 text-xs px-3 py-1">
                {h}
                <button
                  type="button"
                  aria-label={`Remove ${h}`}
                  onClick={() => setValue("style_hints", styleHints.filter(x => x !== h))}
                >
                  <X size={10} />
                </button>
              </span>
            ))}
          </div>
        )}
        <input
          value={styleInput}
          onChange={e => setStyleInput(e.target.value)}
          onKeyDown={e => {
            if (e.key === "Enter" || e.key === ",") {
              e.preventDefault();
              addStyleHint(styleInput);
            }
          }}
          placeholder="cinematic, anime, oil painting… (Enter to add)"
          className="input-neon w-full rounded-xl px-4 py-2.5 text-sm"
        />
      </div>

      {/* Error */}
      {(imageMutation.error || videoMutation.error) && (
        <div className="rounded-xl bg-red-500/10 border border-red-500/20 px-4 py-3">
          <p className="text-sm text-red-400">Generation failed — please try again.</p>
        </div>
      )}

      {/* Submit */}
      <motion.button
        type="submit"
        disabled={isLoading}
        whileTap={{ scale: 0.98 }}
        className="btn-cta w-full flex items-center justify-center gap-2.5 rounded-2xl py-4 text-sm disabled:opacity-50 disabled:cursor-not-allowed"
      >
        {isLoading ? <Loader2 size={18} className="animate-spin" /> : <Wand2 size={18} />}
        {isLoading ? "Queueing…" : "Generate"}
      </motion.button>
    </form>
  );
}
