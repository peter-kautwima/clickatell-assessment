import { useState, type FormEvent } from "react";
import { uploadDocument } from "../api/client";
import { ApiError, type DocumentMeta } from "../api/types";

interface DocumentUploadProps {
  onUploaded: (document: DocumentMeta) => void;
}

type Status = "idle" | "submitting" | "success" | "error";

export function DocumentUpload({ onUploaded }: DocumentUploadProps) {
  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");
  const [status, setStatus] = useState<Status>("idle");
  const [message, setMessage] = useState<string | null>(null);

  const canSubmit = title.trim() !== "" && content.trim() !== "";

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!canSubmit) return;

    setStatus("submitting");
    setMessage(null);
    try {
      const document = await uploadDocument(title, content);
      setStatus("success");
      setMessage(`Uploaded "${document.title}" — ${document.chunk_count} chunks`);
      setTitle("");
      setContent("");
      onUploaded(document);
    } catch (error) {
      setStatus("error");
      setMessage(error instanceof ApiError ? error.message : "Upload failed");
    }
  };

  return (
    <section>
      <h2>Upload Document</h2>
      <form onSubmit={handleSubmit} aria-busy={status === "submitting"}>
        <div>
          <label htmlFor="upload-title">Title</label>
          <input
            id="upload-title"
            type="text"
            value={title}
            onChange={(event) => setTitle(event.target.value)}
            required
          />
        </div>
        <div>
          <label htmlFor="upload-content">Content</label>
          <textarea
            id="upload-content"
            value={content}
            onChange={(event) => setContent(event.target.value)}
            required
          />
        </div>
        <button type="submit" disabled={!canSubmit || status === "submitting"}>
          {status === "submitting" ? "Uploading…" : "Upload"}
        </button>
      </form>
      {message !== null && (
        <p role={status === "error" ? "alert" : "status"}>{message}</p>
      )}
    </section>
  );
}
