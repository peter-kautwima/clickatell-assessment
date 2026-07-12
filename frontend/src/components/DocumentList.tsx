import { useState } from "react";
import { deleteDocument } from "../api/client";
import { ApiError, type DocumentMeta } from "../api/types";

type Status = "idle" | "loading" | "loaded" | "error";

interface DocumentListProps {
  documents: DocumentMeta[];
  status: Status;
  error: string | null;
  onRefresh: () => void;
}

export function DocumentList({
  documents,
  status,
  error,
  onRefresh,
}: DocumentListProps) {
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [deleteError, setDeleteError] = useState<string | null>(null);

  const handleDelete = async (id: string) => {
    setDeletingId(id);
    setDeleteError(null);
    try {
      await deleteDocument(id);
      onRefresh();
    } catch (caught) {
      setDeleteError(
        caught instanceof ApiError ? caught.message : "Delete failed",
      );
    } finally {
      setDeletingId(null);
    }
  };

  return (
    <section>
      <h2>Documents</h2>
      <div aria-live="polite">
        {deleteError !== null && <p role="alert">{deleteError}</p>}
        {status === "loading" && <p>Loading documents…</p>}
        {status === "error" && (
          <p role="alert">
            {error ?? "Failed to load documents."}{" "}
            <button type="button" onClick={onRefresh}>
              Retry
            </button>
          </p>
        )}
        {status === "loaded" && documents.length === 0 && (
          <p>No documents uploaded yet.</p>
        )}
        {status === "loaded" && documents.length > 0 && (
          <ul>
            {documents.map((document) => (
              <li key={document.id}>
                <span>{document.title}</span>{" "}
                <span>({document.chunk_count} chunks)</span>{" "}
                <span>{new Date(document.uploaded_at).toLocaleString()}</span>{" "}
                <button
                  type="button"
                  aria-label={`Delete ${document.title}`}
                  onClick={() => handleDelete(document.id)}
                  disabled={deletingId === document.id}
                >
                  {deletingId === document.id ? "Deleting…" : "Delete"}
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
    </section>
  );
}
