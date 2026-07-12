import { useState, type FormEvent } from "react";
import { askQuestion, isBackendUnreachable } from "../api/client";
import { ApiError, type AskResponse } from "../api/types";

type Status = "idle" | "loading" | "answered" | "error";

// Terminology from NIST TREC graded relevance judgments (trec.nist.gov):
// highly relevant / relevant / not relevant. "Not relevant" never reaches
// the UI — the backend's 0.15 similarity floor filters it (DECISIONS.md D8,
// /ask similarity threshold & source filtering). The 0.45 cutoff is the top
// of the measured true-answer range, 0.45–0.53 across the D8 calibration
// and D10 evaluation runs (DECISIONS.md D10, Evaluation harness) — cosine
// magnitudes aren't comparable across models, so cutoffs are calibrated
// per corpus, not taken from a universal scale.
function relevanceLabel(score: number): string {
  return score >= 0.45 ? "Highly relevant" : "Relevant";
}

interface QAPanelProps {
  /** Q&A is pointless against an empty store, so the form stays disabled
   * until at least one document exists. */
  hasDocuments: boolean;
  /** True once the document list has actually loaded — the "upload first"
   * hint waits for it, so it never flashes while the list is still fetching. */
  documentsLoaded: boolean;
  /** Routes "no backend answered" to the app-level banner. */
  onBackendDown: () => void;
}

export function QAPanel({
  hasDocuments,
  documentsLoaded,
  onBackendDown,
}: QAPanelProps) {
  const [question, setQuestion] = useState("");
  const [status, setStatus] = useState<Status>("idle");
  const [answer, setAnswer] = useState<AskResponse | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (question.trim() === "") return;

    setStatus("loading");
    setErrorMessage(null);
    try {
      const response = await askQuestion(question);
      setAnswer(response);
      setStatus("answered");
    } catch (error) {
      if (isBackendUnreachable(error)) {
        onBackendDown();
        setStatus("idle");
        return;
      }
      setStatus("error");
      setErrorMessage(error instanceof ApiError ? error.message : "Ask failed");
    }
  };

  return (
    <section>
      <h2>Q&amp;A</h2>
      <form onSubmit={handleSubmit} aria-busy={status === "loading"}>
        <label htmlFor="qa-question">Question</label>
        <div className="ask-row">
          <input
            id="qa-question"
            type="text"
            value={question}
            onChange={(event) => setQuestion(event.target.value)}
            disabled={!hasDocuments}
            required
          />
          <button
            type="submit"
            disabled={
              !hasDocuments || question.trim() === "" || status === "loading"
            }
          >
            {status === "loading" ? "Asking…" : "Ask"}
          </button>
        </div>
        {documentsLoaded && !hasDocuments && (
          <p className="hint">Upload a document to start asking questions.</p>
        )}
      </form>

      {status === "error" && (
        <p role="alert">{errorMessage}</p>
      )}

      {status === "answered" && answer !== null && (
        <section aria-live="polite">
          <h3>Answer</h3>
          <p>{answer.answer}</p>
          {answer.sources.length > 0 && (
            <>
              <h3>Sources</h3>
              <p className="sources-note">
                Ranked by cosine similarity to your question; matches below
                0.15 are filtered out. Labels reflect this system&apos;s
                measured score ranges.
              </p>
              <ul>
                {answer.sources.map((source, index) => (
                  <li key={`${source.document_id}-${index}`}>
                    <p>{source.chunk}</p>
                    <p>
                      <strong>{relevanceLabel(source.score)}</strong> · cosine
                      similarity {source.score.toFixed(3)} — document:{" "}
                      {source.document_id}
                    </p>
                  </li>
                ))}
              </ul>
            </>
          )}
        </section>
      )}
    </section>
  );
}
