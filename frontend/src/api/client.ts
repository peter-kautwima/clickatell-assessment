import type { DocumentUploadResponse, QueryResponse } from "./types";

const BASE_URL = "/";

export async function uploadDocument(
  file: File,
): Promise<DocumentUploadResponse> {
  const form = new FormData();
  form.append("file", file);

  const response = await fetch(`${BASE_URL}documents`, {
    method: "POST",
    body: form,
  });

  return response.json();
}

export async function queryDocuments(): Promise<QueryResponse> {
  const response = await fetch(`${BASE_URL}query`);
  return response.json();
}
