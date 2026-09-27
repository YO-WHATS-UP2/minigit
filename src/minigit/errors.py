"""Errors that minigit reports to the user."""


class MinigitError(Exception):
    """A problem the user caused or can fix.

    The CLI catches this, prints ``fatal: <message>`` to stderr and exits
    with status 128, the same way Git does. Raise it instead of printing an
    error yourself.
    """
