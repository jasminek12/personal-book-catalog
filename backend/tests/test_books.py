def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}

def test_create_book_with_author_and_genres(client):
    r = client.post("/books", json={
        "title": "The Hobbit",
        "author_name": "J.R.R. Tolkien",
        "genre_names": ["Fantasy", "Classic"],
    })
    assert r.status_code == 201
    body = r.json()
    assert body["title"] == "The Hobbit"
    assert body["author"]["name"] == "J.R.R. Tolkien"
    assert {g["name"] for g in body["genres"]} == {"Fantasy", "Classic"}
    assert body["read_status"] == "unread"
    assert body["identification_method"] == "manual"

def test_create_book_reuses_existing_author(client):
    r1 = client.post("/books", json={"title": "Dune", "author_name": "Frank Herbert"})
    r2 = client.post("/books", json={"title": "Dune Messiah", "author_name": "Frank Herbert"})
    assert r1.json()["author"]["id"] == r2.json()["author"]["id"]

def test_get_book_not_found(client):
    r = client.get("/books/00000000-0000-0000-0000-000000000000")
    assert r.status_code == 404

def test_list_books_filter_by_genre(client):
    client.post("/books", json={"title": "Foundation", "genre_names": ["Sci-Fi"]})
    client.post("/books", json={"title": "Pride and Prejudice", "genre_names": ["Romance"]})

    r = client.get("/books", params={"genre": "Sci-Fi"})
    assert r.status_code == 200
    titles = [b["title"] for b in r.json()]
    assert titles == ["Foundation"]

def test_list_books_search_by_title(client):
    client.post("/books", json={"title": "The Hunger Games"})
    client.post("/books", json={"title": "Catching Fire"})

    r = client.get("/books", params={"search": "hunger"})
    assert r.status_code == 200
    assert len(r.json()) == 1
    assert r.json()[0]["title"] == "The Hunger Games"

def test_list_books_filter_by_read_status(client):
    created = client.post("/books", json={"title": "1984"}).json()
    client.put(f"/books/{created['id']}", json={"read_status": "read"})
    client.post("/books", json={"title": "Brave New World"})

    r = client.get("/books", params={"read_status": "read"})
    assert r.status_code == 200
    assert [b["title"] for b in r.json()] == ["1984"]

def test_update_book_partial(client):
    created = client.post("/books", json={"title": "Neuromancer"}).json()

    r = client.put(f"/books/{created['id']}", json={"rating": 5})
    assert r.status_code == 200
    body = r.json()
    assert body["rating"] == 5
    assert body["title"] == "Neuromancer"  # untouched fields stay as-is

def test_update_book_changes_author(client):
    created = client.post("/books", json={"title": "Some Book", "author_name": "Author A"}).json()

    r = client.put(f"/books/{created['id']}", json={"author_name": "Author B"})
    assert r.status_code == 200
    assert r.json()["author"]["name"] == "Author B"

def test_delete_book(client):
    created = client.post("/books", json={"title": "To Delete"}).json()

    r = client.delete(f"/books/{created['id']}")
    assert r.status_code == 204

    r = client.get(f"/books/{created['id']}")
    assert r.status_code == 404

def test_delete_nonexistent_book(client):
    r = client.delete("/books/00000000-0000-0000-0000-000000000000")
    assert r.status_code == 404

def test_list_authors_and_genres(client):
    client.post("/books", json={
        "title": "Test Book",
        "author_name": "Test Author",
        "genre_names": ["Test Genre"],
    })

    authors = client.get("/authors").json()
    genres = client.get("/genres").json()
    assert any(a["name"] == "Test Author" for a in authors)
    assert any(g["name"] == "Test Genre" for g in genres)
