# InkCal product site

Next.js 16 (App Router, Tailwind 4). Letterpress-on-paper styling, a live demo of every view and theme, and a waitlist.

```bash
cd site
npm install
npm run dev        # http://localhost:3000
npm run build
```

## Screens are real

Everything in `public/screens/` is rendered by the device's own code (`inkcal/render`). After changing how the
panel draws, refresh them from the repo root:

```bash
./scripts/site-screens.sh                          # panel renders → public/screens
.venv/bin/python scripts/site-phone-screens.py     # phone pages (Wi-Fi, link, settings) → public/phone
```

The phone pages are the real Flask templates rendered against a throwaway demo device and captured with
headless Chrome at iPhone width (needs Google Chrome installed).

## Waitlist

`app/actions.ts` → `joinWaitlist()` is a **stub**: it validates the email and logs it, nothing is stored.
Wire it to a store (Vercel Postgres / Upstash) or an email service (Buttondown, Resend) before launch.

## Deploy on Vercel

Import the repo, set **Root Directory** to `site`. Optionally, under Settings → Git → Ignored Build Step, use
`git diff --quiet HEAD^ HEAD -- .` so pushes that only touch the device code don't rebuild the site.
