import { useState, type FormEvent } from "react";
import { api } from "../services/api";

export function AddBookForm({ onAdded }: { onAdded: () => void }) {
  const [title, setTitle] = useState("");
  const [author, setAuthor] = useState("");
  const [genres, setGenres] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!title.trim()) return;
    setSubmitting(true);
    try {
      await api.createBook({
        title: title.trim(),
        author_name: author.trim() || undefined,
        genre_names: genres
          .split(",")
          .map((g) => g.trim())
          .filter(Boolean),
      });
      setTitle("");
      setAuthor("");
      setGenres("");
      onAdded();
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap" }}>
      <input
        placeholder="Title"
        value={title}
        onChange={(e) => setTitle(e.target.value)}
        required
      />
      <input
        placeholder="Author (optional)"
        value={author}
        onChange={(e) => setAuthor(e.target.value)}
      />
      <input
        placeholder="Genres, comma separated (optional)"
        value={genres}
        onChange={(e) => setGenres(e.target.value)}
      />
      <button type="submit" disabled={submitting}>
        {submitting ? "Adding..." : "Add book"}
      </button>
    </form>
  );
}
