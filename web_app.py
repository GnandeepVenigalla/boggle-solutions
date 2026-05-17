#!/usr/bin/env python3
"""
Boggle Solver Web App — Flask backend
Accepts a manual letter grid and returns all valid words with scores and paths.
"""

import time
from pathlib import Path
from flask import Flask, request, jsonify, send_from_directory

from boggle_solver import load_dictionary, solve

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 1 * 1024 * 1024   # 1 MB max (no images)

# ── Load dictionary once at startup ────────────────────────────
print("Loading dictionary …")
TRIE = load_dictionary(min_len=3)

USER_BANNED_FILE = Path(__file__).parent / "user_banned.txt"
USER_BANNED = set()
if USER_BANNED_FILE.exists():
    with open(USER_BANNED_FILE) as f:
        for line in f:
            USER_BANNED.add(line.strip().lower())
print(f"Loaded {len(USER_BANNED)} user-banned words.")
print("Ready!\n")

# ── Routes ──────────────────────────────────────────────────────
@app.route("/")
def index():
    return send_from_directory(".", "index.html")

@app.route("/solve", methods=["POST"])
def solve_route():
    """
    Accepts JSON: { "grid": [["a","b",...], ...] }
    Returns JSON: { total_words, total_score, elapsed, groups }
    """
    if not request.is_json:
        return jsonify({"error": "Send JSON with a 'grid' key."}), 400

    data = request.get_json()
    grid = data.get("grid")

    if not grid or not isinstance(grid, list):
        return jsonify({"error": "Missing or invalid 'grid'."}), 400

    # Normalise to lowercase strings
    grid = [[str(c).lower() for c in row] for row in grid]

    # Validate all cells are filled
    for row in grid:
        for cell in row:
            if not cell or cell == "?":
                return jsonify({"error": "Board has empty cells — fill all letters first."}), 400

    t0 = time.time()
    found = solve(grid, TRIE)
    elapsed = round(time.time() - t0, 3)

    # Group words by length
    groups: dict[int, list] = {}
    for word, info in found.items():
        if word.lower() in USER_BANNED:
            continue
        groups.setdefault(len(word), []).append({
            "word":  word.upper(),
            "score": info["score"],
            "path":  info["path"],
        })

    for length in groups:
        groups[length].sort(key=lambda x: x["word"])

    lengths_sorted = sorted(groups.keys(), reverse=True)
    result_groups = [{"length": l, "words": groups[l]} for l in lengths_sorted]

    total_words = sum(len(g["words"]) for g in result_groups)
    total_score = sum(w["score"] for g in result_groups for w in g["words"])

    return jsonify({
        "grid":        grid,
        "total_words": total_words,
        "total_score": total_score,
        "elapsed":     elapsed,
        "groups":      result_groups,
    })

@app.route("/ban", methods=["POST"])
def ban_route():
    data = request.get_json()
    word = data.get("word")
    if word:
        word = word.lower()
        if word not in USER_BANNED:
            USER_BANNED.add(word)
            with open(USER_BANNED_FILE, "a") as f:
                f.write(word + "\n")
    return jsonify({"status": "success"})

if __name__ == "__main__":
    print("\n🎲 Boggle Solver — http://localhost:5050\n")
    app.run(host="0.0.0.0", port=5050, debug=False)
# Vercel uses the 'app' object directly — no app.run() needed.
