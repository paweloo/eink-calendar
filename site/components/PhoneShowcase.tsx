"use client";

import { useState } from "react";
import { asset } from "@/lib/asset";

// Images in /public/phone are the device's own web pages: run scripts/site-phone-screens.py to refresh them.
const PAGES = [
  {
    id: "wifi",
    label: "Pick your Wi-Fi",
    body: "Scan the code on the screen and this page opens by itself. Choose your home network and type its password.",
    url: "10.42.0.1",
    src: asset("/phone/wifi.png"),
    h: 1653,
  },
  {
    id: "link",
    label: "Prove you’re there",
    body: "Type the six-digit code from the calendar’s screen, then sign in to Google. The calendar can only read events, never change them.",
    url: "192.168.1.23",
    src: asset("/phone/link.png"),
    h: 1303,
  },
  {
    id: "settings",
    label: "Tune it any time",
    body: "View, theme, week start, which calendars appear, how often to sync, quiet hours. A live preview shows exactly what the panel shows.",
    url: "calendar-7f3a.local",
    src: asset("/phone/settings.png"),
    h: 4345,
  },
] as const;

type PageId = (typeof PAGES)[number]["id"];

function StatusBar() {
  return (
    <div className="flex h-11 shrink-0 items-end justify-between px-7 pb-1.5 text-[13px] font-semibold text-black">
      <span>9:41</span>
      <span className="flex items-center gap-1.5" aria-hidden>
        <svg width="17" height="11" viewBox="0 0 17 11" fill="currentColor">
          <rect x="0" y="7" width="3" height="4" rx="0.7" />
          <rect x="4.5" y="5" width="3" height="6" rx="0.7" />
          <rect x="9" y="2.5" width="3" height="8.5" rx="0.7" />
          <rect x="13.5" y="0" width="3" height="11" rx="0.7" />
        </svg>
        <svg width="15" height="11" viewBox="0 0 15 11" fill="currentColor">
          <path d="M7.5 2.2c2.1 0 4 .8 5.5 2.1l1.1-1.1A9.3 9.3 0 0 0 7.5.6 9.3 9.3 0 0 0 .9 3.2L2 4.3a7.8 7.8 0 0 1 5.5-2.1Zm0 3.2c1.2 0 2.4.5 3.3 1.3l1.1-1.1a6.2 6.2 0 0 0-8.8 0l1.1 1.1c.9-.8 2-1.3 3.3-1.3Zm0 3.2c-.4 0-.8.2-1.1.5L7.5 10.2l1.1-1.1c-.3-.3-.7-.5-1.1-.5Z" />
        </svg>
        <span className="relative h-[11px] w-[22px] rounded-[3px] border border-black/40 p-[1.5px]">
          <span className="block h-full w-3/4 rounded-[1.5px] bg-black" />
        </span>
      </span>
    </div>
  );
}

function Phone({ page }: { page: (typeof PAGES)[number] }) {
  return (
    <div className="relative mx-auto w-[300px] sm:w-[320px]">
      {/* Body */}
      <div className="rounded-[52px] bg-[#1d1c1a] p-[11px] shadow-[0_0_0_1.5px_#4b4842,0_40px_60px_-25px_rgb(40_25_10/0.55),0_18px_25px_-15px_rgb(40_25_10/0.4)]">
        {/* Screen */}
        <div className="relative flex aspect-[390/844] flex-col overflow-hidden rounded-[42px] bg-white">
          <div className="absolute top-2.5 left-1/2 z-10 h-[26px] w-[92px] -translate-x-1/2 rounded-full bg-black" />
          <StatusBar />
          <div
            key={page.id}
            className="min-h-0 flex-1 overflow-y-auto overscroll-contain [scrollbar-width:none] [&::-webkit-scrollbar]:hidden"
          >
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src={page.src} alt={`${page.label}: the calendar’s own page on a phone`} width={390} height={page.h / 2} className="block w-full" />
          </div>
          {/* Browser address bar */}
          <div className="shrink-0 border-t border-black/10 bg-[#f6f6f6]/95 px-4 pt-2 pb-6 backdrop-blur">
            <div className="flex items-center justify-center gap-1.5 rounded-xl bg-black/[0.06] py-2 text-[13px] text-black/80">
              <svg width="10" height="12" viewBox="0 0 10 12" fill="none" stroke="currentColor" strokeWidth="1.4" aria-hidden>
                <rect x="1" y="5" width="8" height="6" rx="1.2" fill="currentColor" stroke="none" opacity=".7" />
                <path d="M3 5V3.5a2 2 0 0 1 4 0V5" />
              </svg>
              {page.url}
            </div>
            <div className="mx-auto mt-3 h-[5px] w-[120px] rounded-full bg-black" />
          </div>
        </div>
      </div>
      {/* Side buttons */}
      <span className="absolute top-[110px] -left-[3px] h-8 w-[3px] rounded-l bg-[#2c2a27]" />
      <span className="absolute top-[160px] -left-[3px] h-14 w-[3px] rounded-l bg-[#2c2a27]" />
      <span className="absolute top-[150px] -right-[3px] h-20 w-[3px] rounded-r bg-[#2c2a27]" />
    </div>
  );
}

export function PhoneShowcase() {
  const [id, setId] = useState<PageId>("settings");
  const page = PAGES.find((p) => p.id === id)!;
  return (
    <div className="grid items-center gap-14 lg:grid-cols-[1fr_auto]">
      <ol className="space-y-3">
        {PAGES.map((p, i) => {
          const on = p.id === id;
          return (
            <li key={p.id}>
              <button
                type="button"
                aria-pressed={on}
                onClick={() => setId(p.id)}
                className={`w-full rounded-2xl border p-5 text-left transition-colors ${
                  on ? "border-ink bg-card shadow-[4px_4px_0_var(--ink)]" : "border-rule hover:border-ink-faint"
                }`}
              >
                <div className="flex items-baseline gap-4">
                  <span className={`font-serif text-2xl italic ${on ? "text-red" : "text-ink-faint"}`}>{i + 1}.</span>
                  <div>
                    <h3 className="font-serif text-xl font-medium">{p.label}</h3>
                    <p className={`mt-1 text-sm leading-relaxed ${on ? "text-ink-soft" : "text-ink-faint"}`}>{p.body}</p>
                    <p className="smallcaps mt-3 text-ink-faint">{p.url}</p>
                  </div>
                </div>
              </button>
            </li>
          );
        })}
        <li className="pt-2 pl-1 text-xs text-ink-faint">
          Real pages from the calendar, captured at iPhone size.{id === "settings" && " Scroll inside the phone to see them all."}
        </li>
      </ol>
      <div className="order-first lg:order-none">
        <Phone page={page} />
      </div>
    </div>
  );
}
