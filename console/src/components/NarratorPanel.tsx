import { FormEvent, useState } from "react";

import { queryAssistant } from "../api/quasarApiClient";
import type { NarratorAnswer } from "../types/quasarLedgerTypes";

const SUGGESTED_QUESTIONS = [
  "Why was this robot denied admission?",
  "Which module failed attestation, and when?",
  "Has this ledger been tampered with?",
] as const;

interface NarratorPanelProps {
  embedded?: boolean;
}

export default function NarratorPanel({ embedded = false }: NarratorPanelProps) {
  const [question, setQuestion] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [answer, setAnswer] = useState<NarratorAnswer | null>(null);

  async function submitQuery(text: string) {
    const trimmed = text.trim();
    if (!trimmed || loading) {
      return;
    }

    setLoading(true);
    setError(null);
    setAnswer(null);

    try {
      const result = await queryAssistant(trimmed);
      setAnswer(result);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Could not reach the narrator. Check the API connection and try again.",
      );
    } finally {
      setLoading(false);
    }
  }

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    void submitQuery(question);
  }

  const content = (
    <>
      {!embedded && (
        <header className="mb-4">
          <h2 className="section-title">Ledger narrator</h2>
          <p className="section-subtitle">
            Read-only assistant over the hash-chained record — explains, never decides.
          </p>
        </header>
      )}

      <form onSubmit={handleSubmit} className="space-y-3">
        <label className="block">
          <span className="sr-only">Ask about the ledger</span>
          <input
            type="text"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder="Ask about the ledger..."
            disabled={loading}
            className="w-full rounded-md border border-line-strong bg-surface-card px-3 py-2 text-sm text-ink placeholder:text-ink-faint focus:border-accent focus:outline-none focus:ring-2 focus:ring-accent/20 disabled:opacity-60"
          />
        </label>

        <div className="flex flex-wrap gap-2">
          {SUGGESTED_QUESTIONS.map((suggested) => (
            <button
              key={suggested}
              type="button"
              disabled={loading}
              onClick={() => {
                setQuestion(suggested);
                void submitQuery(suggested);
              }}
              className="rounded-full border border-line bg-surface-muted px-3 py-1 text-xs font-medium text-ink-secondary hover:border-accent hover:text-accent disabled:opacity-50"
            >
              {suggested}
            </button>
          ))}
        </div>

        <button
          type="submit"
          disabled={loading || !question.trim()}
          className="btn-primary inline-flex items-center gap-2"
        >
          {loading && (
            <span
              className="inline-block h-4 w-4 animate-spin rounded-full border-2 border-white/30 border-t-white"
              aria-hidden="true"
            />
          )}
          {loading ? "Asking…" : "Ask narrator"}
        </button>
      </form>

      {error && (
        <p
          className="mt-4 rounded-md border border-trust-fail-border bg-trust-fail-bg px-3 py-2 text-sm text-trust-fail-text"
          role="alert"
        >
          {error}
        </p>
      )}

      {answer && !answer.llm_configured && (
        <p className="mt-4 rounded-md border border-trust-warn-border bg-trust-warn-bg px-3 py-2 text-sm text-trust-warn-text">
          Narrator not configured — set QUASAR_LLM_API_KEY in .env
        </p>
      )}

      {answer && answer.llm_configured && (
        <div className="mt-4 space-y-3">
          <div className="rounded-md border border-line bg-surface-inset px-4 py-3 text-sm leading-relaxed text-ink">
            {answer.answer}
          </div>
          {answer.grounded_on.length > 0 && (
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-xs font-medium uppercase tracking-wide text-ink-muted">
                Grounded on ledger seq
              </span>
              {answer.grounded_on.map((seq) => (
                <span
                  key={seq}
                  className="rounded-full border border-accent/30 bg-accent-subtle px-2.5 py-0.5 font-mono text-xs font-semibold text-accent"
                >
                  #{seq}
                </span>
              ))}
            </div>
          )}
        </div>
      )}

      <p
        className={`mt-4 text-xs text-ink-muted ${embedded ? "pt-2" : "border-t border-line pt-3"}`}
      >
        The assistant explains the record. It never decides clearance.
      </p>
    </>
  );

  if (embedded) {
    return content;
  }

  return <section className="card">{content}</section>;
}
