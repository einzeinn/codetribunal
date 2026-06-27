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

      {/* Decorative border frame */}
      <div className="absolute inset-0 z-0 pointer-events-none">
        <div className="absolute top-4 left-4 right-4 bottom-4 border border-[#6b5a30] opacity-20" />
        <div className="absolute top-6 left-6 right-6 bottom-6 border border-[#6b5a30] opacity-10" />
      </div>

      <div className="relative z-10 flex flex-col items-center">
        {/* Top decorative element */}
        <div className="flex items-center gap-2 mb-6">
          <div className="w-12 h-px bg-gradient-to-r from-transparent to-[#8a7340]" />
          <div className="w-2 h-2 bg-[#8a7340] rotate-45" />
          <div className="w-12 h-px bg-gradient-to-l from-transparent to-[#8a7340]" />
        </div>

        {/* Kicker line */}
        <div className="flex items-center gap-3 mb-4 opacity-60">
          <div className="w-8 h-px bg-gradient-to-r from-transparent to-[#6b5a30]" />
          <span className="text-[9px] text-[#8a7340] tracking-[0.4em] uppercase font-[family-name:var(--font-cinzel)]">
            Where Code Meets Justice
          </span>
          <div className="w-8 h-px bg-gradient-to-l from-transparent to-[#6b5a30]" />
        </div>

        {/* Inquisitor Sword — larger, centered, with floating animation */}
        <motion.div
          animate={{ y: [0, -6, 0] }}
          transition={{ duration: 5, repeat: Infinity, ease: "easeInOut" }}
          className="text-text-primary mb-6"
          style={{ color: "var(--text-primary)" }}
        >
          <Image
            src="/vectors/inquisitor-sword.svg"
            alt="Inquisitor Sword"
            width={320}
            height={448}
            className="w-64 h-auto md:w-80"
            priority
          />
        </motion.div>

        {/* Title — with decorative framing */}
        <div className="text-center mb-4">
          <div className="flex items-center justify-center gap-3 mb-2">
            <div className="w-16 h-px bg-gradient-to-r from-transparent to-[#c9a84c]" />
            <div className="w-1.5 h-1.5 bg-[#c9a84c] rotate-45" />
            <div className="w-16 h-px bg-gradient-to-l from-transparent to-[#c9a84c]" />
          </div>
          
          <h1 className="text-[48px] md:text-[56px] font-[family-name:var(--font-cinzel-decorative)] text-gold tracking-[8px] uppercase">
            CODE TRIBUNAL
          </h1>
          
          <div className="flex items-center justify-center gap-3 mt-2 mb-4">
            <div className="w-16 h-px bg-gradient-to-r from-transparent to-[#c9a84c]" />
            <div className="w-1.5 h-1.5 bg-[#c9a84c] rotate-45" />
            <div className="w-16 h-px bg-gradient-to-l from-transparent to-[#c9a84c]" />
          </div>
          
          <p className="text-sm md:text-base font-[family-name:var(--font-im-fell)] text-text-secondary italic">
            Where every line of code faces justice
          </p>
        </div>

        {/* Agent dots — five colored dots with agent names */}
        <div className="flex gap-6 flex-wrap justify-center my-8">
          {agents.map((agent) => (
            <div
              key={agent.id}
              className="flex items-center gap-2 text-[11px] tracking-[0.1em]"
              style={{ color: "var(--text-secondary)" }}
            >
              <span
                className="w-[6px] h-[6px] rounded-full inline-block"
                style={{ background: agent.accent }}
              />
              {agent.name}
            </div>
          ))}
        </div>

        {/* CTA — with decorative border and hover glow */}
        <motion.div 
          whileHover={{ 
            boxShadow: "0 0 32px rgba(201,168,76,0.3)",
            scale: 1.02
          }}
          transition={{ duration: 0.2 }}
        >
          <Link 
            href="/file" 
            className="btn-primary mt-4 inline-block text-[12px] tracking-[0.3em] px-10 py-3"
          >
            Approach the Gates
          </Link>
        </motion.div>

        {/* Footer line */}
        <div className="flex items-center gap-2 mt-8">
          <div className="w-8 h-px bg-[#5a4f38]" />
          <p className="text-[10px] text-[#5a4f38] tracking-[0.15em] font-[family-name:var(--font-cinzel)]">
            five agents await your code
          </p>
          <div className="w-8 h-px bg-[#5a4f38]" />
        </div>

        {/* Bottom decorative element */}
        <div className="flex items-center gap-2 mt-6">
          <div className="w-12 h-px bg-gradient-to-r from-transparent to-[#8a7340]" />
          <div className="w-2 h-2 bg-[#8a7340] rotate-45" />
          <div className="w-12 h-px bg-gradient-to-l from-transparent to-[#8a7340]" />
        </div>
      </div>
    </main>
  );
}