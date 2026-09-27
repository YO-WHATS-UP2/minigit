# Tutorial: your first minigit command

In about 15 minutes you'll add a practice command, `minigit whereami`, that prints the current branch and commit. You won't submit it. It's here so you learn the pattern before picking up a real issue.

```console
$ minigit whereami
On branch main at fb23685 (First commit)
```

## Step 1: create the file

Create `src/minigit/commands/whereami.py`:

```python
"""minigit whereami: show the current branch and commit (tutorial example)."""

NAME = "whereami"
HELP = "Show the current branch and commit"


def configure(parser):
    pass  # no options yet


def run(args, repo):
    print("hello from whereami")
    return 0
```

Run it:

```console
$ minigit whereami
hello from whereami
$ minigit --help          # it's listed automatically!
```

You didn't register the command anywhere. `commands/__init__.py` finds every file in the folder.

## Step 2: use the helpers

Don't read `.minigit/HEAD` yourself. The helpers in `refs.py` and `objects.py` already know how:

```python
from minigit.objects import read_commit
from minigit.refs import current_branch, head_commit

NAME = "whereami"
HELP = "Show the current branch and commit"


def configure(parser):
    pass


def run(args, repo):
    branch = current_branch(repo) or "(detached HEAD)"
    sha = head_commit(repo)
    if sha is None:
        print(f"On branch {branch}, no commits yet")
        return 0
    title = read_commit(repo, sha).message.splitlines()[0]
    print(f"On branch {branch} at {sha[:7]} ({title})")
    return 0
```

Try it in a playground repo before and after making a commit.

## Step 3: add an option

`configure` receives a normal [argparse](https://docs.python.org/3/library/argparse.html) parser:

```python
def configure(parser):
    parser.add_argument("--full", action="store_true", help="print the full SHA")


def run(args, repo):
    ...
    shown = sha if args.full else sha[:7]
```

## Step 4: handle errors the minigit way

If something is wrong, **raise** instead of printing:

```python
from minigit.errors import MinigitError

if sha is None and args.full:
    raise MinigitError("no commits yet")
```

The user sees `fatal: no commits yet` and the exit code is 128, the same as Git.

## Step 5: write a test

Create `tests/test_whereami.py`:

```python
def test_before_first_commit(repo, run):
    assert run("whereami").out == "On branch main, no commits yet\n"


def test_after_commit(repo, run, write):
    write("a.txt", "hi\n")
    run("add", "a.txt")
    run("commit", "-m", "First commit")
    result = run("whereami")
    assert result.code == 0
    assert result.out.startswith("On branch main at ")
    assert result.out.endswith("(First commit)\n")
```

The fixtures (defined in `tests/conftest.py`) do the setup:

| Fixture | Gives you |
|---|---|
| `repo` | a fresh `minigit init`-ed repository; the test runs inside it |
| `run(*args)` | runs a command, returns `.code`, `.out`, `.err` |
| `write(path, content)` | creates a file (and folders) in the working tree |
| `git(*args)` | runs **real** git on the same repo (skipped if git isn't installed) |

Run `pytest tests/test_whereami.py -v`.

## Step 6: clean up

This was practice, so delete both files before starting your real issue:

```bash
rm src/minigit/commands/whereami.py tests/test_whereami.py
```

## Checklist for a real command PR

- [ ] One file in `src/minigit/commands/`, plus shared logic in a helper module if other commands could use it
- [ ] Behaviour and output match real `git` for the cases the issue lists
- [ ] Errors use `MinigitError`
- [ ] Tests cover the normal case, and at least one edge case (empty repo, missing file, detached HEAD, …)
- [ ] `pytest`, `ruff check .` and `ruff format --check .` all pass
- [ ] The "What works" table in `README.md` is updated
