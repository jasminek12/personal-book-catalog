import { useEffect, useState } from "react";
import { api, type Book, type ReadStatus } from "../services/api";
import { AddBookForm } from "../components/AddBookForm";
import { BookCard } from "../components/BookCard";
import { CaptureBook } from "../components/CaptureBook";

export function Library() {
  const [books, setBooks] = useState<Book[]>([]);
  const [filter, setFilter] = useState<ReadStatus | "all">("all");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadBooks = async () => {
    setLoading(true);
    setError(null);
    try {
      const results = await api.listBooks(
        filter === "all" ? undefined : { read_status: filter }
      );
      setBooks(results);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load books");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadBooks();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filter]);

  const handleDelete = async (id: string) => {
    await api.deleteBook(id);
    loadBooks();
  };

  return (
    <div style={{ maxWidth: 720, margin: "0 auto", padding: "1rem" }}>
      <h1>MyBookVault</h1>

      <CaptureBook onBookAdded={loadBooks} />

      <details style={{ marginBottom: "1rem" }}>
        <summary>Add manually instead</summary>
        <div style={{ marginTop: "0.5rem" }}>
          <AddBookForm onAdded={loadBooks} />
        </div>
      </details>

      <div style={{ margin: "1rem 0", display: "flex", gap: "0.5rem" }}>
        {(["all", "unread", "reading", "read"] as const).map((status) => (
          <button
            key={status}
            onClick={() => setFilter(status)}
            style={{
              fontWeight: filter === status ? "bold" : "normal",
              padding: "0.4rem 0.8rem",
            }}
          >
            {status}
          </button>
        ))}
      </div>

      {loading && <p>Loading...</p>}
      {error && <p style={{ color: "crimson" }}>{error}</p>}
      {!loading && !error && books.length === 0 && <p>No books yet. Add one above.</p>}

      <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
        {books.map((book) => (
          <BookCard key={book.id} book={book} onDelete={() => handleDelete(book.id)} />
        ))}
      </div>
    </div>
  );
}
