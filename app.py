"""
My Recommendations — a movies & songs website.

A Flask app with SQLite persistence and a custom Python fuzzy-search
algorithm. Share the public URL and your list travels with you across
devices.
"""
import os
import sqlite3
import re
from datetime import datetime
from flask import (
    Flask, render_template, request, jsonify,
    redirect, url_for, send_from_directory, abort
)
from werkzeug.utils import secure_filename

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DB_PATH = os.path.join(BASE_DIR, "estate.db")
UPLOAD_DIR = os.path.join(BASE_DIR, "static", "uploads")
ALLOWED_EXT = {"png", "jpg", "jpeg", "gif", "webp"}

os.makedirs(UPLOAD_DIR, exist_ok=True)

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16 MB per upload
app.config["UPLOAD_FOLDER"] = UPLOAD_DIR


# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create the movies and songs tables if they don't exist."""
    with get_db() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS movies (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                title      TEXT    NOT NULL,
                year       INTEGER,
                image_url  TEXT,
                note       TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS songs (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                title        TEXT    NOT NULL,
                artist       TEXT    NOT NULL,
                album_image  TEXT,
                preview_url  TEXT,
                note         TEXT,
                created_at   TEXT DEFAULT CURRENT_TIMESTAMP
            );
        """)
        conn.commit()


init_db()


# ---------------------------------------------------------------------------
# Python Search Algorithm
# ---------------------------------------------------------------------------
# A custom fuzzy-ranked search. No external libraries — just honest Python.
# Scoring combines: exact substring hits, token overlap, and a tiny
# Levenshtein-style tolerance for typos. Results bubble up by relevance.
# ---------------------------------------------------------------------------
def _normalize(text):
    """Lowercase and strip non-alphanumerics to spaces."""
    if not text:
        return ""
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def _tokenize(text):
    return [t for t in _normalize(text).split() if t]


def _edit_distance(a, b, cap=2):
    """Bounded Levenshtein distance. Returns cap+1 if further than cap."""
    if abs(len(a) - len(b)) > cap:
        return cap + 1
    if a == b:
        return 0
    # Classic DP, early-exit when the row minimum exceeds the cap.
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        curr = [i] + [0] * len(b)
        row_min = curr[0]
        for j, cb in enumerate(b, 1):
            cost = 0 if ca == cb else 1
            curr[j] = min(
                curr[j - 1] + 1,       # insertion
                prev[j] + 1,           # deletion
                prev[j - 1] + cost     # substitution
            )
            if curr[j] < row_min:
                row_min = curr[j]
        if row_min > cap:
            return cap + 1
        prev = curr
    return prev[-1]


def score_item(query, fields):
    """
    Score how well `fields` (a list of strings) matches `query`.
    Higher is better. Returns 0 if no meaningful match.
    """
    if not query:
        return 0

    q_norm = _normalize(query)
    q_tokens = _tokenize(query)
    if not q_tokens:
        return 0

    haystack = _normalize(" ".join(f for f in fields if f))
    haystack_tokens = _tokenize(" ".join(f for f in fields if f))

    score = 0

    # (1) Exact full-phrase match is king.
    if q_norm and q_norm in haystack:
        score += 100
        # Bonus if it appears at the very start of a field.
        for field in fields:
            if _normalize(field).startswith(q_norm):
                score += 40
                break

    # (2) Token-level hits — covers reordered or partial queries.
    for qt in q_tokens:
        if not qt:
            continue
        # Substring hit on any token in the haystack.
        for ht in haystack_tokens:
            if qt == ht:
                score += 25
                break
            if qt in ht or ht in qt:
                score += 10
                break
        else:
            # Typo tolerance for tokens of 4+ characters.
            if len(qt) >= 4:
                best = min(
                    (_edit_distance(qt, ht, cap=2) for ht in haystack_tokens),
                    default=99,
                )
                if best == 1:
                    score += 8
                elif best == 2:
                    score += 3

    # (3) Coverage ratio — reward queries where most tokens land.
    hit_tokens = sum(
        1 for qt in q_tokens
        if any(qt in ht or ht in qt for ht in haystack_tokens)
    )
    if q_tokens:
        score += int(20 * (hit_tokens / len(q_tokens)))

    return score


def search_collection(query, limit=50):
    """Search movies and songs, return ranked results."""
    with get_db() as conn:
        movies = conn.execute("SELECT * FROM movies").fetchall()
        songs = conn.execute("SELECT * FROM songs").fetchall()

    results = []

    for m in movies:
        fields = [m["title"], str(m["year"] or ""), m["note"] or ""]
        s = score_item(query, fields) if query else 1
        if s > 0:
            results.append({
                "kind": "movie",
                "score": s,
                "data": dict(m),
            })

    for song in songs:
        fields = [song["title"], song["artist"], song["note"] or ""]
        s = score_item(query, fields) if query else 1
        if s > 0:
            results.append({
                "kind": "song",
                "score": s,
                "data": dict(song),
            })

    # Sort by score desc, then newest first within a tie.
    results.sort(key=lambda r: (-r["score"], -r["data"]["id"]))
    return results[:limit]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def allowed_file(filename):
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXT
    )


def save_uploaded_image(file_storage):
    """Save an uploaded file and return its public URL, or None."""
    if not file_storage or not file_storage.filename:
        return None
    if not allowed_file(file_storage.filename):
        return None
    fname = secure_filename(file_storage.filename)
    # Prefix with timestamp to avoid collisions.
    stamp = datetime.utcnow().strftime("%Y%m%d%H%M%S%f")
    fname = f"{stamp}_{fname}"
    file_storage.save(os.path.join(UPLOAD_DIR, fname))
    return url_for("uploaded_file", filename=fname)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.route("/")
def index():
    with get_db() as conn:
        movies = conn.execute(
            "SELECT * FROM movies ORDER BY id DESC"
        ).fetchall()
        songs = conn.execute(
            "SELECT * FROM songs ORDER BY id DESC"
        ).fetchall()
    return render_template(
        "index.html",
        movies=[dict(m) for m in movies],
        songs=[dict(s) for s in songs],
    )


@app.route("/uploads/<path:filename>")
def uploaded_file(filename):
    return send_from_directory(UPLOAD_DIR, filename)


# ---- Movies -------------------------------------------------------------
@app.route("/api/movies", methods=["POST"])
def add_movie():
    title = (request.form.get("title") or "").strip()
    year_raw = (request.form.get("year") or "").strip()
    image_url = (request.form.get("image_url") or "").strip()
    note = (request.form.get("note") or "").strip()

    if not title:
        return jsonify({"error": "Title is required"}), 400

    try:
        year = int(year_raw) if year_raw else None
    except ValueError:
        return jsonify({"error": "Year must be a number"}), 400

    # If a file was uploaded, prefer it over the URL.
    uploaded = save_uploaded_image(request.files.get("image_file"))
    if uploaded:
        image_url = uploaded

    with get_db() as conn:
        cur = conn.execute(
            "INSERT INTO movies (title, year, image_url, note) "
            "VALUES (?, ?, ?, ?)",
            (title, year, image_url or None, note or None),
        )
        conn.commit()
        new_id = cur.lastrowid
        row = conn.execute(
            "SELECT * FROM movies WHERE id = ?", (new_id,)
        ).fetchone()

    return jsonify({"movie": dict(row)}), 201


@app.route("/api/movies/<int:movie_id>", methods=["DELETE"])
def delete_movie(movie_id):
    with get_db() as conn:
        conn.execute("DELETE FROM movies WHERE id = ?", (movie_id,))
        conn.commit()
    return jsonify({"ok": True})


# ---- Songs --------------------------------------------------------------
@app.route("/api/songs", methods=["POST"])
def add_song():
    title = (request.form.get("title") or "").strip()
    artist = (request.form.get("artist") or "").strip()
    album_image = (request.form.get("album_image") or "").strip()
    preview_url = (request.form.get("preview_url") or "").strip()
    note = (request.form.get("note") or "").strip()

    if not title or not artist:
        return jsonify({"error": "Title and artist are required"}), 400

    uploaded = save_uploaded_image(request.files.get("image_file"))
    if uploaded:
        album_image = uploaded

    with get_db() as conn:
        cur = conn.execute(
            "INSERT INTO songs (title, artist, album_image, preview_url, note) "
            "VALUES (?, ?, ?, ?, ?)",
            (title, artist, album_image or None, preview_url or None, note or None),
        )
        conn.commit()
        new_id = cur.lastrowid
        row = conn.execute(
            "SELECT * FROM songs WHERE id = ?", (new_id,)
        ).fetchone()

    return jsonify({"song": dict(row)}), 201


@app.route("/api/songs/<int:song_id>", methods=["DELETE"])
def delete_song(song_id):
    with get_db() as conn:
        conn.execute("DELETE FROM songs WHERE id = ?", (song_id,))
        conn.commit()
    return jsonify({"ok": True})


# ---- Search -------------------------------------------------------------
@app.route("/api/search")
def api_search():
    query = (request.args.get("q") or "").strip()
    kind = (request.args.get("kind") or "all").strip().lower()
    results = search_collection(query) if query else []

    if kind in ("movies", "movie"):
        results = [r for r in results if r["kind"] == "movie"]
    elif kind in ("songs", "song"):
        results = [r for r in results if r["kind"] == "song"]

    return jsonify({"query": query, "count": len(results), "results": results})


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    # Host 0.0.0.0 so the site is reachable across the network when
    # deployed or run on a LAN. Port can be overridden via env.
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
