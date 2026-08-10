import type { Book } from "../services/api";

export function BookCard({ book, onDelete }: { book: Book; onDelete: () => void }) {
  return (
    <div style={{ border: "1px solid #334155", borderRadius: 8, padding: "0.75rem" }}>
      <div style={{ display: "flex", justifyContent: "space-between" }}>
        <strong>{book.title}</strong>
        <button onClick={onDelete} style={{ color: "crimson" }}>
          delete
        </button>
      </div>
      {book.author && <div>by {book.author.name}</div>}
      {book.genres.length > 0 && (
        <div style={{ fontSize: "0.85rem", opacity: 0.8 }}>
          {book.genres.map((g) => g.name).join(", ")}
        </div>
      )}
      <div style={{ fontSize: "0.85rem", opacity: 0.6 }}>{book.read_status}</div>
    </div>
  );
}
