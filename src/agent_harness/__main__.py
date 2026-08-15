"""Module entry point: ``py -3.11 -m agent_harness``.

Routes to the same Typer application as the console command.
"""

from .cli import app

if __name__ == "__main__":
    app()
