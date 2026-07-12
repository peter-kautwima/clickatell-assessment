/** TypeScript mirrors of every Pydantic model in
 * backend/app/models/schemas.py — one interface per model, same field
 * names/optionality as the wire JSON (snake_case, not renamed to camelCase)
 * so this file stays a faithful 1:1 mirror rather than a translation layer.
 */

export interface DocumentCreate {
  title: string;
  content: string;
}

export interface DocumentMeta {
  id: string;
  title: string;
  chunk_count: number;
  uploaded_at: string;
}

export interface DocumentDetail extends DocumentMeta {
  chunks: string[];
}

export interface DocumentListResponse {
  documents: DocumentMeta[];
}

export interface QueryRequest {
  question: string;
  k?: number;
}

export interface QueryResult {
  document_id: string;
  chunk: string;
  score: number;
}

export interface QueryResponse {
  results: QueryResult[];
}

export interface AskRequest {
  question: string;
  k?: number;
}

export interface AskResponse {
  answer: string;
  sources: QueryResult[];
}

export interface ErrorDetail {
  code: string;
  message: string;
}

export interface ErrorResponse {
  error: ErrorDetail;
}

/** FastAPI's built-in 422 validation-error shape — not overridden by any
 * custom handler in backend/app/main.py, so the client must recognize this
 * shape separately from ErrorResponse.
 */
export interface ValidationErrorDetail {
  loc: (string | number)[];
  msg: string;
  type: string;
}

export interface ValidationErrorResponse {
  detail: ValidationErrorDetail[];
}

/** The single normalized error shape components consume — api/client.ts
 * folds both ErrorResponse and ValidationErrorResponse into this so callers
 * never need to know two wire shapes exist.
 */
export class ApiError extends Error {
  readonly status: number;
  readonly code: string;

  constructor(status: number, code: string, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
  }
}
