import { useCallback, useEffect, useState } from "react";
import {
  BACKEND_UNREACHABLE_MESSAGE,
  isBackendUnreachable,
  listDocuments,
} from "./api/client";
import { ApiError, type DocumentMeta } from "./api/types";
import { DocumentUpload } from "./components/DocumentUpload";
import { DocumentList } from "./components/DocumentList";
import { QAPanel } from "./components/QAPanel";

type DocumentsStatus = "idle" | "loading" | "loaded" | "error";

function App() {
  const [documents, setDocuments] = useState<DocumentMeta[]>([]);
  const [documentsStatus, setDocumentsStatus] = useState<DocumentsStatus>("idle");
  const [documentsError, setDocumentsError] = useState<string | null>(null);
  // One page-level flag for "no backend answered at all", so every panel's
  // failure funnels into a single banner instead of stacking raw errors.
  const [backendDown, setBackendDown] = useState(false);

  const reportBackendDown = useCallback(() => setBackendDown(true), []);

  const refreshDocuments = useCallback(async () => {
    setDocumentsStatus("loading");
    setDocumentsError(null);
    try {
      const response = await listDocuments();
      setDocuments(response.documents);
      setDocumentsStatus("loaded");
      setBackendDown(false);
    } catch (error) {
      if (isBackendUnreachable(error)) {
        // The banner carries the message; "idle" keeps the list from
        // rendering a second copy of the same failure.
        setBackendDown(true);
        setDocumentsStatus("idle");
        return;
      }
      setDocumentsError(
        error instanceof ApiError ? error.message : "Failed to load documents",
      );
      setDocumentsStatus("error");
    }
  }, []);

  useEffect(() => {
    refreshDocuments();
  }, [refreshDocuments]);

  return (
    <main>
      <h1>Document Q&amp;A</h1>
      {backendDown && (
        <p role="alert" className="banner">
          {BACKEND_UNREACHABLE_MESSAGE}
          <button
            type="button"
            onClick={refreshDocuments}
            disabled={documentsStatus === "loading"}
          >
            Retry
          </button>
        </p>
      )}
      <div className="panels">
        <DocumentUpload
          onUploaded={refreshDocuments}
          onBackendDown={reportBackendDown}
        />
        <DocumentList
          documents={documents}
          status={documentsStatus}
          error={documentsError}
          onRefresh={refreshDocuments}
          onBackendDown={reportBackendDown}
        />
      </div>
      <QAPanel
        hasDocuments={documents.length > 0}
        documentsLoaded={documentsStatus === "loaded"}
        onBackendDown={reportBackendDown}
      />
    </main>
  );
}

export default App;
