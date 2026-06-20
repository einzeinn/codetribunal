import Link from "next/link";
import GuardCharacter from "../../../components/svg/GuardCharacter";

export default function EnterPage() {
  return (
    <main className="min-h-screen flex flex-col items-center justify-center px-4 md:px-8 bg-bg-primary">
      <div className="max-w-4xl w-full flex flex-col md:flex-row items-center gap-8 md:gap-16">
        {/* Guard — Left 40% */}
        <div className="flex-shrink-0">
          <GuardCharacter />
        </div>

        {/* Dialogue — Right 60% */}
        <div className="flex-1 max-w-[360px]">
          {/* Speech bubble with left gold accent */}
          <div className="bg-bg-surface border border-default border-l-gold border-l p-6 md:p-8">
            <h2 className="font-[family-name:var(--font-cinzel)] text-[10px] text-gold tracking-[0.2em] uppercase mb-4">
              Guard of the Tribunal
            </h2>
            <p className="font-[family-name:var(--font-im-fell)] text-sm text-text-primary italic leading-[1.8] mb-4">
              &quot;Halt, traveller. None may enter the Code Tribunal without a proper Case Filing.
              Present your scroll, and state the nature of your grievance against the code in question.&quot;
            </p>
            <p className="font-[family-name:var(--font-im-fell)] text-xs text-text-secondary italic mb-6">
              The guard adjusts his grip on the spear, eyes scanning you beneath the visor.
            </p>
            <Link href="/file" className="btn-primary inline-block">
              Present your case scroll
            </Link>
          </div>
        </div>
      </div>
    </main>
  );
}
