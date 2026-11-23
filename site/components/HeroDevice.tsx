"use client";

import { useEffect, useState } from "react";
import { Device } from "./Device";
import { viewSrc, type ViewId } from "@/lib/screens";

const CYCLE: ViewId[] = ["month", "week", "agenda"];

/** Hero calendar that "refreshes" to the next view every few seconds. */
export function HeroDevice() {
  const [i, setI] = useState(0);
  useEffect(() => {
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    const t = setInterval(() => !document.hidden && setI((n) => (n + 1) % CYCLE.length), 7000);
    return () => clearInterval(t);
  }, []);
  return <Device src={viewSrc(CYCLE[i], "classic")} alt="InkCal showing this month’s calendar" priority />;
}
