#!/usr/bin/env python3
"""
🎲 Boggle Solver
----------------
Give it an image of your Boggle board (or type the letters yourself)
and it finds every valid word — sorted by length and score.

Usage:
    python3 boggle_solver.py              ← launches menu
    python3 boggle_solver.py board.jpg    ← solve directly from image
"""

import sys
import os
import time
import subprocess
from pathlib import Path

# ──────────────────────────────────────────────
# TRIE DATA STRUCTURE (fast prefix lookup)
# ──────────────────────────────────────────────
class TrieNode:
    __slots__ = ("children", "is_word")
    def __init__(self):
        self.children = {}
        self.is_word = False

class Trie:
    def __init__(self):
        self.root = TrieNode()

    def insert(self, word: str):
        node = self.root
        for ch in word:
            if ch not in node.children:
                node.children[ch] = TrieNode()
            node = node.children[ch]
        node.is_word = True

    def search_prefix(self, prefix: str):
        """Returns (prefix_exists, is_complete_word)"""
        node = self.root
        for ch in prefix:
            if ch not in node.children:
                return False, False
            node = node.children[ch]
        return True, node.is_word

# ──────────────────────────────────────────────
# LOAD DICTIONARY
# ──────────────────────────────────────────────
SCRIPT_DIR      = Path(__file__).parent
SCRABBLE_FILE   = SCRIPT_DIR / "scrabble_words.txt"   # preferred: no proper nouns/archaic
WORD_FILE       = SCRIPT_DIR / "words_alpha.txt"       # fallback
BAD_WORDS_FILE  = SCRIPT_DIR / "bad_words.txt"         # profanity filter

def load_dictionary(min_len=3) -> Trie:
    trie = Trie()

    # Prefer scrabble word list (cleaner, matches word-game rules)
    if SCRABBLE_FILE.exists():
        src = SCRABBLE_FILE
        label = "Scrabble"
    elif WORD_FILE.exists():
        src = WORD_FILE
        label = "words_alpha"
    else:
        print("⚠️  No dictionary found — downloading …")
        url = "https://raw.githubusercontent.com/raun/Scrabble/master/words.txt"
        import subprocess
        subprocess.run(["curl", "-s", url, "-o", str(SCRABBLE_FILE)], check=True)
        src = SCRABBLE_FILE
        label = "Scrabble"

    # Load bad words
    bad_words = set()
    if BAD_WORDS_FILE.exists():
        with open(BAD_WORDS_FILE) as f:
            for line in f:
                bad_words.add(line.strip().lower())

    count = 0
    with open(src) as f:
        for line in f:
            word = line.strip().lower()
            if word in bad_words:
                continue
            if len(word) >= min_len and word.isalpha():
                trie.insert(word)
                count += 1
    print(f"  ✓  Loaded {count:,} words from {label} dictionary (filtered {len(bad_words)} bad words)\n")
    return trie

# ──────────────────────────────────────────────
# GAME RULES  (matches the Netflix Boggle app)
# ──────────────────────────────────────────────
# Scoring: each letter beyond the 2nd = 1 pt
#   3 letters = 1 pt,  4 = 2 pts,  5 = 3 pts, etc.
# ✅ Accepted : common/everyday English words, plurals, past tense
# ❌ Rejected : abbreviations, proper nouns/adjectives,
#               names (e.g. Jane, Pepsi), archaic words,
#               strongly offensive words
# Note: our dictionary (words_alpha) is broad; it may include
# some archaic/rare words the app wouldn't accept — those are rare.
def word_score(word: str) -> int:
    n = len(word)
    if n < 3:  return 0
    return n - 2   # 3→1pt, 4→2pt, 5→3pt, 6→4pt …

def get_neighbors(r: int, c: int, rows: int, cols: int):
    for dr in (-1, 0, 1):
        for dc in (-1, 0, 1):
            if dr == 0 and dc == 0:
                continue
            nr, nc = r + dr, c + dc
            if 0 <= nr < rows and 0 <= nc < cols:
                yield nr, nc

def solve(grid: list[list[str]], trie: Trie) -> dict:
    """Returns {word: {score, path}} where path is list of [r,c] positions."""
    rows, cols = len(grid), len(grid[0])
    found: dict = {}   # word -> {"score": int, "path": list[list[int]]}

    def dfs(r, c, visited, path_str, cell_path, node):
        ch = grid[r][c]
        letters = "qu" if ch == "q" else ch
        for letter in letters:
            if letter not in node.children:
                return
            node = node.children[letter]
            path_str += letter

        if node.is_word and len(path_str) >= 3 and path_str not in found:
            found[path_str] = {"score": word_score(path_str), "path": list(cell_path)}

        visited.add((r, c))
        for nr, nc in get_neighbors(r, c, rows, cols):
            if (nr, nc) not in visited:
                dfs(nr, nc, visited, path_str, cell_path + [[nr, nc]], node)
        visited.remove((r, c))

    for r in range(rows):
        for c in range(cols):
            dfs(r, c, set(), "", [[r, c]], trie.root)

    return found

