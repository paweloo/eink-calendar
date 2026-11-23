import { Demo } from "@/components/Demo";
import { Device } from "@/components/Device";
import { HeroDevice } from "@/components/HeroDevice";
import { PhoneShowcase } from "@/components/PhoneShowcase";
import { WaitlistForm } from "@/components/WaitlistForm";
import { screenSrc } from "@/lib/screens";

const NAV = [
  ["Demo", "#demo"],
  ["Features", "#features"],
  ["Setup", "#setup"],
  ["App", "#phone"],
  ["Specs", "#specs"],
] as const;

const STRIP = [
  "Month · Week · Agenda",
  "Black, white & red e-paper",
  "Set up from your phone",
  "Google Calendar",
  "Quiet at night",
  "No backlight",
  "Four themes",
  "Five frame colours",
];

const FEATURES = [
  {
    title: "Paper, not a screen",
    body: "E-paper reflects light like a printed page. No glow in a dark room, and you can read it from across the kitchen.",
  },
  {
    title: "Set up from your phone",
    body: "Scan the code on the screen, pick your Wi-Fi, link Google with a six-digit code. No keyboard and no app to install.",
  },
  {
    title: "Your calendars, chosen",
    body: "Show the family calendar and hide the work one. Pick which Google calendars appear, and change it whenever you like.",
  },
  {
    title: "Three ways to read time",
    body: "A full month with today’s schedule beside it, a seven-day week, or an agenda of the days ahead.",
  },
  {
    title: "Four moods, one panel",
    body: "Classic black with red, plain mono, a heavier bold, or dark: white on black with red accents.",
  },
  {
    title: "Quiet when you sleep",
    body: "Quiet hours keep the panel still overnight, 23:00 to 06:00 by default. Set your own hours in settings.",
  },
  {
    title: "Redraws only on change",
    body: "The panel refreshes only when what it shows actually changes. If the Wi-Fi drops, the last calendar stays put.",
  },
  {
    title: "Settings in your pocket",
    body: "Open calendar-xxxx.local on any phone on your Wi-Fi to change the view, theme, week start, 24-hour clock and sync interval.",
  },
];

const STEPS = [
  {
    n: "I",
    title: "Say hello",
    body: "Plug it in. The screen shows a QR code. Scan it, and your phone joins the calendar’s own setup Wi-Fi.",
    src: screenSrc("welcome"),
    alt: "Welcome screen with a QR code",
  },
  {
    n: "II",
    title: "Link Google",
    body: "Pick your home network, then link your Google account with the six-digit code that only the screen shows.",
    src: screenSrc("link"),
    alt: "Link screen with a six-digit code",
  },
  {
    n: "III",
    title: "Hang it up",
    body: "That’s it. Your calendar appears and stays current. Nothing else to do.",
    src: screenSrc("ready"),
    alt: "Ready screen confirming setup",
  },
];

const SPECS = [
  ["Display", "7.5″ e-paper, 800 × 480 pixels"],
  ["Inks", "Black, white and red"],
  ["Frame", "3D printed in five colours"],
  ["Inside", "Raspberry Pi Zero 2 W"],
  ["Connection", "2.4 GHz Wi-Fi"],
  ["Calendar", "Google Calendar, any calendars you choose"],
  ["Views", "Month, week, agenda"],
  ["Themes", "Classic, mono, bold, dark"],
  ["Setup & settings", "Any phone browser. No app."],
];

const FAQ = [
  [
    "Do I need to install an app?",
    "No. Setup and settings both run in your phone’s browser. The calendar hosts its own little settings page on your Wi-Fi.",
  ],
  ["Which calendars does it show?", "Google Calendar. You choose which of your calendars appear."],
  [
    "What if I change my Wi-Fi?",
    "Change it from settings. If the calendar can’t join a network, it turns its setup Wi-Fi back on so you can pick again.",
  ],
  [
    "Does it glow at night?",
    "No. E-paper has no backlight. It looks like paper and holds its image even when nothing is being redrawn.",
  ],
];

