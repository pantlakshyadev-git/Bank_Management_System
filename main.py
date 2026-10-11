import logging
from bank_app.database import Database
from bank_app.config import settings
from bank_app.cli import run_cli


def main():
    settings.output_dir.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        filename=settings.output_dir / "bank_app.log",
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    try:
        db = Database()
        db.ping()
        run_cli(db)
    except Exception:
        logging.exception("Application startup or runtime failure")
        print("Could not start the application. Check MySQL settings and output/bank_app.log.")


if __name__ == "__main__":
    main()
