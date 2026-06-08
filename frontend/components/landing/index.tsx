"use client";

import { Navbar } from "./Navbar";
import { Hero } from "./Hero";
import { PipelineStrip } from "./PipelineStrip";
import { HowItRuns } from "./HowItRuns";
import { Features } from "./Features";
import { CtaSection } from "./CtaSection";
import { Reveal } from "./Reveal";

export function Landing() {
  return (
    <div id="top" className="relative pb-16">
      <Navbar />
      <div className="mx-auto w-full max-w-6xl px-5">
        <Hero />
        <Reveal delay={120}>
          <PipelineStrip />
        </Reveal>
        <HowItRuns />
        <Features />
        <CtaSection />
      </div>
    </div>
  );
}
