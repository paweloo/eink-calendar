"use client";

import { useState } from "react";

const prefersReducedMotion = () =>
  typeof window !== "undefined" && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

/** The calendar in its frame. When `src` changes, the panel runs an e-ink style refresh. */
export function Device({
  src,
  alt,
  compact = false,
  priority = false,
}: {
  src: string;
  alt: string;
  compact?: boolean;
  priority?: boolean;
}) {
  const [shown, setShown] = useState(src);
  const [old, setOld] = useState<string | null>(null);

  // New image: keep the previous one as a ghost while the panel blinks through its inks.
  if (src !== shown) {
    setOld(prefersReducedMotion() ? null : shown);
    setShown(src);
  }

  return (
    <div className={`frame ${compact ? "compact" : ""}`}>
      <div className="mat">
        <div className={`panel ${old ? "refreshing" : ""}`}>
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src={shown} alt={alt} width={800} height={480} fetchPriority={priority ? "high" : "auto"} />
          {old && (
            // eslint-disable-next-line @next/next/no-img-element
            <img src={old} alt="" aria-hidden className="old" width={800} height={480} />
          )}
          <div className="flash" key={shown} onAnimationEnd={() => setOld(null)} />
        </div>
      </div>
    </div>
  );
}
