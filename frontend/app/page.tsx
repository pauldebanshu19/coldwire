"use client";

import { useAuth } from "@/lib/auth";
import { AppHeader } from "@/components/app-header";
import { Landing } from "@/components/landing";
import { SubmitConsole } from "@/components/submit-console";
import { JobList } from "@/components/job-list";

function Dashboard() {
  return (
    <div className="space-y-8 py-6">
      <SubmitConsole />
      <JobList />
    </div>
  );
}

export default function Home() {
  const { token, ready } = useAuth();

  if (!ready) {
    return (
      <div className="flex flex-1 items-center justify-center py-24 font-mono text-sm text-muted-foreground">
        loading…
      </div>
    );
  }

  // Logged out → the landing (which has its own navbar). No AppHeader here,
  // so there's only ever one navbar.
  if (!token) return <Landing />;

  return (
    <>
      <AppHeader />
      <main className="mx-auto w-full max-w-6xl flex-1 px-5">
        <Dashboard />
      </main>
      <footer className="border-t border-border/60 py-6">
        <div className="mx-auto w-full max-w-6xl px-5 text-center font-mono text-[11px] text-muted-foreground">
          &copy; {new Date().getFullYear()} Coldwire. All rights reserved.
        </div>
      </footer>
    </>
  );
}
