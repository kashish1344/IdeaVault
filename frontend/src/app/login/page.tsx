"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Eye, EyeOff, Loader2, Lock, Mail, Sparkles, User } from "lucide-react";
import { authApi } from "../../lib/api";

export default function LoginPage() {
  const router = useRouter();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [showPass, setShowPass] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError("");
    try {
      if (mode === "register") {
        await authApi.register({ email, username, password });
      }
      const res = await authApi.login(email, password);
      localStorage.setItem("nc_token", res.data.access_token);
      router.push("/generate");
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setError(typeof msg === "string" ? msg : "Something went wrong. Try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="relative min-h-screen bg-space flex items-center justify-center px-4 overflow-hidden">

      {/* Orbs */}
      <div className="pointer-events-none fixed inset-0">
        <div className="orb w-[600px] h-[600px] bg-violet-600/25 top-[-150px] left-[-150px] animate-float-a" />
        <div className="orb w-[500px] h-[500px] bg-cyan-500/15 bottom-[-100px] right-[-100px] animate-float-b" />
        <div className="orb w-[300px] h-[300px] bg-pink-500/12 top-[50%] right-[30%] animate-float-c" />
      </div>
      <div className="pointer-events-none fixed inset-0 grid-bg opacity-50" />

      {/* Card */}
      <div className="relative z-10 w-full max-w-md animate-appear">
        <div className="glass-md rounded-3xl p-8 border-glow">

          {/* Logo */}
          <div className="text-center mb-8">
            <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-gradient-to-br from-violet-600 to-cyan-500 mb-4 glow-violet">
              <Sparkles size={28} className="text-white" />
            </div>
            <h1 className="text-2xl font-black">
              Idea<span className="text-gradient">Vault</span>
            </h1>
            <p className="text-white/35 text-sm mt-1.5">
              {mode === "login" ? "Welcome back, creator" : "Join the AI revolution"}
            </p>
          </div>

          {/* Mode toggle */}
          <div className="flex rounded-xl overflow-hidden border border-white/10 bg-white/5 p-1 gap-1 mb-6">
            {(["login", "register"] as const).map(m => (
              <button key={m} type="button" onClick={() => { setMode(m); setError(""); }}
                className={`flex-1 py-2.5 rounded-lg text-sm font-semibold transition-all ${
                  mode === m
                    ? "bg-gradient-to-r from-violet-600 to-violet-500 text-white shadow-lg"
                    : "text-white/40 hover:text-white/70"
                }`}>
                {m === "login" ? "Sign In" : "Register"}
              </button>
            ))}
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            {/* Email */}
            <div className="relative">
              <Mail size={16} className="absolute left-4 top-1/2 -translate-y-1/2 text-white/30 pointer-events-none" />
              <input type="email" placeholder="Email address" value={email}
                onChange={e => setEmail(e.target.value)} required
                className="input-neon w-full rounded-xl pl-11 pr-4 py-3.5 text-sm" />
            </div>

            {/* Username (register only) */}
            {mode === "register" && (
              <div className="relative">
                <User size={16} className="absolute left-4 top-1/2 -translate-y-1/2 text-white/30 pointer-events-none" />
                <input type="text" placeholder="Username" value={username}
                  onChange={e => setUsername(e.target.value)} required minLength={3}
                  pattern="[a-zA-Z0-9_-]+"
                  className="input-neon w-full rounded-xl pl-11 pr-4 py-3.5 text-sm" />
              </div>
            )}

            {/* Password */}
            <div className="relative">
              <Lock size={16} className="absolute left-4 top-1/2 -translate-y-1/2 text-white/30 pointer-events-none" />
              <input type={showPass ? "text" : "password"} placeholder="Password" value={password}
                onChange={e => setPassword(e.target.value)} required minLength={8}
                className="input-neon w-full rounded-xl pl-11 pr-12 py-3.5 text-sm" />
              <button type="button" onClick={() => setShowPass(!showPass)}
                className="absolute right-4 top-1/2 -translate-y-1/2 text-white/30 hover:text-white/60 transition-colors">
                {showPass ? <EyeOff size={16} /> : <Eye size={16} />}
              </button>
            </div>

            {/* Error */}
            {error && (
              <div className="rounded-xl bg-red-500/10 border border-red-500/20 px-4 py-3 flex items-center gap-2">
                <span className="text-red-400">⚠</span>
                <p className="text-sm text-red-400">{error}</p>
              </div>
            )}

            {/* Submit */}
            <button type="submit" disabled={loading}
              className="btn-cta w-full flex items-center justify-center gap-2.5 rounded-2xl py-4 text-sm mt-2 disabled:opacity-50 disabled:cursor-not-allowed">
              {loading ? <Loader2 size={18} className="animate-spin" /> : <Sparkles size={18} />}
              {loading ? "Please wait…" : mode === "login" ? "Enter the Vault" : "Create Account"}
            </button>
          </form>

          <p className="text-center text-sm text-white/35 mt-6">
            {mode === "login" ? "No account?" : "Already a creator?"}{" "}
            <button type="button" onClick={() => { setMode(mode === "login" ? "register" : "login"); setError(""); }}
              className="text-violet-400 hover:text-violet-300 font-semibold transition-colors">
              {mode === "login" ? "Register free" : "Sign in"}
            </button>
          </p>

          <div className="flex items-center justify-center gap-6 mt-6 pt-6 border-t border-white/5">
            {["100% Local", "MIT License", "No API Keys"].map(b => (
              <span key={b} className="text-xs text-white/25">{b}</span>
            ))}
          </div>
        </div>
      </div>
    </main>
  );
}
