import { getApiBase } from "../api/quasarApiClient";

interface QuasarAppBarProps {
  apiOnline: boolean | null;
}

export default function QuasarAppBar({ apiOnline }: QuasarAppBarProps) {
  return (
    <header className="shell-app-bar">
      <div className="flex min-w-0 flex-1 flex-col gap-0.5">
        <div className="flex flex-wrap items-baseline gap-x-3 gap-y-0">
          <h1 className="text-xl font-bold tracking-tight text-brand sm:text-2xl lg:text-3xl">
            GravitonForge Quasar
          </h1>
          <span className="text-lg font-semibold text-ink-secondary sm:text-xl lg:text-2xl">
            Fleet Console
          </span>
        </div>
      </div>

      <div className="flex shrink-0 flex-wrap items-center justify-end gap-2 sm:gap-3">
        <div className="hidden text-right text-xs text-ink-muted md:block">
          <div>
            API:{" "}
            <span className="font-mono text-ink-secondary">{getApiBase()}</span>
          </div>
          <div className="mt-0.5 inline-flex items-center gap-1.5">
            Status:{" "}
            {apiOnline === null ? (
              "checking…"
            ) : apiOnline ? (
              <span className="inline-flex items-center gap-1 font-medium text-trust-ok-text">
                <span aria-hidden="true">●</span> connected
              </span>
            ) : (
              <span className="inline-flex items-center gap-1 font-medium text-trust-fail-text">
                <span aria-hidden="true">●</span> offline
              </span>
            )}
          </div>
        </div>

        <div className="text-xs text-ink-muted md:hidden">
          {apiOnline === null ? (
            "API checking…"
          ) : apiOnline ? (
            <span className="inline-flex items-center gap-1 font-medium text-trust-ok-text">
              <span aria-hidden="true">●</span> connected
            </span>
          ) : (
            <span className="inline-flex items-center gap-1 font-medium text-trust-fail-text">
              <span aria-hidden="true">●</span> offline
            </span>
          )}
        </div>

        <span
          className="rounded-full border border-trust-warn-border bg-trust-warn-bg px-2.5 py-1 text-[10px] font-semibold uppercase tracking-wide text-trust-warn-text sm:text-xs"
          title="Policy breadth disclosure"
        >
          policy breadth = stub_curated_single_task
        </span>

        <button
          type="button"
          className="flex h-9 w-9 items-center justify-center rounded-full border border-line-strong bg-surface-muted text-xs font-semibold text-ink-secondary transition-colors hover:bg-surface-inset focus:outline-none focus:ring-2 focus:ring-accent/30"
          title="Demo account (stub — non-functional)"
          aria-label="Demo account (stub — non-functional)"
        >
          GF
        </button>
      </div>
    </header>
  );
}
