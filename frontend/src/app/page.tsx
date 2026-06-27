import Link from "next/link";

export default function HeroPage() {
  return (
    <main className="min-h-screen flex flex-col items-center justify-center px-4 relative overflow-hidden bg-bg-primary">
      <div className="relative z-10 flex flex-col items-center">
        {/* Inquisitor Sword — color-adaptive via currentColor */}
        <div className="text-text-primary" style={{ color: "var(--text-primary)" }}>
          <img
            src="/vectors/inquisitor-sword.svg"
            alt="Inquisitor Sword"
            className="w-48 h-auto md:w-64"
          />
        </div>

        {/* Title — 32px below sword */}
        <div className="text-center mt-8">
          <h1 className="text-[40px] font-[family-name:var(--font-cinzel-decorative)] text-gold tracking-[6px] uppercase">
            CODE TRIBUNAL
          </h1>
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
