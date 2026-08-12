/**
 * Thin API client. VITE_API_URL should point at the backend - when
 * accessing from your phone over wifi, this needs to be the laptop's
 * local IP (e.g. http://192.168.1.42:8000), not localhost, since
 * "localhost" on your phone means the phone itself.
 */
const API_URL = import.meta.env.VITE_API_URL ?? "/api";

export interface Author {
  id: string;
  name: string;
}

export interface Genre {
  id: string;
  name: string;
}

export interface Series {
  id: string;
  name: string;
}

export type ReadStatus = "unread" | "reading" | "read";

export interface Book {
  id: string;
  title: string;
  author: Author | null;
  series: Series | null;
  series_number: number | null;
  genres: Genre[];
  isbn: string | null;
  cover_url: string | null;
  description: string | null;
  page_count: number | null;
  publication_year: number | null;
  read_status: ReadStatus;
  rating: number | null;
  notes: string | null;
  date_added: string;
  date_finished: string | null;
}

export interface CreateBookInput {
  title: string;
  author_name?: string;
  genre_names?: string[];
  series_name?: string;
  series_number?: number;
  page_count?: number;
  publication_year?: number;
  read_status?: ReadStatus;
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`API error ${res.status}: ${body}`);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

export const api = {
  listBooks: (params?: { search?: string; genre?: string; read_status?: ReadStatus }) => {
    const qs = new URLSearchParams(params as Record<string, string>).toString();
    return request<Book[]>(`/books${qs ? `?${qs}` : ""}`);
  },
  getBook: (id: string) => request<Book>(`/books/${id}`),
  createBook: (input: CreateBookInput) =>
    request<Book>("/books", { method: "POST", body: JSON.stringify(input) }),
  updateBook: (id: string, input: Partial<CreateBookInput> & { rating?: number; notes?: string }) =>
    request<Book>(`/books/${id}`, { method: "PUT", body: JSON.stringify(input) }),
  deleteBook: (id: string) => request<void>(`/books/${id}`, { method: "DELETE" }),
  listAuthors: () => request<Author[]>("/authors"),
  listGenres: () => request<Genre[]>("/genres"),
  health: () => request<{ status: string }>("/health"),
};

export interface ScanCandidate {
  title: string;
  author_name: string | null;
  isbn: string | null;
  cover_url: string | null;
  publication_year: number | null;
  page_count: number | null;
  confidence: number;
}

export interface ScanIdentifyResult {
  raw_ocr_text: string;
  candidates: ScanCandidate[];
}

export interface ScanConfirmInput {
  title: string;
  author_name?: string;
  isbn?: string;
  cover_url?: string;
  publication_year?: number;
  page_count?: number;
  genre_names?: string[];
  raw_ocr_text?: string;
  ocr_confidence?: number;
}

export const scanApi = {
  identify: async (imageBlob: Blob): Promise<ScanIdentifyResult> => {
    const formData = new FormData();
    formData.append("image", imageBlob, "cover.jpg");
    const res = await fetch(`${API_URL}/scan/identify`, {
      method: "POST",
      body: formData,
    });
    if (!res.ok) throw new Error(`Scan identify failed: ${res.status}`);
    return res.json();
  },
  confirm: (input: ScanConfirmInput): Promise<Book> =>
    request<Book>("/scan/confirm", { method: "POST", body: JSON.stringify(input) }),
};
