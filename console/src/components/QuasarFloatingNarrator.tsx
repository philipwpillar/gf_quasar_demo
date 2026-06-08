import { useEffect, useState } from "react";

import NarratorPanel from "./NarratorPanel";

export default function QuasarFloatingNarrator() {
  const [open, setOpen] = useState(false);

  useEffect(() => {
    if (!open) {
      return;
    }

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        setOpen(false);
      }
    }

    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [open]);

  return (
    <>
      {!open && (
        <button
          type="button"
          onClick={() => setOpen(true)}
          className="shell-narrator-fab"
          aria-label="Ask the ledger — open narrator"
        >
          <svg
            aria-hidden="true"
            className="h-5 w-5"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={2}
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"
            />
          </svg>
          <span>Ask the ledger</span>
        </button>
      )}

      {open && (
        <div
          className="shell-narrator-panel"
          role="dialog"
          aria-label="Ledger narrator"
        >
          <div className="flex items-center justify-between border-b border-line px-4 py-3">
            <div>
              <h2 className="text-sm font-semibold text-ink">Ledger narrator</h2>
              <p className="text-xs text-ink-muted">Read-only — explains, never decides</p>
            </div>
            <button
              type="button"
              onClick={() => setOpen(false)}
              className="rounded-md p-1.5 text-ink-muted transition-colors hover:bg-surface-muted hover:text-ink focus:outline-none focus:ring-2 focus:ring-accent/30"
              aria-label="Close narrator"
            >
              <svg aria-hidden="true" className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
          <div className="max-h-[min(520px,calc(100vh-12rem))] overflow-y-auto px-4 py-4">
            <NarratorPanel embedded />
          </div>
        </div>
      )}
    </>
  );
}
