"""Entry point for ``python -m app``.

Binds the Flask development server to ``127.0.0.1`` only, per PLAN.md §11.
"""

from __future__ import annotations

from . import create_app


def main() -> None:
    app = create_app()
    app.run(host="127.0.0.1", port=5000, debug=False)


if __name__ == "__main__":
    main()
