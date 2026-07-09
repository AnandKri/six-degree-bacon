"""Enable ``python -m sdb`` as an alias for the ``sdb`` console script."""

from sdb.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
