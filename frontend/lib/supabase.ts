import { createBrowserClient } from "@supabase/ssr";

// Publishable key is safe in the browser (NEXT_PUBLIC_*). Never put the
// service_role / secret key here.
export const supabase = createBrowserClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL ?? "",
  process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY ?? "",
);
