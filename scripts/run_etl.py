import argparse
from pathlib import Path
import sys


ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.core.config import ENV_FILE, get_settings
from app.core.exceptions import ApplicationError
from app.db.session import init_db, session_scope, verify_db_connection
from app.services.etl_service import ETLService


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the CarteiraConsol ETL pipeline.")
    parser.add_argument(
        "--source",
        dest="source",
        choices=("local", "s3"),
        default="local",
        help="Choose the ETL source type.",
    )
    parser.add_argument("--source-path", dest="source_path", help="Optional file path to process.")
    parser.add_argument(
        "--sample",
        action="store_true",
        help="Force the bundled sample file instead of auto-discovering from data/raw.",
    )
    parser.add_argument(
        "--real-inputs",
        action="store_true",
        help="Process the XP-oriented files located in data/real_inputs as one bundle.",
    )
    parser.add_argument("--s3-key", dest="s3_key", help="Exact S3 key to process.")
    parser.add_argument("--s3-prefix", dest="s3_prefix", help="S3 prefix to search for the latest file.")
    args = parser.parse_args()

    settings = get_settings()
    settings.ensure_directories()
    print(f"Using env file: {ENV_FILE}")
    verify_db_connection()
    init_db()

    source_path = args.source_path
    if args.sample and args.source == "local":
        source_path = str(settings.samples_dir / "sample_portfolio.csv")
    elif args.real_inputs and args.source == "local":
        source_path = str(settings.real_inputs_dir)

    try:
        with session_scope() as session:
            if args.source == "s3":
                result = ETLService(session).run_from_s3(s3_key=args.s3_key, s3_prefix=args.s3_prefix)
            else:
                result = ETLService(session).run(source_path=source_path)
            print(result.model_dump_json(indent=2))
    except ApplicationError as exc:
        print(f"ETL failed: {exc.message}")
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
