import { useState, type FormEvent } from "react";
import { askQuestion } from "../api/client";
import { ApiError, type AskResponse } from "../api/types";

type Status = "idle" | "loading" | "answered" | "error";

export function QAPanel() {
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
      setStatus("error");
      setErrorMessage(error instanceof ApiError ? error.message : "Ask failed");
    }
  };

  return (
    <section>
      <h2>Q&amp;A</h2>
      <form onSubmit={handleSubmit} aria-busy={status === "loading"}>
        <label htmlFor="qa-question">Question</label>
        <input
          id="qa-question"
          type="text"
          value={question}
          onChange={(event) => setQuestion(event.target.value)}
          required
        />
        <button type="submit" disabled={question.trim() === "" || status === "loading"}>
          {status === "loading" ? "Asking…" : "Ask"}
        </button>
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
              <ul>
                {answer.sources.map((source, index) => (
                  <li key={`${source.document_id}-${index}`}>
                    <p>{source.chunk}</p>
                    <p>
                      document: {source.document_id} — score:{" "}
                      {source.score.toFixed(3)}
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
