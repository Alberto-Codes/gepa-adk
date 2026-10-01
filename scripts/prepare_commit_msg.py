"""Strip ``Co-Authored-By`` lines before the commit-msg gate runs.

Some harnesses append a model ``Co-Authored-By`` trailer on their own.
``.claude/rules/pull-requests.md`` forbids every such trailer, so the
``prepare-commit-msg`` hook removes each one and the stored message
matches policy. ``scripts/check_commit_msg.py`` still refuses a trailer
that survives this stage, for example one added in the editor.

Examples:
    pre-commit calls it with the message file, then git's extra arguments:

    ```console
    $ uv run python scripts/prepare_commit_msg.py .git/COMMIT_EDITMSG message
    ```

See Also:
    - [scripts.check_commit_msg][]: The gate that refuses a surviving trailer.
"""

from __future__ import annotations

import sys
from pathlib import Path

if __package__ in {None, ""}:
    from check_commit_msg import strip_coauthors
else:
    from .check_commit_msg import strip_coauthors


def main(argv: list[str] | None = None) -> int:
    """Rewrite the commit message file without ``Co-Authored-By`` lines.

    Args:
        argv: The message file path, then git's optional source and object
            arguments, which are ignored. None reads ``sys.argv``.

    Returns:
        Process exit code, always 0.
    """
    args = list(argv if argv is not None else sys.argv[1:])
    if args:
        path = Path(args[0])
        if path.is_file():
            text = path.read_text(encoding="utf-8")
            stripped = strip_coauthors(text)
            if stripped != text:
                path.write_text(stripped, encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
