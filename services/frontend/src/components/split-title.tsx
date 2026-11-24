import type { CSSProperties } from "react";

/** A headline whose words slide up one after another (CSS only, starts at first paint). The text itself stays one sentence. */
export function SplitTitle({ text, start = 0 }: { text: string; start?: number }) {
  const words = text.split(" ");
  return (
    <>
      {words.map((word, i) => (
        <span key={i}>
          <span className="word">
            <span style={{ "--i": start + i } as CSSProperties}>{word}</span>
          </span>
          {i < words.length - 1 ? " " : null}
        </span>
      ))}
    </>
  );
}
