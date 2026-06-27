"use client";

import { useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import CourtroomAtmosphere from "../../../components/ui/CourtroomAtmosphere";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function FilePage() {
  const router = useRouter();
  const [title, setTitle] = useState("");
  const [codeContent, setCodeContent] = useState("");
  const [filename, setFilename] = useState("");
  const [language, setLanguage] = useState("");
  const [focusArea, setFocusArea] = useState("");
  const [isDragging, setIsDragging] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState("");

  const handleFile = useCallback((file: File) => {
    setFilename(file.name);
    const reader = new FileReader();
    reader.onload = (e) => {
      const content = e.target?.result as string;
      setCodeContent(content);
      const ext = file.name.split(".").pop()?.toLowerCase() || "";
      const langMap: Record<string, string> = {
        py: "Python", js: "JavaScript", ts: "TypeScript", go: "Go",
        java: "Java", cpp: "C++", c: "C", cs: "C#", rb: "Ruby",
        php: "PHP", rs: "Rust", kt: "Kotlin", swift: "Swift",
      };
      setLanguage(langMap[ext] || "Unknown");
    };
    reader.readAsText(file);
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    const file = e.dataTransfer.files[0];
    if (file) handleFile(file);
  }, [handleFile]);

  const handleSubmit = async (e?: React.MouseEvent) => {
    if (e) e.preventDefault();
    if (!codeContent.trim()) {
      setError("You must present a scroll with code upon it.");
      return;
    }
    setIsSubmitting(true);
    setError("");

    const payload = {
      code_content: codeContent,
      language: language || "auto",
      focus_area: focusArea,
      title: title || `Case - ${filename || "Unknown Code"}`,
    };

    console.log("[FilePage] Submitting to /submit-session/:", {
      language: payload.language,
      contentLength: payload.code_content.length,
    });

    try {
      const res = await fetch(`${API_BASE}/submit-session/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        const text = await res.text();
        console.error("[FilePage] Server rejected filing:", res.status, text);
        throw new Error(`The tribunal scribe rejected your filing. (${res.status})`);
      }

      const data = await res.json();
      console.log("[FilePage] Response JSON:", JSON.stringify(data));

      if (!data.session_id) {
        throw new Error("Server returned no session_id — check backend logs.");
      }

      const targetUrl = `/courtroom?session_id=${encodeURIComponent(data.session_id)}&title=${encodeURIComponent(data.title || title)}`;
      console.log("[FilePage] Redirecting to:", targetUrl);
      router.push(targetUrl);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "An error occurred while filing the case.";
      console.error("[FilePage] Submit error:", msg);
      setError(msg);
      setIsSubmitting(false);
    }
  };

  const lineCount = codeContent ? codeContent.split("\n").length : 0;

  return (
    <main className="min-h-screen flex items-center justify-center px-4 py-12 relative overflow-hidden bg-bg-primary">
      {/* Atmosphere layer — behind the card */}
      <CourtroomAtmosphere />

      <div className="relative z-10 w-full max-w-[480px]">
        {/* Case number kicker */}
        <div className="flex items-center justify-center gap-3 mb-2 opacity-80">
          <div className="w-6 h-px bg-[#6b5a30]" />
          <span className="text-[9px] text-[#7a6a45] tracking-[0.3em] font-[family-name:var(--font-cinzel)]">
            CASE No. 0001
          </span>
          <div className="w-6 h-px bg-[#6b5a30]" />
        </div>

        {/* Card with gold top accent */}
        <div className="card-accent p-10 md:p-12 relative">
          {/* Corner bracket decorations */}
          <div className="absolute -top-px -left-px w-3.5 h-3.5 border-t border-l" style={{ borderColor: "var(--gold)" }} />
          <div className="absolute -top-px -right-px w-3.5 h-3.5 border-t border-r" style={{ borderColor: "var(--gold)" }} />
          <div className="absolute -bottom-px -left-px w-3.5 h-3.5 border-b border-l" style={{ borderColor: "var(--gold)" }} />
          <div className="absolute -bottom-px -right-px w-3.5 h-3.5 border-b border-r" style={{ borderColor: "var(--gold)" }} />

          {/* Header — title only, no wax seal */}
          <h1 className="font-[family-name:var(--font-cinzel)] text-sm text-gold tracking-[0.3em] uppercase mb-8">
            CASE FILING DOCUMENT
          </h1>

          {/* Case Title */}
          <div className="mb-6">
            <label className="block font-[family-name:var(--font-cinzel)] text-[9px] text-text-secondary tracking-[0.2em] uppercase mb-1.5">
              Case Title
            </label>
            <input
              type="text"
              className="input-medieval"
              placeholder="The People vs. auth_middleware.py"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
            />
          </div>

          {/* Code upload — file drop zone */}
          <div className="mb-6">
            <label className="block font-[family-name:var(--font-cinzel)] text-[9px] text-text-secondary tracking-[0.2em] uppercase mb-1.5">
              Code Scroll
            </label>
            <motion.div
              className={`border border-dashed p-8 text-center cursor-pointer transition-colors ${
                isDragging ? "border-accent bg-bg-raised" : "border-default hover:border-accent"
              }`}
              animate={isDragging ? { scale: 1.01 } : { scale: 1 }}
              transition={{ duration: 0.2 }}
              onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
              onDragLeave={() => setIsDragging(false)}
              onDrop={handleDrop}
              onClick={() => document.getElementById("file-input")?.click()}
            >
              {filename ? (
                <div>
                  <p className="font-[family-name:var(--font-cinzel)] text-[13px] text-gold">{filename}</p>
                  <p className="font-[family-name:var(--font-im-fell)] text-[11px] text-text-secondary mt-1">{lineCount} lines loaded</p>
                </div>
              ) : (
                <div>
                  {/* File icon SVG */}
                  <svg
                    className="mx-auto mb-3"
                    width="28"
                    height="32"
                    viewBox="0 0 28 32"
                    fill="none"
                    stroke="var(--gold)"
                    strokeWidth="1.5"
                    style={{ opacity: 0.5 }}
                  >
                    <path d="M4 2H16L24 10V28C24 29.1 23.1 30 22 30H6C4.9 30 4 29.1 4 28V4C4 2.9 4.9 2 6 2Z" />
                    <path d="M16 2V10H24" />
                    <path d="M8 18H20M8 22H16" />
                  </svg>
                  <p className="font-[family-name:var(--font-im-fell)] text-[13px] text-text-secondary italic">
                    Drop your code scroll here
                  </p>
                  <p className="font-[family-name:var(--font-im-fell)] text-[11px] text-text-disabled mt-1.5">
                    or click to browse — .py .js .ts .java and more
                  </p>
                </div>
              )}
              <input
                id="file-input"
                type="file"
                className="hidden"
                accept=".py,.js,.ts,.go,.java,.cpp,.c,.cs,.rb,.php,.rs,.kt,.swift"
                onChange={(e) => {
                  const file = e.target.files?.[0];
                  if (file) handleFile(file);
                }}
              />
            </motion.div>
          </div>

          {/* Language badge */}
          {language && (
            <div className="mb-6 flex items-center gap-2">
              <span className="font-[family-name:var(--font-cinzel)] text-[9px] text-text-secondary tracking-[0.2em] uppercase">Language:</span>
              <span className="px-2.5 py-0.5 text-[10px] border border-gold text-gold font-[family-name:var(--font-cinzel)] tracking-[0.15em]">{language}</span>
            </div>
          )}

          {/* Focus area */}
          <div className="mb-8">
            <label className="block font-[family-name:var(--font-cinzel)] text-[9px] text-text-secondary tracking-[0.2em] uppercase mb-1.5">
              Concern / Focus Area (optional)
            </label>
            <input
              type="text"
              className="input-medieval"
              placeholder="e.g., security vulnerabilities..."
              value={focusArea}
              onChange={(e) => setFocusArea(e.target.value)}
            />
          </div>

          {/* Error */}
          {error && (
            <p className="text-danger text-sm mb-4 italic">{error}</p>
          )}

          {/* Submit — with hover glow */}
          <motion.div whileHover={{ boxShadow: "0 0 24px rgba(201,168,76,0.25)" }}>
            <button
              type="button"
              onClick={handleSubmit}
              disabled={isSubmitting || !codeContent}
              className="btn-primary w-full disabled:opacity-40 disabled:cursor-not-allowed"
            >
              {isSubmitting ? (
                <span className="flex items-center justify-center gap-2">
                  <span className="inline-block w-4 h-4 border border-gold border-t-transparent rounded-full animate-spin" />
                  Filing the case...
                </span>
              ) : (
                "Bring this case to trial"
              )}
            </button>
          </motion.div>
        </div>

        {/* Footer line */}
        <p className="mt-4 text-center text-[10px] text-[#5a4f38] tracking-[0.1em] font-[family-name:var(--font-cinzel)]">
          — LEDGER awaits your submission —
        </p>
      </div>
    </main>
  );
}
