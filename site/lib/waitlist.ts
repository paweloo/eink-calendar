// Waitlist signup, sent straight from the browser (GitHub Pages has no server).
// Set NEXT_PUBLIC_WAITLIST_URL to a form endpoint that accepts a POSTed `email` field and answers JSON,
// e.g. Formspree (https://formspree.io/f/<id>). The deploy workflow reads it from the repo variable WAITLIST_URL.

export type WaitlistState = { ok: boolean; message: string } | null;

const ENDPOINT = process.env.NEXT_PUBLIC_WAITLIST_URL ?? "";
const EMAIL = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export async function joinWaitlist(_prev: WaitlistState, formData: FormData): Promise<WaitlistState> {
  const email = String(formData.get("email") ?? "").trim().toLowerCase();
  if (!EMAIL.test(email) || email.length > 254) {
    return { ok: false, message: "That email doesn’t look right." };
  }
  // Honeypot: bots fill every field.
  if (formData.get("company")) return { ok: true, message: "You’re on the list." };

  if (!ENDPOINT) {
    console.warn("[waitlist] NEXT_PUBLIC_WAITLIST_URL is not set; nothing was sent.");
    return { ok: false, message: "Signups aren’t open yet. Please check back soon." };
  }
  try {
    const body = new FormData();
    body.set("email", email);
    const res = await fetch(ENDPOINT, { method: "POST", body, headers: { Accept: "application/json" } });
    if (!res.ok) throw new Error(String(res.status));
    return { ok: true, message: "You’re on the list. We’ll write when InkCal is ready." };
  } catch {
    return { ok: false, message: "Couldn’t sign you up just now. Please try again." };
  }
}