# ──────────────────────────────────────────────
# IMAGE → GRID  (two strategies)
# ──────────────────────────────────────────────
def extract_grid_from_image(image_path: str) -> list[list[str]] | None:
    """
    Strategy 1: Use pytesseract OCR on the cropped grid cells.
    Strategy 2: Ask Google Gemini (free tier) if tesseract fails.
    Returns a 2-D list of single lowercase letters, or None.
    """
    try:
        from PIL import Image
        import pytesseract, re

        img = Image.open(image_path).convert("L")   # grayscale
        W, H = img.size

        # ── Try to detect grid size ──────────────────────
        # Common Boggle boards: 4x4 (standard) or 5x5 (Big Boggle)
        # We'll attempt 4x4 first, allow user to override.
        grid_size = 4
        cell_w, cell_h = W // grid_size, H // grid_size

        grid = []
        all_ok = True
        for row in range(grid_size):
            row_letters = []
            for col in range(grid_size):
                x1 = col * cell_w
                y1 = row * cell_h
                x2 = x1 + cell_w
                y2 = y1 + cell_h
                cell = img.crop((x1, y1, x2, y2))

                # Scale up for better OCR
                cell = cell.resize((cell.width * 4, cell.height * 4), Image.LANCZOS)

                # Threshold
                cell = cell.point(lambda p: 255 if p > 128 else 0)

                letter = pytesseract.image_to_string(
                    cell,
                    config="--psm 10 --oem 3 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ"
                ).strip().lower()

                letter = re.sub(r"[^a-z]", "", letter)
                if not letter:
                    all_ok = False
                    letter = "?"
                row_letters.append(letter[0] if letter else "?")
            grid.append(row_letters)

        if not all_ok:
            print("  ⚠️  Some cells could not be read by OCR.")
            return grid   # return partial so user can fix

        return grid

    except ImportError:
        print("  ⚠️  pytesseract/Pillow not installed — skipping image OCR.")
        return None
    except Exception as e:
        print(f"  ⚠️  Image reading error: {e}")
        return None

# ──────────────────────────────────────────────
# DISPLAY HELPERS
# ──────────────────────────────────────────────
BLUE   = "\033[94m"
GREEN  = "\033[92m"
YELLOW = "\033[93m"
CYAN   = "\033[96m"
BOLD   = "\033[1m"
RESET  = "\033[0m"
DIM    = "\033[2m"

def banner():
    print(f"""
{BOLD}{BLUE}╔══════════════════════════════════════════╗
║   🎲  B O G G L E   S O L V E R   🎲    ║
╚══════════════════════════════════════════╝{RESET}
""")

def print_grid(grid: list[list[str]]):
    print(f"\n{CYAN}{'─'*20}{RESET}")
    for row in grid:
        print("  " + "  ".join(f"{BOLD}{c.upper():>2}{RESET}" for c in row))
    print(f"{CYAN}{'─'*20}{RESET}\n")

def print_results(found: dict[str, int], grid: list[list[str]]):
    if not found:
        print(f"{YELLOW}  No words found. Check your grid letters.{RESET}")
        return

    # Sort: longest first, then alphabetical
    words_sorted = sorted(found.items(), key=lambda x: (-len(x[0]), x[0]))
    total_score  = sum(found.values())
    total_words  = len(found)

    # Group by length
    groups: dict[int, list] = {}
    for w, s in words_sorted:
        groups.setdefault(len(w), []).append((w, s))

    print(f"\n{BOLD}{GREEN}  ✅  Found {total_words} words  |  Total score: {total_score} pts{RESET}\n")

    for length in sorted(groups.keys(), reverse=True):
        pairs = groups[length]
        label = f"{length}-letter words ({len(pairs)})"
        print(f"  {CYAN}{BOLD}{label}{RESET}")
        # Print 4 per row
        row_buf = []
        for w, s in sorted(pairs, key=lambda x: x[0]):
            row_buf.append(f"{BOLD}{w.upper():<12}{RESET}{DIM}[{s}pt]{RESET}")
            if len(row_buf) == 4:
                print("    " + "  ".join(row_buf))
                row_buf = []
        if row_buf:
            print("    " + "  ".join(row_buf))
        print()

    print(f"  {DIM}Scoring: 3 letters=1pt, 4=2pt, 5=3pt, 6=4pt … (length − 2 pts each){RESET}\n")

# ──────────────────────────────────────────────
# INPUT HELPERS
# ──────────────────────────────────────────────
def ask_grid_manually(size: int = 4) -> list[list[str]]:
    """
    Let the user type the letters row by row.
    """
    print(f"\n{YELLOW}  Enter the board letters row by row.")
    print(f"  For a {size}x{size} board, type {size} letters per row (space-separated or together).")
    print(f"  Use 'Qu' as 'Q' — it will be handled automatically.{RESET}\n")

    grid = []
    while len(grid) < size:
        row_num = len(grid) + 1
        raw = input(f"  Row {row_num}: ").strip().lower()
        # Accept with or without spaces / commas
        import re
        letters = re.findall(r"[a-z]+", raw)
        # Flatten to individual letters (handles "qu" as one tile)
        flat = []
        i = 0
        for token in letters:
            j = 0
            while j < len(token):
                if token[j] == "q" and j + 1 < len(token) and token[j+1] == "u":
                    flat.append("q")   # store as 'q', solver handles 'qu'
                    j += 2
                else:
                    flat.append(token[j])
                    j += 1
        if len(flat) < size:
            print(f"  ❌  Need {size} letters, got {len(flat)}. Try again.")
            continue
        grid.append(flat[:size])

    return grid

