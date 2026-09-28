# minigit

**A small Git, rebuilt from scratch in Python so you can see how it works.**

You use Git every day. minigit rebuilds it in plain Python with no dependencies: the object store, SHA-1 content addressing, trees, commits, branches and the staging area.

It isn't a toy format. minigit writes **real Git objects**, so real Git can read a minigit repository:

```console
$ minigit init
$ echo "hello" > hello.txt
$ minigit add hello.txt
$ minigit commit -m "First commit"
[main (root-commit) 3f6a1c2] First commit     # your SHA will differ: it includes the time

$ GIT_DIR=.minigit git log --oneline      # real git, reading minigit's data
3f6a1c2 First commit
```

minigit is a [Hello FOSS 2026](https://www.wncc-iitb.org/) project. Each Git command is a small, self-contained Python file, so it's easy to make your first open-source contribution here, and you learn how Git works while doing it.

## Quick start

You need **Python 3.10 or newer**. Git is optional; it's only used to check compatibility.

```bash
git clone https://github.com/<your-username>/minigit.git
cd minigit
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
pytest                             # everything should pass
```

Now try it in a scratch folder **outside** the minigit source code:

```bash
mkdir ~/playground && cd ~/playground
minigit init
echo "hello" > hello.txt
minigit add hello.txt
minigit commit -m "First commit"
minigit cat-file -p HEAD           # look inside the commit you just made
```

> **Tip:** If the `minigit` command isn't found, use `python -m minigit` instead.

## What works

| Command | Status | |
|---|---|---|
| `init` | ✅ Done | Create a repository |
| `hash-object [-w]` | ✅ Done | Hash a file, optionally store it |
| `cat-file -t/-s/-p` | ✅ Done | Look inside any object |
| `add <paths>` | ✅ Done | Stage files and directories |
| `commit -m` | ✅ Done | Record a snapshot |
| `ls-files [-s]` | ✅ Done | Show staged files |
| `log`, `status`, `branch`, `checkout`, `diff`, `tag`, `rm`, `reset`, `merge`, … | 🚧 [Open issues](../../issues) | **This is where you come in** |

## How Git works, in about a minute

Git is a **key-value store**. The key is the SHA-1 hash of the value, and there are only three kinds of value you need to know:

```
commit fb23685 ──► tree afbdd27 ──┬─► blob ce01362  "hello\n"         (hello.txt)
  author Ada                      └─► tree 5f6ed9b ──► blob b917a72    (src/app.py)
  parent (none)
  "First commit"
```

- A **blob** is the contents of one file.
- A **tree** is one directory, mapping names to blobs and other trees.
- A **commit** is a snapshot: one root tree, plus parent commit(s), author and message.
- A **branch** is a file containing a commit SHA. `HEAD` says which branch you're on.

That's all of it. Every command in Git (and minigit) reads or moves these pieces around. For the full tour of the code, read [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Contributing

We'd love your help, especially if this is your first open-source contribution.

1. Read **[CONTRIBUTING.md](CONTRIBUTING.md)** for setup, the workflow and PR rules.
2. Work through **[docs/adding-a-command.md](docs/adding-a-command.md)**, a 15-minute tutorial.
3. Pick an issue labelled [`good first issue`](../../issues?q=is%3Aopen+label%3A%22good+first+issue%22) and comment to claim it.

## Project layout

```
src/minigit/
    cli.py          argument parsing; finds commands automatically
    commands/       one file per command  ← most contributions go here
    objects.py      blobs, trees, commits: reading, writing, hashing
    index.py        the staging area
    refs.py         branches, tags, HEAD, and resolving names to SHAs
    worktree.py     listing the files in the working tree
    repo.py         finding / creating the .minigit directory
    identity.py     who is committing, and when
tests/              pytest tests, one file per module / command
docs/               architecture guide and tutorials
```

## License

[MIT](LICENSE)
