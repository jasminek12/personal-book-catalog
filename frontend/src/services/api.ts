const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

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