def fix_grid_interactively(grid: list[list[str]]) -> list[list[str]]:
    """Show current grid; let user fix any bad cells."""
    print("\n  Current board (? = unread):")
    print_grid(grid)
    while True:
        fix = input("  Fix a cell? Enter row,col,letter (e.g. 2,3,T) or press Enter to continue: ").strip()
        if not fix:
            break
        try:
            parts = fix.replace(" ", "").split(",")
            r, c, l = int(parts[0]) - 1, int(parts[1]) - 1, parts[2].lower()[0]
            grid[r][c] = l
            print_grid(grid)
        except Exception:
            print("  ❌  Bad input. Use format: row,col,letter")
    return grid

def choose_grid_size() -> int:
    raw = input("\n  Board size? (4 for 4×4, 5 for 5×5) [default 4]: ").strip()
    return 5 if raw == "5" else 4

# ──────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────
def main():
    banner()

    # ── Load dictionary first ────────────────
    print("  Loading dictionary …")
    trie = load_dictionary(min_len=3)

    # ── Determine grid source ─────────────────
    grid = None

    if len(sys.argv) > 1:
        # Image path passed on command line
        image_path = sys.argv[1]
        if not os.path.exists(image_path):
            print(f"  ❌  File not found: {image_path}")
            sys.exit(1)
        print(f"  📷  Reading image: {image_path} …")
        grid = extract_grid_from_image(image_path)

    if grid is None:
        # Interactive menu
        while True:
            print(f"  {BOLD}How would you like to enter the board?{RESET}")
            print("   [1]  Load from image file")
            print("   [2]  Type letters manually")
            print("   [3]  Quit\n")
            choice = input("  Your choice: ").strip()

            if choice == "1":
                path = input("  Image path (or drag file here): ").strip().strip("'\"")
                if not os.path.exists(path):
                    print(f"  ❌  File not found: {path}\n")
                    continue
                print(f"  📷  Reading image …")
                grid = extract_grid_from_image(path)
                if grid is None:
                    print("  ⚠️  Falling back to manual entry.\n")
                    size = choose_grid_size()
                    grid = ask_grid_manually(size)
                break

            elif choice == "2":
                size = choose_grid_size()
                grid = ask_grid_manually(size)
                break

            elif choice == "3":
                print("  Bye! 👋")
                sys.exit(0)

    # If any '?' in grid, let user fix
    flat = [c for row in grid for c in row]
    if "?" in flat:
        print("\n  ⚠️  Some letters could not be read from the image.")
        grid = fix_grid_interactively(grid)
    else:
        print("  ✓  Board read successfully!")
        print_grid(grid)
        confirm = input("  Does the board look correct? (y/n) [y]: ").strip().lower()
        if confirm == "n":
            grid = fix_grid_interactively(grid)

    # ── Solve ─────────────────────────────────
    print(f"\n  {CYAN}Solving …{RESET}")
    t0 = time.time()
    found = solve(grid, trie)
    elapsed = time.time() - t0
    print(f"  Done in {elapsed:.2f}s")

    # ── Show results ──────────────────────────
    print_results(found, grid)

    # ── Save to file ──────────────────────────
    out_file = SCRIPT_DIR / "answers.txt"
    words_sorted = sorted(found.items(), key=lambda x: (-len(x[0]), x[0]))
    with open(out_file, "w") as f:
        f.write("BOGGLE ANSWERS\n")
        f.write("=" * 40 + "\n")
        f.write(f"Board:\n")
        for row in grid:
            f.write("  " + "  ".join(c.upper() for c in row) + "\n")
        f.write(f"\nFound {len(found)} words  |  Score: {sum(found.values())} pts\n\n")
        for word, score in words_sorted:
            f.write(f"{word.upper():<20} {score} pt\n")

    print(f"  💾  Answers saved to: {out_file}\n")

    # ── Play again? ───────────────────────────
    again = input("  Solve another board? (y/n): ").strip().lower()
    if again == "y":
        print("\n" + "="*50 + "\n")
        # Restart without reloading dictionary
        grid = None
        size = choose_grid_size()
        grid = ask_grid_manually(size)
        t0 = time.time()
        found = solve(grid, trie)
        elapsed = time.time() - t0
        print(f"  Done in {elapsed:.2f}s")
        print_results(found, grid)
    else:
        print(f"\n  {GREEN}{BOLD}Good luck! 🍀{RESET}\n")

if __name__ == "__main__":
    main()