function SectionHead({ no, kicker, title }: { no: string; kicker: string; title: React.ReactNode }) {
  return (
    <header className="mb-12 grid gap-4 md:grid-cols-[120px_1fr]">
      <div className="smallcaps text-red">§ {no}</div>
      <div>
        <div className="smallcaps mb-3 text-ink-faint">{kicker}</div>
        <h2 className="press font-serif text-4xl leading-[1.05] tracking-tight text-balance md:text-5xl">{title}</h2>
      </div>
    </header>
  );
}

export default function Home() {
  return (
    <div className="relative overflow-x-clip">
      {/* Masthead */}
      <div className="border-b border-rule">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-2 sm:px-6">
          <span className="smallcaps text-ink-faint">Vol. I · No. 1</span>
          <span className="smallcaps hidden text-ink-faint sm:inline">Printed fresh, all day long</span>
          <span className="smallcaps text-ink-faint">Est. 2026</span>
        </div>
      </div>

      <nav className="sticky top-0 z-40 border-b border-rule bg-paper/85 backdrop-blur">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-3 sm:px-6">
          <a href="#" className="font-serif text-2xl font-semibold tracking-tight">
            InkCal<span className="text-red">.</span>
          </a>
          <div className="flex items-center gap-6">
            <ul className="hidden gap-6 text-sm text-ink-soft md:flex">
              {NAV.map(([label, href]) => (
                <li key={href}>
                  <a href={href} className="hover:text-ink">
                    {label}
                  </a>
                </li>
              ))}
            </ul>
            <a
              href="#waitlist"
              className="rounded-full bg-ink px-4 py-2 text-sm font-medium text-paper transition-colors hover:bg-red"
            >
              Join waitlist
            </a>
          </div>
        </div>
      </nav>

      {/* Hero */}
      <header className="mx-auto max-w-6xl px-4 pt-14 pb-20 sm:px-6 md:pt-20">
        <div className="grid items-center gap-14 lg:grid-cols-[1fr_1.15fr]">
          <div>
            <p className="smallcaps mb-6 text-red">A wall calendar that keeps itself current</p>
            <h1 className="press font-serif text-[3.4rem] leading-[0.95] font-medium tracking-tight text-balance sm:text-7xl">
              Your days, <em className="font-normal">set in ink.</em>
            </h1>
            <p className="mt-7 max-w-md text-lg leading-relaxed text-ink-soft">
              InkCal puts your Google Calendar on a 7.5-inch black, white and red e-paper display. No glow, no app, no
              fiddling. Just your week on the wall, quietly up to date.
            </p>
            <div className="mt-9">
              <WaitlistForm id="email-hero" />
            </div>
          </div>
          <div className="relative">
            <div className="absolute -top-4 -right-3 z-10 hidden rotate-[7deg] rounded-full border-2 border-red bg-paper px-3 py-1 shadow-sm sm:block">
              <span className="smallcaps text-red">Real screens</span>
            </div>
            <HeroDevice />
          </div>
        </div>
      </header>

      {/* Strip */}
      <div className="double-rule border-b border-ink bg-ink text-paper" aria-hidden>
        <div className="overflow-hidden py-3">
          <div className="marquee">
            {[...STRIP, ...STRIP].map((s, i) => (
              <span key={i} className="flex items-center font-serif text-lg italic">
                <span className="px-6">{s}</span>
                <span className="text-red not-italic">✦</span>
              </span>
            ))}
          </div>
        </div>
      </div>

      <main>
        {/* Demo */}
        <section id="demo" className="mx-auto max-w-6xl scroll-mt-20 px-4 py-24 sm:px-6">
          <SectionHead
            no="I"
            kicker="Try it"
            title={
              <>
                Turn the dials. <em className="font-normal text-ink-soft">Watch the ink settle.</em>
              </>
            }
          />
          <Demo />
        </section>

        {/* Features */}
        <section id="features" className="scroll-mt-20 border-y border-rule bg-paper-deep/60">
          <div className="mx-auto max-w-6xl px-4 py-24 sm:px-6">
            <SectionHead no="II" kicker="The almanac" title="Small things, done properly." />
            <div className="grid border-t border-l border-rule sm:grid-cols-2 lg:grid-cols-4">
              {FEATURES.map((f, i) => (
                <article key={f.title} className="border-r border-b border-rule p-6">
                  <div className="mb-6 font-serif text-3xl text-red tabular-nums">{String(i + 1).padStart(2, "0")}</div>
                  <h3 className="mb-2 font-serif text-xl font-medium">{f.title}</h3>
                  <p className="text-sm leading-relaxed text-ink-soft">{f.body}</p>
                </article>
              ))}
            </div>
          </div>
        </section>

        {/* Setup */}
        <section id="setup" className="mx-auto max-w-6xl scroll-mt-20 px-4 py-24 sm:px-6">
          <SectionHead
            no="III"
            kicker="Setup"
            title={
              <>
                Out of the box and onto the wall. <em className="font-normal">No keyboard required.</em>
              </>
            }
          />
          <ol className="grid gap-12 md:grid-cols-3 md:gap-8">
            {STEPS.map((s) => (
              <li key={s.n}>
                <Device src={s.src} alt={s.alt} compact />
                <div className="mt-6 flex gap-4">
                  <span className="font-serif text-3xl text-red italic">{s.n}.</span>
                  <div>
                    <h3 className="font-serif text-xl font-medium">{s.title}</h3>
                    <p className="mt-1 text-sm leading-relaxed text-ink-soft">{s.body}</p>
                  </div>
                </div>
              </li>
            ))}
          </ol>
        </section>

        {/* Phone */}
        <section id="phone" className="scroll-mt-20 border-t border-rule bg-paper-deep/60">
          <div className="mx-auto max-w-6xl px-4 py-24 sm:px-6">
            <SectionHead
              no="IV"
              kicker="On your phone"
              title={
                <>
                  The remote is <em className="font-normal">the phone in your pocket.</em>
                </>
              }
            />
            <PhoneShowcase />
          </div>
        </section>

        {/* Specs + FAQ */}
        <section id="specs" className="scroll-mt-20 border-t border-rule">
          <div className="mx-auto grid max-w-6xl gap-16 px-4 py-24 sm:px-6 lg:grid-cols-2">
            <div>
              <SectionHead no="V" kicker="Specifications" title="The fine print." />
              <dl className="double-rule">
                {SPECS.map(([k, v]) => (
                  <div key={k} className="flex items-baseline gap-3 border-b border-rule py-3 text-sm">
                    <dt className="smallcaps shrink-0 text-ink-faint">{k}</dt>
                    <span className="mb-1 flex-1 border-b border-dotted border-ink-faint/60" aria-hidden />
                    <dd className="text-right">{v}</dd>
                  </div>
                ))}
              </dl>
            </div>
            <div>
              <SectionHead no="VI" kicker="Questions" title="Asked & answered." />
              <div className="double-rule">
                {FAQ.map(([q, a]) => (
                  <details key={q} className="group border-b border-rule py-4">
                    <summary className="flex cursor-pointer list-none items-center justify-between gap-4 font-serif text-lg">
                      {q}
                      <span className="text-red transition-transform group-open:rotate-45">+</span>
                    </summary>
                    <p className="mt-2 text-sm leading-relaxed text-ink-soft">{a}</p>
                  </details>
                ))}
              </div>
            </div>
          </div>
        </section>

        {/* Waitlist */}
        <section id="waitlist" className="scroll-mt-20 bg-ink text-paper">
          <div className="mx-auto max-w-6xl px-4 py-24 text-center sm:px-6">
            <p className="smallcaps mb-6 text-red">The waitlist</p>
            <h2 className="mx-auto max-w-3xl font-serif text-5xl leading-[1.02] tracking-tight text-balance md:text-6xl">
              Be first to hang one <em className="font-normal">on your wall.</em>
            </h2>
            <p className="mx-auto mt-6 max-w-lg text-paper/70">
              InkCal isn’t on sale yet. Leave your email and we’ll write once, when it is.
            </p>
            <div className="mt-10 flex justify-center">
              <WaitlistForm id="email-footer" tone="dark" />
            </div>
          </div>
        </section>
      </main>

      <footer className="border-t border-rule">
        <div className="mx-auto flex max-w-6xl flex-col gap-3 px-4 py-8 text-sm text-ink-faint sm:flex-row sm:justify-between sm:px-6">
          <span className="font-serif text-lg text-ink">
            InkCal<span className="text-red">.</span>
          </span>
          <span>Every screen on this page was drawn by the calendar’s own software.</span>
        </div>
      </footer>
    </div>
  );
}
