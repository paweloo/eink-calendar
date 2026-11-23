"use client";

import { useActionState } from "react";
import { joinWaitlist, type WaitlistState } from "@/app/actions";

export function WaitlistForm({ id, tone = "light" }: { id: string; tone?: "light" | "dark" }) {
  const [state, action, pending] = useActionState<WaitlistState, FormData>(joinWaitlist, null);
  const dark = tone === "dark";

  if (state?.ok) {
    return (
      <p role="status" className={`font-serif text-xl italic ${dark ? "text-paper" : "text-ink"}`}>
        <span className="text-red not-italic">✓</span> {state.message}
      </p>
    );
  }

  return (
    <form action={action} className="w-full max-w-md">
      <label htmlFor={id} className="sr-only">
        Email address
      </label>
      <div
        className={`flex rounded-full border p-1 focus-within:ring-2 focus-within:ring-red/40 ${
          dark ? "border-paper/30 bg-paper/5" : "border-ink bg-card"
        }`}
      >
        <input
          id={id}
          name="email"
          type="email"
          required
          autoComplete="email"
          placeholder="you@example.com"
          className={`min-w-0 flex-1 bg-transparent px-4 text-base outline-none ${
            dark ? "text-paper placeholder:text-paper/40" : "text-ink placeholder:text-ink-faint"
          }`}
        />
        <input type="text" name="company" tabIndex={-1} autoComplete="off" aria-hidden className="hidden" />
        <button
          type="submit"
          disabled={pending}
          className="shrink-0 rounded-full bg-red px-5 py-2.5 text-sm font-medium text-paper transition-colors hover:bg-red-deep disabled:opacity-60"
        >
          {pending ? "Joining…" : "Join the waitlist"}
        </button>
      </div>
      <p aria-live="polite" className={`mt-2 min-h-5 pl-4 text-sm ${dark ? "text-paper/60" : "text-ink-faint"}`}>
        {state && !state.ok ? <span className="text-red">{state.message}</span> : "One email when it’s ready. Nothing else."}
      </p>
    </form>
  );
}
