#!/usr/bin/env python3
import argparse, json, os, re, subprocess, sys
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data"
RATINGS_JSON = DATA_DIR / "ratings.json"

# e.g., "1680.8242"
LINE_FLOAT = re.compile(r"(?P<rating>\d{3,4}\.\d+)")
# leetcode slug
SLUG = re.compile(r"([a-z0-9]+(?:-[a-z0-9]+)+)")


def normalize_slug(s: str) -> str:
    """Accept either a LeetCode URL or a slug and return the slug."""
    m = re.search(r"problems/([^/]+)/", s)
    return m.group(1) if m else s


def parse_ratings_txt(path: Path):
    """Parse Zerotrac ratings.txt heuristically into list of dicts.
    We pick the *last* float on the line as the rating and the *first* slug-looking
    token as the slug; also try to capture a numeric problem ID if present.
    """
    out = {}
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        for raw in f:
            line = raw.strip()
            if not line:
                continue
            m_slug = SLUG.search(line)
            m_rat = None
            for m in LINE_FLOAT.finditer(line):
                m_rat = m
            if not m_slug or not m_rat:
                continue
            slug = m_slug.group(1)
            rating = float(m_rat.group("rating"))
            # Try to capture a numeric problem ID if present
            id_match = re.search(r"\b(\d{1,5})\b", line)
            pid = int(id_match.group(1)) if id_match else None
            out[slug] = {"slug": slug, "rating": rating, "problem_id": pid}
    return out


def build_index(ratings_file: Path, out: Path):
    items = parse_ratings_txt(ratings_file)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)
    print(f"Indexed {len(items)} problems -> {out}")


def load_index():
    if not RATINGS_JSON.exists():
        print("ratings.json not found. Run scripts/sync_ratings.sh first.", file=sys.stderr)
        sys.exit(1)
    return json.loads(RATINGS_JSON.read_text(encoding="utf-8"))


def suggest(slug: str, delta: int = 150, limit: int = 3):
    idx = load_index()
    if slug not in idx:
        print(f"Slug '{slug}' not in ratings index.")
        sys.exit(2)
    target = idx[slug]["rating"]
    # Gather candidates with rating < target and within window
    cands = [v for v in idx.values() if v["rating"] < target and (target - v["rating"]) <= max(delta, 1)]
    # Prefer similar slugs by keyword overlap
    key = set(slug.split("-"))

    def score(v):
        w = set(v["slug"].split("-"))
        return (len(key & w), -abs(target - v["rating"]))

    cands.sort(key=score, reverse=True)
    return cands[:limit], target


def explain(slug: str, statement_file: str | None, code_file: str | None):
    idx = load_index()
    rating = idx.get(slug, {}).get("rating")
    # Choose prompt: review if user code provided, else explain
    prompt_name = "review.md" if code_file else "explain.md"
    prompt_body = (Path(__file__).parent / "prompts" / prompt_name).read_text()

    vars_blob = f"Slug: {slug}\nRating: {rating}\n"
    if statement_file and os.path.exists(statement_file):
        vars_blob += f"Statement file: {statement_file}\n"
    if code_file and os.path.exists(code_file):
        vars_blob += f"User code: {code_file}\n"

    prompt = f"{prompt_body}\n\n---\n{vars_blob}\n"

    # Call Gemini CLI non-interactively and attach local files
    cmd = ["gemini", "-m", "gemini-2.5-pro", "-p", prompt]
    if statement_file and os.path.exists(statement_file):
        cmd += ["-f", statement_file]
    if code_file and os.path.exists(code_file):
        cmd += ["-f", code_file]
    subprocess.run(cmd, check=False)


def mcp_server():
    """Very small MCP-like server shim: respond to 'lookup <slug>' on stdin.
    This is a toy to demonstrate MCP wiring in settings.json.
    """
    idx = load_index()
    print("ratings MCP ready", flush=True)
    for line in sys.stdin:
        line = line.strip()
        if line.startswith("lookup "):
            s = line.split(" ", 1)[1]
            print(json.dumps(idx.get(s, {})), flush=True)
        else:
            print(json.dumps({"error": "unknown command"}), flush=True)


def main():
    ap = argparse.ArgumentParser("leetcoach")
    sub = ap.add_subparsers(dest="cmd", required=True)

    b = sub.add_parser("build-index")
    b.add_argument("--ratings-file", required=True)
    b.add_argument("--out", default=str(RATINGS_JSON))

    s = sub.add_parser("suggest")
    s.add_argument("slug")
    s.add_argument("--delta", type=int, default=150)
    s.add_argument("--limit", type=int, default=3)

    e = sub.add_parser("explain")
    e.add_argument("slug")
    e.add_argument("--statement-file")
    e.add_argument("--code-file")

    a = sub.add_parser("start")
    a.add_argument("slug")
    a.add_argument("--statement-file")
    a.add_argument("--code-file")
    a.add_argument(
        "--non-interactive",
        action="store_true",
        help="Skip the choice prompt; just print analysis + bridges",
    )

    m = sub.add_parser("mcp")

    args = ap.parse_args()

    if args.cmd == "build-index":
        build_index(Path(args.ratings_file), Path(args.out))

    elif args.cmd == "suggest":
        target_slug = normalize_slug(args.slug)
        cands, target = suggest(target_slug, args.delta, args.limit)
        print(
            json.dumps(
                {"target": {"slug": target_slug, "rating": target}, "bridges": cands},
                indent=2,
            )
        )

    elif args.cmd == "explain":
        target_slug = normalize_slug(args.slug)
        explain(target_slug, args.statement_file, args.code_file)

    elif args.cmd == "start":
        target_slug = normalize_slug(args.slug)
        cands, target = suggest(target_slug, 150, 3)
        explain(target_slug, args.statement_file, args.code_file)

        if not args.non_interactive:
            try:
                choice = (
                    input(
                        "Type 'solve' for a full solution, 'bridges' for easier practice, or ENTER to exit: "
                    )
                    .strip()
                    .lower()
                )
            except EOFError:
                choice = ""

            if choice == "bridges":
                print("\nStrictly-easier bridge suggestions (Zerotrac):")
                for c in cands:
                    print(f"- {c['slug']}  ({c['rating']:.1f})")

            elif choice == "solve":
                solve_prompt = (Path(__file__).parent / "prompts" / "solve.md").read_text()
                vars_blob = f"Slug: {target_slug}\nRating: {target}\n"
                if args.statement_file and os.path.exists(args.statement_file):
                    vars_blob += f"Statement file: {args.statement_file}\n"
                if args.code_file and os.path.exists(args.code_file):
                    vars_blob += f"User code: {args.code_file}\n"
                prompt = f"{solve_prompt}\n\n---\n{vars_blob}\n"

                cmd = ["gemini", "-m", "gemini-2.5-pro", "-p", prompt]
                if args.statement_file and os.path.exists(args.statement_file):
                    cmd += ["-f", args.statement_file]
                if args.code_file and os.path.exists(args.code_file):
                    cmd += ["-f", args.code_file]
                subprocess.run(cmd, check=False)

    elif args.cmd == "mcp":
        mcp_server()


if __name__ == "__main__":
    main()
