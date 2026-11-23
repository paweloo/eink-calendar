"use client";

import { useEffect, useState, useSyncExternalStore } from "react";
import { Device } from "./Device";
import { THEMES, VIEWS, viewSrc, type ThemeId, type ViewId } from "@/lib/screens";
import { FRAMES, applyFrame, frameStore, type FrameId } from "@/lib/frames";

function Choice<T extends string>({
  legend,
  options,
  value,
  onChange,
}: {
  legend: string;
  options: readonly { id: T; label: string; note: string }[];
  value: T;
  onChange: (v: T) => void;
}) {
  const current = options.find((o) => o.id === value);
  return (
    <fieldset>
      <legend className="smallcaps text-ink-faint mb-3">{legend}</legend>
      <div className="flex flex-wrap gap-2">
        {options.map((o) => {
          const on = o.id === value;
          return (
            <button
              key={o.id}
              type="button"
              aria-pressed={on}
              onClick={() => onChange(o.id)}
              className={`rounded-full border px-4 py-1.5 text-sm transition-colors ${
                on
                  ? "border-ink bg-ink text-paper"
                  : "border-rule bg-card text-ink hover:border-ink"
              }`}
            >
              {o.label}
            </button>
          );
        })}
      </div>
      <p className="mt-2 text-sm text-ink-soft min-h-5">{current?.note}</p>
    </fieldset>
  );
}

function FramePicker({ value, onChange }: { value: FrameId; onChange: (v: FrameId) => void }) {
  const current = FRAMES.find((f) => f.id === value)!;
  return (
    <fieldset>
      <legend className="smallcaps text-ink-faint mb-3">Frame · 3D printed</legend>
      <div className="flex flex-wrap gap-3">
        {FRAMES.map((f) => {
          const on = f.id === value;
          return (
            <button
              key={f.id}
              type="button"
              aria-pressed={on}
              aria-label={f.label}
              title={f.label}
              onClick={() => onChange(f.id)}
              className={`size-9 rounded-full p-[3px] transition-shadow motion-reduce:transition-none ${
                on ? "ring-2 ring-ink ring-offset-2 ring-offset-paper" : "ring-1 ring-rule hover:ring-ink-faint"
              }`}
            >
              <span
                className="block size-full rounded-full shadow-[inset_0_-2px_3px_rgb(0_0_0/0.25),inset_0_1px_1px_rgb(255_255_255/0.3)]"
                style={{ background: f.color }}
              />
            </button>
          );
        })}
      </div>
      <p className="mt-2 text-sm text-ink-soft min-h-5">
        <span className="font-medium text-ink">{current.label}.</span> {current.note}
      </p>
    </fieldset>
  );
}

export function Demo() {
  const [view, setView] = useState<ViewId>("month");
  const [theme, setTheme] = useState<ThemeId>("classic");
  const frame = useSyncExternalStore(frameStore.subscribe, frameStore.get, frameStore.server);

  // The chosen colour (remembered across visits) recolours every frame on the page.
  useEffect(() => applyFrame(frame), [frame]);

  // Warm the cache so every switch is instant and only the "refresh" is visible.
  useEffect(() => {
    for (const v of VIEWS) for (const t of THEMES) new Image().src = viewSrc(v.id, t.id);
  }, []);

  return (
    <div className="grid gap-10 lg:grid-cols-[1fr_320px] lg:items-center">
      <Device src={viewSrc(view, theme)} alt={`${view} view in the ${theme} theme`} />
      <div className="space-y-8">
        <Choice legend="View" options={VIEWS} value={view} onChange={setView} />
        <Choice legend="Theme" options={THEMES} value={theme} onChange={setTheme} />
        <FramePicker value={frame} onChange={frameStore.set} />
        <p className="border-t border-rule pt-4 text-xs leading-relaxed text-ink-faint">
          These are the real screens, drawn by the calendar’s own software from sample events. The refresh is sped
          up here: a real three-colour panel takes several seconds and only redraws when something changed.
        </p>
      </div>
    </div>
  );
}
