# minigit architecture

This guide explains how minigit is put together and why. Read it once before your first PR. After that, the docstrings in each module are the detailed reference.

## The big picture

```
            you type:  minigit commit -m "msg"
                              │
                     cli.py   │  parses args, finds the repo, runs the command,
                              │  turns MinigitError into "fatal: ..." + exit 128
                              ▼
               commands/commit.py   run(args, repo)
                 │          │           │            │
                 ▼          ▼           ▼            ▼
             index.py   objects.py   refs.py    identity.py
           (staging)   (blob/tree/   (HEAD,      (author,
                        commit)      branches)    time)
                 │          │           │
                 └──────────┴───────────┴──►  .minigit/  on disk
```

**Commands** (in `commands/`) are thin. They parse options, call helpers, and print. **Helpers** (the other modules) do the actual Git logic and are shared by every command. If two commands need the same thing, it belongs in a helper module.

## What's on disk

```
my-project/
├── hello.txt                  ← working tree: your actual files
├── src/app.py
└── .minigit/
    ├── HEAD                   "ref: refs/heads/main"
    ├── config                 INI settings
    ├── minigit-index          staging area (plain text, see below)
    ├── objects/
    │   ├── ce/013625030b...   zlib-compressed objects, named by SHA-1
    │   └── af/bdd27cb0dd...
    └── refs/
        ├── heads/main         "fb2368536aa0b5238a8c2e1443b3cec6e76a45a0"
        └── tags/
```

This is the same layout as `.git`, so real Git can read it: `GIT_DIR=.minigit git log`. The one intentional difference is the **index** (staging area). Git's is a binary file called `index`. minigit's is plain text called `minigit-index`, so you can read it. It has a different name so real Git ignores it instead of failing with "index file corrupt":

```
minigit-index 1
100644 ce013625030ba8dba906f756967f9e9ca394464a hello.txt
100644 b917a726c93f902e43291d9009d6488385133b67 src/app.py
```

## Objects (`objects.py`)

Every object is stored as `zlib(b"<type> <size>\0" + content)` and named by the SHA-1 of the uncompressed bytes. Identical content always gets the same name, which is why Git never stores the same file twice.

| Type | Content | minigit API |
|---|---|---|
| blob | raw file bytes | `write_object(repo, data)` / `read_object(repo, sha)` |
| tree | entries `<mode> <name>\0<20-byte sha>` | `TreeEntry`, `read_tree`, `serialize_tree`, `flatten_tree` |
| commit | `tree`, `parent`s, `author`, `committer`, blank line, message | `Commit`, `Signature`, `read_commit`, `peel_to_tree` |

Things that trip people up:

- **Tree sort order.** Entries are sorted by name, but directories sort as if their name ended in `/`. `serialize_tree` handles this. Always use it; never build tree bytes by hand.
- **Modes** are strings: `"100644"` (file), `"100755"` (executable), `"40000"` (directory; Git writes no leading zero).
- **`flatten_tree(repo, sha)`** turns a whole commit snapshot into `{"src/app.py": TreeEntry, ...}`. Most comparison commands (`status`, `diff`, `checkout`) start by calling it.

## The index (`index.py`)

`Index.load(repo)` → change it → `index.save(repo)`. Entries are `IndexEntry(mode, sha, path)` and iterate in sorted path order. `index.write_tree(repo)` converts the flat list of paths into nested tree objects and returns the root tree SHA. `commit` uses this.

## Refs (`refs.py`)

| Function | Use it to… |
|---|---|
| `resolve(repo, name)` | turn anything a user types (`HEAD`, `main`, `v1.0`, a SHA) into a full SHA |
| `head_commit(repo)` | get the current commit (`None` before the first commit) |
| `current_branch(repo)` | get `"main"`, or `None` if HEAD is detached |
| `update_head(repo, sha)` | move the current branch (what `commit` does) |
| `set_head(repo, "refs/heads/x")` | switch branches (what `checkout` will do) |
| `read_ref` / `update_ref` / `iter_refs` | work with any ref directly, e.g. `iter_refs(repo, "refs/tags")` |

## The working tree (`worktree.py`)

- `iter_files(repo)` yields every tracked-or-not file as a sorted, forward-slash, repo-relative path. It already skips `.minigit` and `.git`. **Ignore rules will go here**, so every command gets them automatically.
- `repo_relative(repo, path)` converts what the user typed (relative to their current folder) into a repo path, and rejects paths outside the repo.

## Commands (`commands/`)

`commands/__init__.py` imports every module in the folder at startup. A command is any module with `NAME`, `HELP`, `configure(parser)` and `run(args, repo)`. You never register a command anywhere; adding the file is enough. That's deliberate: 20 people can each add a command in parallel without editing the same file. See [adding-a-command.md](adding-a-command.md).

## Conventions

- **Errors:** `raise MinigitError("message")`. The CLI prints `fatal: message` and exits 128, like Git.
- **Output:** match `git`'s output format when it's reasonable to do so. Print to stdout; errors go through `MinigitError`.
- **Paths:** always forward slashes inside minigit, even on Windows. Convert at the edges with `worktree.repo_relative`.
- **Bytes vs text:** file contents are `bytes`. Never decode a blob unless you're displaying it.
- **Tests:** in-process via the `run` fixture. Use the `git` fixture to compare with real Git where it helps. Fixed author/date env vars make SHAs stable.

## Deliberate simplifications

These differ from real Git on purpose. Some of them are open issues if you want to close the gap:

- The index is text (`minigit-index`), not Git's binary `DIRC` format, and stores no file timestamps. Real Git therefore sees an empty staging area in a minigit repo: `git log`, `git show` and `git fsck` work, but `git status` shows every file as deleted-and-untracked.
- Every file is staged as mode `100644` (no executable bit or symlinks yet).
- Only loose objects; no packfiles.
- No `packed-refs`, reflog, hooks, submodules or remotes.
