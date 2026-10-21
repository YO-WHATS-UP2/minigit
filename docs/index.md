# minigit

**A small Git, rebuilt from scratch in Python so you can see how it works.**

minigit is a small Git implementation in Python. It writes real Git objects, including blobs, trees and commits, so standard Git tools can inspect its repository data. The project keeps each command self-contained to make the internals approachable and contributions easy to review.

## Quick start

You need Python 3.10 or newer. Git is optional and is used for compatibility checks.

```bash
git clone https://github.com/YO-WHATS-UP2/minigit.git
cd minigit
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\\Scripts\\activate
pip install -e ".[dev]"
pytest
```

Try minigit in a scratch directory outside the source checkout:

```bash
mkdir ~/playground && cd ~/playground
minigit init
echo "hello" > hello.txt
minigit add hello.txt
minigit commit -m "First commit"
minigit cat-file -p HEAD
```

If the `minigit` command is not found, use `python -m minigit` instead.

## Explore the project

- [Tutorial: add your first command](adding-a-command.md) walks through the command structure, helpers and tests.
- [Architecture guide](ARCHITECTURE.md) explains the object store, index, refs and working tree.
- [Internals walkthrough](internals-walkthrough.md) follows blobs, trees and commits as they are written to disk.
- [Contributing guide](contributing.md) covers the contribution workflow and documentation preview.

The root [README.md](https://github.com/YO-WHATS-UP2/minigit/blob/main/README.md) remains the GitHub-friendly project overview with its original relative links.
