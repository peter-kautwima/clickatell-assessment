import { useCallback, useEffect, useState } from "react";
import { listDocuments } from "./api/client";
import { ApiError, type DocumentMeta } from "./api/types";
import { DocumentUpload } from "./components/DocumentUpload";
import { DocumentList } from "./components/DocumentList";
import { QAPanel } from "./components/QAPanel";

type DocumentsStatus = "idle" | "loading" | "loaded" | "error";

function App() {
  const [documents, setDocuments] = useState<DocumentMeta[]>([]);
  const [documentsStatus, setDocumentsStatus] = useState<DocumentsStatus>("idle");
  const [documentsError, setDocumentsError] = useState<string | null>(null);

  const refreshDocuments = useCallback(async () => {
    setDocumentsStatus("loading");
    setDocumentsError(null);
    try {
      const response = await listDocuments();
      setDocuments(response.documents);
      setDocumentsStatus("loaded");
    } catch (error) {
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
      <div className="panels">
        <DocumentUpload onUploaded={refreshDocuments} />
        <DocumentList
          documents={documents}
          status={documentsStatus}
          error={documentsError}
          onRefresh={refreshDocuments}
        />
      </div>
      <QAPanel
        hasDocuments={documents.length > 0}
        documentsLoaded={documentsStatus === "loaded"}
      />
    </main>
  );
}

export default App;
