import Link from "next/link";
import CourthouseGate from "../../components/svg/CourthouseGate";

export default function HeroPage() {
  return (
    <main className="min-h-screen flex flex-col items-center justify-center px-4 relative overflow-hidden bg-bg-primary">
      <div className="relative z-10 flex flex-col items-center">
        {/* Gate SVG — positioned at 55% vertical */}
        <CourthouseGate />

        {/* Title — 32px below gate */}
        <div className="text-center mt-8">
          <h1 className="text-[40px] font-[family-name:var(--font-cinzel-decorative)] text-gold tracking-[6px] uppercase">
            CODE TRIBUNAL
          </h1>
          {/* Subtitle — 12px below title */}
          <p className="mt-3 text-sm font-[family-name:var(--font-im-fell)] text-text-secondary italic">
            Where every line of code faces justice
          </p>
        </div>

        {/* CTA — 32px below subtitle */}
        <Link href="/enter" className="btn-primary mt-8">
          Approach the Gates
        </Link>
      </div>
    </main>
  );
}
