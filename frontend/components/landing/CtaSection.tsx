export function CtaSection() {
  return (
    <section className="mt-16">
      <div className="relative overflow-hidden rounded-2xl border border-primary/30 bg-card/60 p-8 text-center sm:p-12 glow-edge">
        <div className="absolute inset-0 -z-10 bg-grid opacity-60" />
        <h2 className="mx-auto max-w-xl text-2xl font-semibold tracking-tight sm:text-4xl">
          Type one domain. <span className="text-primary text-glow">Watch it run.</span>
        </h2>
        <p className="mx-auto mt-4 max-w-md text-sm text-muted-foreground">
          From a single seed to a vetted, ready-to-send contact list — with a safety
          checkpoint before anything leaves the building.
        </p>
        <a
          href="#access"
          className="mt-7 inline-flex h-11 items-center rounded-md bg-primary px-6 font-mono text-sm font-medium tracking-wide text-primary-foreground transition-transform hover:scale-[1.02]"
        >
          Get access →
        </a>
      </div>
    </section>
  );
}
