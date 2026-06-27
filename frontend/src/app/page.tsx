"use client";

import Link from "next/link";
import Image from "next/image";
import { motion } from "framer-motion";
import CourtroomAtmosphere from "../../components/ui/CourtroomAtmosphere";

export default function HeroPage() {
  // Agent accent colors (hardcoded to avoid SSR serialization issues with AGENTS object)
  const agents = [
    { id: "aegis", name: "AEGIS", accent: "#D85A30" },
    { id: "axiom", name: "AXIOM", accent: "#185FA5" },
    { id: "metric", name: "METRIC", accent: "#5F5E5A" },
    { id: "arbiter", name: "ARBITER", accent: "#BA7517" },
    { id: "ledger", name: "LEDGER", accent: "#8B7355" },
  ];

  return (
    <main className="min-h-screen flex flex-col items-center justify-center px-4 relative overflow-hidden bg-bg-primary">
      {/* Atmosphere layer — behind everything */}
      <CourtroomAtmosphere />

      <div className="relative z-10 flex flex-col items-center">
        {/* Kicker line */}
        <div className="flex items-center gap-3 mb-2 opacity-80">
          <div className="w-9 h-px bg-gradient-to-r from-transparent to-[#6b5a30]" />
          <span className="text-[10px] text-[#8a7340] tracking-[0.35em] uppercase font-[family-name:var(--font-cinzel)]">
            Est. in the age of agents
          </span>
          <div className="w-9 h-px bg-gradient-to-l from-transparent to-[#6b5a30]" />
        </div>

        {/* Inquisitor Sword — color-adaptive via currentColor, with floating animation */}
        <motion.div
          animate={{ y: [0, -4, 0] }}
          transition={{ duration: 4, repeat: Infinity, ease: "easeInOut" }}
          className="text-text-primary"
          style={{ color: "var(--text-primary)" }}
        >
          <Image
            src="/vectors/inquisitor-sword.svg"
            alt="Inquisitor Sword"
            width={256}
            height={358}
            className="w-48 h-auto md:w-64"
            priority
          />
        </motion.div>

        {/* Title — 32px below sword */}
        <div className="text-center mt-8">
          <h1 className="text-[40px] font-[family-name:var(--font-cinzel-decorative)] text-gold tracking-[6px] uppercase">
            CODE TRIBUNAL
          </h1>
          <p className="mt-3 text-sm font-[family-name:var(--font-im-fell)] text-text-secondary italic">
            Where every line of code faces justice
          </p>
        </div>

        {/* Agent dots — five colored dots with agent names */}
        <div className="flex gap-5 flex-wrap justify-center my-6">
          {agents.map((agent) => (
            <div
              key={agent.id}
              className="flex items-center gap-1.5 text-[11px] tracking-[0.08em]"
              style={{ color: "var(--text-secondary)" }}
            >
              <span
                className="w-[5px] h-[5px] rounded-full inline-block"
                style={{ background: agent.accent }}
              />
              {agent.name}
            </div>
          ))}
        </div>

        {/* CTA — 32px below subtitle, with hover glow */}
        <motion.div whileHover={{ boxShadow: "0 0 24px rgba(201,168,76,0.25)" }}>
          <Link href="/file" className="btn-primary mt-8 inline-block">
            Approach the Gates
          </Link>
        </motion.div>

        {/* Footer line */}
        <p className="mt-6 text-[10px] text-[#5a4f38] tracking-[0.1em] font-[family-name:var(--font-cinzel)]">
          — five agents await your code —
        </p>
      </div>
    </main>
  );
}
