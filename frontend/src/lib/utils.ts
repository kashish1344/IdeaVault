import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs));
}

export function formatRelativeTime(dateStr: string): string {
  const now = Date.now();
  const then = new Date(dateStr).getTime();
  const diff = Math.floor((now - then) / 1000);
  if (diff < 60) return `${diff}s ago`;
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  return `${Math.floor(diff / 86400)}d ago`;
}

export function estimatedProgress(
  status: string,
  createdAt: string,
  estimatedSeconds = 30,
  startedAt?: string,
): number {
  if (status === "completed") return 100;
  if (status === "failed" || status === "cancelled") return 0;
  if (status === "queued") {
    // Slowly creep 2 → 8 % while waiting in queue (0.5 %/s), never goes backwards
    const elapsed = (Date.now() - new Date(createdAt).getTime()) / 1000;
    return Math.min(8, 2 + Math.floor(elapsed * 0.5));
  }
  // processing: linear 10 → 95 % over estimatedSeconds
  // Starts at 10 % so the bar never goes backwards after the queued phase
  const base = startedAt ?? createdAt;
  const elapsed = (Date.now() - new Date(base).getTime()) / 1000;
  return Math.min(95, 10 + Math.floor((elapsed / estimatedSeconds) * 85));
}
