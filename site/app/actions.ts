"use server";

export type WaitlistState = { ok: boolean; message: string } | null;

const EMAIL = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

/**
 * Waitlist signup. STUB: validates and logs only.
 * To go live, store `email` here (Vercel Postgres/Upstash, or an email service like Buttondown/Resend).
 */
export async function joinWaitlist(_prev: WaitlistState, formData: FormData): Promise<WaitlistState> {
  const email = String(formData.get("email") ?? "").trim().toLowerCase();
  if (!EMAIL.test(email) || email.length > 254) {
    return { ok: false, message: "That email doesn’t look right." };
  }
  // Honeypot: bots fill every field.
  if (formData.get("company")) return { ok: true, message: "You’re on the list." };

  console.log("[waitlist] signup (stub, not stored):", email);
  return { ok: true, message: "You’re on the list. We’ll write when InkCal is ready." };
}
