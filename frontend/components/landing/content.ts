// Landing copy, kept separate so sections stay presentational + data-driven.

export interface RunStep {
  n: string;
  label: string;
  provider: string;
  body: string;
}

export const RUN: RunStep[] = [
  { n: "01", label: "Source", provider: "Ocean.io",
    body: "One seed company expands into a clean list of lookalike companies — same industry, size and market." },
  { n: "02", label: "Prospect", provider: "Prospeo",
    body: "Each company surfaces its C-suite and VP decision-makers, with LinkedIn profiles attached." },
  { n: "03", label: "Resolve", provider: "Prospeo",
    body: "Every profile is resolved to a verified, deliverable work email — masked previews are revealed." },
  { n: "04", label: "Send", provider: "Brevo",
    body: "Personalized outreach fires on your approval. One mail per human, unsubscribe baked in." },
];

export interface Feature {
  title: string;
  body: string;
}

export const FEATURES: Feature[] = [
  { title: "Zero humans in the loop", body: "One domain in. Sourcing through mailing runs itself — no copy-paste between tools." },
  { title: "Hard approval gate", body: "Nothing sends until you see a rendered sample against a real contact and approve it." },
  { title: "Verified work emails", body: "Decision-makers resolved to deliverable addresses, sent DKIM-signed from your domain." },
  { title: "Copy that gets opened", body: "Each email is written to the contact's role and company — not a generic blast." },
  { title: "Resilient by design", body: "Global rate limits, retry/backoff, de-duplication and partial-failure tolerance." },
  { title: "Live, then exportable", body: "Watch every stage stream in real time, then export the full result set to CSV." },
];

export const STATS: [string, string][] = [
  ["1", "input"],
  ["4", "stages"],
  ["0", "manual steps"],
  ["1", "approval"],
];
