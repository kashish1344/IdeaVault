import axios, { type AxiosInstance } from "axios";

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

function createApiClient(): AxiosInstance {
  const client = axios.create({
    baseURL: `${BASE_URL}/api/v1`,
    headers: { "Content-Type": "application/json" },
    timeout: 15_000,
  });

  // Attach JWT from localStorage on every request
  client.interceptors.request.use((config) => {
    if (typeof window !== "undefined") {
      const token = localStorage.getItem("nc_token");
      if (token) config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  });

  // Redirect to login on 401
  client.interceptors.response.use(
    (res) => res,
    (err) => {
      if (err.response?.status === 401 && typeof window !== "undefined") {
        localStorage.removeItem("nc_token");
        window.location.href = "/login";
      }
      return Promise.reject(err);
    }
  );

  return client;
}

export const api = createApiClient();

// ── Auth ──────────────────────────────────────────────────────────────────────

export interface RegisterPayload {
  email: string;
  username: string;
  password: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
}

export const authApi = {
  register: (data: RegisterPayload) =>
    api.post<TokenResponse>("/auth/register", data),

  login: (email: string, password: string) => {
    const form = new URLSearchParams({ username: email, password });
    return api.post<TokenResponse>("/auth/token", form, {
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
    });
  },

  me: () => api.get("/auth/me"),
};

// ── Generation ────────────────────────────────────────────────────────────────

export interface GeneratePayload {
  prompt: string;
  media_type: "image" | "video";
  quality_preset: "draft" | "standard" | "ultra";
  style_hints?: string[];
  priority?: 0 | 1 | 2 | 3;
  duration_seconds?: number; // video only, 2–8
}

export interface GenerateResponse {
  job_id: string;
  status: string;
  message: string;
  estimated_seconds?: number;
}

export interface Job {
  job_id: string;
  status: "queued" | "processing" | "completed" | "failed" | "cancelled";
  media_type: string;
  raw_prompt: string;
  quality_preset: string;
  created_at: string;
  started_at?: string;
  completed_at?: string;
  output_url?: string;
  thumbnail_url?: string;
  enhanced_prompt?: string;
  model_id?: string;
  quality_score?: number;
  error_message?: string;
  current_step?: string;
}

export const generateApi = {
  image: (data: GeneratePayload) =>
    api.post<GenerateResponse>("/generate/image", data),

  video: (data: GeneratePayload) =>
    api.post<GenerateResponse>("/generate/video", data),

  autocomplete: (prefix: string, limit = 10) =>
    api.get<{ prefix: string; suggestions: string[] }>("/generate/autocomplete", {
      params: { prefix, limit },
    }),
};

export const jobsApi = {
  get: (jobId: string) => api.get<Job>(`/jobs/${jobId}`),
  list: (limit = 20, offset = 0) =>
    api.get<Job[]>("/jobs/", { params: { limit, offset } }),
  cancel: (jobId: string) => api.delete(`/jobs/${jobId}`),
};
