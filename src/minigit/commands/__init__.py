"""Every module in this package is one minigit command.

To add a command, create ``src/minigit/commands/<name>.py`` containing:

    NAME = "log"                        # what users type: minigit log
    HELP = "Show commit history"        # one line, shown in `minigit --help`

    def configure(parser):              # add options with argparse
        parser.add_argument("-n", type=int)

    def run(args, repo):                # do the work; return an exit code
        ...
        return 0

Optionally set ``NEEDS_REPO = False`` for commands that work outside a
repository (``init`` does this). Otherwise ``repo`` is the repository the
user is in.

New commands are found automatically, so you never need to edit this file.
"""

from __future__ import annotations

import importlib
import pkgutil
from types import ModuleType

_REQUIRED = ("NAME", "HELP", "configure", "run")


def discover() -> dict[str, ModuleType]:
    commands = {}
    for info in pkgutil.iter_modules(__path__):
        if info.name.startswith("_"):
            continue
        module = importlib.import_module(f"{__name__}.{info.name}")
        missing = [attr for attr in _REQUIRED if not hasattr(module, attr)]
        if missing:
            raise RuntimeError(f"command module {module.__name__} is missing {', '.join(missing)}")
        commands[module.NAME] = module
    return dict(sorted(commands.items()))
