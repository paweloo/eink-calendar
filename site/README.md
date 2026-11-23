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

The form posts straight from the browser to `NEXT_PUBLIC_WAITLIST_URL` (see `lib/waitlist.ts`): any endpoint
that accepts a POSTed `email` field and answers JSON, such as a Formspree form (`https://formspree.io/f/<id>`).
Unset, the form says signups aren't open yet and sends nothing.

## Deploy (GitHub Pages)

The site is a static export (`npm run build` → `out/`). `.github/workflows/site.yml` builds and publishes it on
every push to `main` that touches `site/`.

One-time setup on GitHub:
1. Settings → Pages → Source: **GitHub Actions**.
2. Settings → Secrets and variables → Actions → Variables: add `WAITLIST_URL`.

It goes live at `https://<user>.github.io/eink-calendar/`. The base path comes from the Pages settings, so adding a
custom domain later needs no code change. To try the Pages build locally:

```bash
NEXT_PUBLIC_BASE_PATH=/eink-calendar npm run build   # then serve out/ under /eink-calendar/
```
