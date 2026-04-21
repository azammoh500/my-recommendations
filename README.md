# My Recommendations — Movies & Songs

A personal website for keeping track of movies and songs you'd recommend.
Warm, simple design. Data saves to a database so your list persists across
reloads and across devices for anyone who visits the URL.

---

## What's inside

- **Flask backend** (`app.py`) with a SQLite database (`estate.db`) that
  auto-creates on first run.
- **Custom Python search algorithm** — token-weighted fuzzy matcher with
  typo tolerance. No external search library.
- **Image uploads** (stored to disk) or image URLs (pasted in).
- **30-second Spotify previews** that play inline when you paste the
  preview `.mp3` URL.
- **Mobile-friendly**, responsive layout.

---

## Run it locally (2 minutes)

```
pip install -r requirements.txt
python app.py
```

Open http://localhost:5000. The database file `estate.db` is created
automatically on first launch. Uploaded images land in `static/uploads/`.

---

## Make it shareable on the internet

See **DEPLOYMENT-GUIDE.md** for a no-terminal walkthrough using Render.

---

## Getting a Spotify preview URL

Spotify's 30-second previews live at URLs like
`https://p.scdn.co/mp3-preview/abc123...`. To find one:

1. Search for the track on [open.spotify.com](https://open.spotify.com).
2. Copy the track link.
3. Paste it into a preview-URL finder (search "spotify track preview url"
   — several small web tools do this) *or* use Spotify's Web API
   `/tracks/{id}` endpoint, which returns a `preview_url` field.

Paste the resulting `.mp3` URL into the "Spotify preview URL" field when
adding a song. A play button will appear on the cover.

---

## The search algorithm (Python)

In `app.py`, see `search_collection()` + `score_item()`. Three signals,
combined into a single score:

1. **Exact phrase match** in any field → +100, plus +40 if it starts the field.
2. **Token overlap** — each query token that hits a haystack token adds points.
3. **Typo tolerance** — bounded Levenshtein (cap = 2) for tokens ≥ 4 chars.

Plus a coverage-ratio bonus for how much of your query actually landed.
Results sort by score, newest first for ties.

So `"budapst"` finds *The Grand Budapest Hotel*, `"2014"` finds anything
from that year, and `"wes ander"` finds Wes Anderson — whether it's in a
title, year, artist, or note.

---

## Project structure

```
cmbyn-recs/
├── app.py                      # Flask app + DB + search algorithm
├── requirements.txt
├── Procfile                    # For deployment
├── estate.db                   # SQLite DB (auto-created)
├── templates/
│   └── index.html
└── static/
    ├── css/style.css
    ├── js/app.js
    └── uploads/                # User-uploaded images
```

---

## A note on privacy

Anyone with the URL can add, view, and delete items — there's no login.
If you want it to be yours-only or friends-only later, user accounts can
be added. For now, treat the link the way you'd treat a shared doc.
