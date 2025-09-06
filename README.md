# LeetCoach: Gemini powered local LeetCode coach

**Problem**: LeetCode’s Easy/Medium/Hard buckets are too coarse. Zerotrac/CLIST offer *numeric* difficulty. In the terminal, I want a coach that only proposes truly easier bridge problems and helps me start quickly.

**What it does**
- `scripts/sync_ratings.sh` pulls the latest Zerotrac ratings and builds a local JSON index.
- `leetcoach.py start <slug>` prints 2–3 strictly easier bridge problems by rating and calls **Gemini CLI** to explain the target problem with a concise plan.
- Optional: pass `--statement-file` to ground Gemini on a local problem statement file (no scraping, all local).

**How to run (5 steps)**
```bash
brew install gemini-cli || npm i -g @google/gemini-cli
python3 -m venv .venv && source .venv/bin/activate
python -c "import sys; sys.exit(0)"  # ensure Python works
bash scripts/sync_ratings.sh
python3 leetcoach.py start two-sum --statement-file examples/two-sum.txt
```

**Why it’s headless**
- Everything is CLI. Gemini is run non‑interactively with `-p` and local files. Ratings stay local (`data/ratings.json`).

**Stretch**
- Add CLIST API fallback for slugs missing in Zerotrac.
- Add `watch` mode to read LeetCode URL from clipboard and auto‑trigger.
- Generate language templates + tiny unit tests with Gemini.

### Mode B: Analyze my broken solution

# 1) Prepare local files
pbpaste > problems/<slug>.txt     # paste the question text
cp </path/to/your/WIP>.py ./wip.py

# 2) Run reviewer
python3 leetcoach.py start <slug|url> \
  --statement-file problems/<slug>.txt \
  --code-file wip.py

# 3) Choose your path
When prompted: type `solve` to get a clean reference solution now, or `bridges` to practice strictly easier problems first.
