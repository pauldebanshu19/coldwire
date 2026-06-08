// Staggered entrance wrapper used across landing sections.

export function Reveal({ delay = 0, children }: { delay?: number; children: React.ReactNode }) {
  return (
    <div
      className="animate-in fade-in slide-in-from-bottom-3 duration-700 fill-mode-both"
      style={{ animationDelay: `${delay}ms` }}
    >
      {children}
    </div>
  );
}
