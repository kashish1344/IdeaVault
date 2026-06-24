"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useCallback, useEffect, useRef, useState } from "react";
import { generateApi, type GeneratePayload, type Job, jobsApi } from "../lib/api";

// ── Cancel job ────────────────────────────────────────────────────────────────

export function useCancelJob(jobId: string | null) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => jobsApi.cancel(jobId!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["job", jobId] });
      queryClient.invalidateQueries({ queryKey: ["jobs"] });
    },
  });
}

// ── Generate mutation ─────────────────────────────────────────────────────────

export function useGenerateImage() {
  return useMutation({
    mutationFn: (payload: GeneratePayload) => generateApi.image(payload),
  });
}

export function useGenerateVideo() {
  return useMutation({
    mutationFn: (payload: GeneratePayload) => generateApi.video(payload),
  });
}

// ── Poll job status until terminal state ──────────────────────────────────────

const TERMINAL = new Set(["completed", "failed", "cancelled"]);

export function useJobPoller(jobId: string | null) {
  const queryClient = useQueryClient();

  return useQuery({
    queryKey: ["job", jobId],
    queryFn: async () => {
      const res = await jobsApi.get(jobId!);
      return res.data;
    },
    enabled: !!jobId,
    refetchInterval: (query) => {
      const data = query.state.data as Job | undefined;
      if (!data || TERMINAL.has(data.status)) return false;
      return data.status === "processing" ? 2000 : 3000;
    },
    staleTime: 0,
  });
}

// ── Job list ──────────────────────────────────────────────────────────────────

export function useJobs(limit = 20) {
  return useQuery({
    queryKey: ["jobs", limit],
    queryFn: async () => {
      const res = await jobsApi.list(limit);
      return res.data;
    },
    refetchInterval: 10_000,
    staleTime: 5_000,
  });
}

// ── Autocomplete with debounce ────────────────────────────────────────────────

export function useAutocomplete(prefix: string, debounceMs = 250) {
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (prefix.length < 2) {
      setSuggestions([]);
      return;
    }
    if (timerRef.current) clearTimeout(timerRef.current);
    timerRef.current = setTimeout(async () => {
      try {
        const res = await generateApi.autocomplete(prefix);
        setSuggestions(res.data.suggestions);
      } catch {
        setSuggestions([]);
      }
    }, debounceMs);

    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, [prefix, debounceMs]);

  return suggestions;
}

// ── Studio state (Zustand-like inline store) ──────────────────────────────────

export interface StudioState {
  activeJobId: string | null;
  mediaType: "image" | "video";
  qualityPreset: "draft" | "standard" | "ultra";
  styleHints: string[];
}

export function useStudioState() {
  const [state, setState] = useState<StudioState>({
    activeJobId: null,
    mediaType: "image",
    qualityPreset: "standard",
    styleHints: [],
  });

  const update = useCallback(
    (patch: Partial<StudioState>) => setState((s) => ({ ...s, ...patch })),
    []
  );

  return { state, update };
}
