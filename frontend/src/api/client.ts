import {
  ApiError,
  type AskRequest,
  type AskResponse,
  type DocumentDetail,
  type DocumentListResponse,
  type DocumentMeta,
  type ErrorResponse,
  type QueryRequest,
  type QueryResponse,
  type ValidationErrorResponse,
} from "./types";

// Empty string, not an absolute host: relies on the Vite dev proxy
// (vite.config.ts) forwarding /documents, /query, /ask to the backend, so
// the same relative paths keep working unchanged if production ever serves
// frontend and backend from one origin.
const BASE_URL = "";

function isErrorResponse(body: unknown): body is ErrorResponse {
  if (typeof body !== "object" || body === null || !("error" in body)) {
    return false;
  }
  const error = (body as { error: unknown }).error;
  return (
    typeof error === "object" &&
    error !== null &&
    "code" in error &&
    "message" in error
  );
}

function isValidationErrorResponse(
  body: unknown,
): body is ValidationErrorResponse {
  if (typeof body !== "object" || body === null || !("detail" in body)) {
    return false;
  }
  return Array.isArray((body as { detail: unknown }).detail);
}

// Reads a non-ok response body as `unknown` and narrows it into one of the
// two real error shapes the backend can send (see DECISIONS.md D5, Error
// handling) rather than assuming a single shape or reaching for `any`.
async function parseErrorResponse(response: Response): Promise<ApiError> {
  let body: unknown;
  try {
    body = await response.json();
  } catch {
    return new ApiError(response.status, "unknown_error", response.statusText);
  }

  if (isErrorResponse(body)) {
    return new ApiError(response.status, body.error.code, body.error.message);
  }
  if (isValidationErrorResponse(body)) {
    const message = body.detail.map((d) => d.msg).join("; ") || "Validation failed";
    return new ApiError(response.status, "validation_error", message);
  }
  return new ApiError(response.status, "unknown_error", response.statusText);
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${BASE_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...init?.headers,
    },
  });

  if (!response.ok) {
    throw await parseErrorResponse(response);
  }

  // 204 No Content (DELETE /documents/{id}) has no body — parsing it as
  // JSON would throw, so this must be special-cased before response.json().
  if (response.status === 204) {
    return undefined as T;
  }

  return (await response.json()) as T;
}

export function uploadDocument(
  title: string,
  content: string,
): Promise<DocumentMeta> {
  return request<DocumentMeta>("/documents", {
    method: "POST",
    body: JSON.stringify({ title, content }),
  });
}

export function listDocuments(): Promise<DocumentListResponse> {
  return request<DocumentListResponse>("/documents");
}

export function getDocument(id: string): Promise<DocumentDetail> {
  return request<DocumentDetail>(`/documents/${id}`);
}

export function deleteDocument(id: string): Promise<void> {
  return request<void>(`/documents/${id}`, { method: "DELETE" });
}

export function queryDocuments(
  question: string,
  k?: number,
): Promise<QueryResponse> {
  const body: QueryRequest = k === undefined ? { question } : { question, k };
  return request<QueryResponse>("/query", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function askQuestion(
  question: string,
  k?: number,
): Promise<AskResponse> {
  const body: AskRequest = k === undefined ? { question } : { question, k };
  return request<AskResponse>("/ask", {
    method: "POST",
    body: JSON.stringify(body),
  });
}
