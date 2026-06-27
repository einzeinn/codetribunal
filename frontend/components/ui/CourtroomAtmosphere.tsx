/**
 * CourtroomAtmosphere — reusable background treatment
 * Adds subtle gold glow, faint grain texture, and pillar lines
 * to give pages the same atmospheric depth as the courtroom.
 */

export default function CourtroomAtmosphere() {
  return (
    <div className="absolute inset-0 z-0 pointer-events-none overflow-hidden">
      {/* Radial gold glow — top center */}
      <div
        className="absolute inset-0"
        style={{
          background: "radial-gradient(ellipse 80% 50% at 50% 0%, rgba(201,168,76,0.08), transparent 60%)",
        }}
      />

      {/* Faint grain/noise texture overlay */}
      <div
        className="absolute inset-0"
        style={{
          opacity: 0.05,
          backgroundImage: `url("data:image/svg+xml,%3Csvg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noise'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.8' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noise)'/%3E%3C/svg%3E")`,
          backgroundSize: "200px 200px",
        }}
      />

      {/* Left pillar line */}
      <div
        className="absolute top-0 bottom-0"
        style={{
          left: "15%",
          width: "1px",
          background: "linear-gradient(180deg, transparent, rgba(201,168,76,0.06) 50%, transparent)",
        }}
      />

      {/* Right pillar line */}
      <div
        className="absolute top-0 bottom-0"
        style={{
          right: "15%",
          width: "1px",
          background: "linear-gradient(180deg, transparent, rgba(201,168,76,0.06) 50%, transparent)",
        }}
      />
    </div>
  );
}
