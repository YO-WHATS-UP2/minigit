# Contributing to minigit

Thanks for being here! This guide takes you from zero to a merged pull request. If anything is unclear, that's a bug in this guide, so please tell us.

## 1. Set up (about 10 minutes)

1. **Fork** this repository on GitHub (the "Fork" button, top right).
2. **Clone your fork** and add the original as `upstream`:
   ```bash
   git clone https://github.com/<your-username>/minigit.git
   cd minigit
   git remote add upstream https://github.com/YO-WHATS-UP2/minigit.git
   ```
3. **Create a virtual environment and install:**
   ```bash
   python -m venv .venv
   source .venv/bin/activate        # Windows: .venv\Scripts\activate
   pip install -e ".[dev]"
   ```
4. **Check everything works:**
   ```bash
   pytest
   ```
   All tests should pass. If they don't, ask in Discord before you change anything.

## 2. Pick an issue

- Browse the [open issues](../../issues). New to this? Filter by `good first issue`.
- **Comment on the issue to claim it** (for example "I'd like to work on this"), then wait for a mentor to assign you. Please don't start until you're assigned; that way two people don't build the same thing.
- **One issue at a time.** Once your PR is merged (or in review), you can claim another.
- If you're assigned but have gone **5 days without an update**, the issue may be given to someone else. If life gets busy, just comment and let us know. That's completely fine.
- For issues labelled `advanced`, **post a short plan in the issue first** (a few bullet points on your approach). A mentor will reply before you write lots of code. This saves you from rewriting everything later.

## 3. Make your change

```bash
git checkout main
git pull upstream main              # start from the latest code
git checkout -b 12-log-command      # <issue number>-<short-description>
```

Then:

- **Read [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)** and, if you're adding a command, **[docs/adding-a-command.md](docs/adding-a-command.md)**.
- **Match real Git.** When in doubt, run the same thing with `git` and copy its behaviour and output format. The Git docs (`git help <command>`) are your spec.
- **Reuse the helpers** in `objects.py`, `refs.py`, `index.py` and `worktree.py` instead of reading `.minigit` files by hand. If you need a new helper that other commands could use too, add it to the right module (with a test).
- **Report errors with `raise MinigitError("...")`.** Don't `print` errors and `exit` yourself.
- **Write tests.** Every PR that changes behaviour needs tests in `tests/`. Look at `tests/test_commands.py` for examples. The `repo`, `run` and `write` fixtures do most of the work.

Before you push, run:

```bash
pytest
ruff check .
ruff format .
```

### Commit messages

Write short, present-tense summaries that say *what* changed:

```
Add log command
Show abbreviated SHAs in commit output
Fix add crashing on empty directories
```

Several small commits are fine. We'll squash them when merging.

## 4. Open a pull request

```bash
git push origin 12-log-command
```

Then open a PR on GitHub **against `main`** and fill in the template:

- Put **`Closes #12`** in the description so the issue is linked.
- Paste a short **terminal session showing your feature working**.
- Keep it to **one issue per PR**. Unrelated fixes go in their own PR.

## 5. Review

- A mentor will review within a few days. **Review comments are normal**; almost every PR gets some, and they aren't a sign you did badly.
- Push new commits to the same branch to address feedback, then reply to each comment.
- If your branch falls behind `main`, update it:
  ```bash
  git fetch upstream
  git rebase upstream/main           # or: git merge upstream/main
  ```
- Once CI is green and the review is approved, a mentor merges it. 🎉

## Getting help

- **Stuck?** First say what you tried: which file you looked at, what you expected, what happened. You'll get a much better answer, much faster.
- Search existing issues and the docs first. Someone may have hit the same thing.
- Ask in the project's channel on the Hello FOSS Discord.

## Code of conduct

Be kind. Everyone here is learning. See [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).
