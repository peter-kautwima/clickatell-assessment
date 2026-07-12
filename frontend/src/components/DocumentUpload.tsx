import { useState, type ChangeEvent, type FormEvent } from "react";
import { isBackendUnreachable, uploadDocument } from "../api/client";
import { ApiError, type DocumentMeta } from "../api/types";

interface DocumentUploadProps {
  onUploaded: (document: DocumentMeta) => void;
  /** Routes "no backend answered" to the app-level banner, keeping this
   * panel's message region for its own validation/upload errors. */
  onBackendDown: () => void;
}

type Status = "idle" | "submitting" | "success" | "error";

export function DocumentUpload({ onUploaded, onBackendDown }: DocumentUploadProps) {
  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");
  const [status, setStatus] = useState<Status>("idle");
  const [message, setMessage] = useState<string | null>(null);

  const canSubmit = title.trim() !== "" && content.trim() !== "";

  // Client-side read only: the backend accepts JSON {title, content}, not
  // multipart uploads, so the file's text is read in the browser and
  // submitted through the same endpoint as pasted content.
  const handleFileChange = async (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;
    try {
      const text = await file.text();
      setContent(text);
      if (title.trim() === "") {
        setTitle(file.name.replace(/\.(txt|md)$/i, ""));
      }
      setStatus("idle");
      setMessage(null);
    } catch {
      setStatus("error");
      setMessage(`Could not read "${file.name}"`);
    }
    // Allow re-selecting the same file after editing the textarea.
    event.target.value = "";
  };

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
      if (isBackendUnreachable(error)) {
        onBackendDown();
        setStatus("idle");
        return;
      }
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
            placeholder="Paste text here, or load a file below"
            required
          />
        </div>
        <div>
          <label htmlFor="upload-file">Or load from a file (.txt / .md)</label>
          <input
            id="upload-file"
            type="file"
            accept=".txt,.md,text/plain,text/markdown"
            onChange={handleFileChange}
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
