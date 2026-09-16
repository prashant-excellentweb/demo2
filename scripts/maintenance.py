"""Operational tasks for a Buddy Chat deployment.

Run from the project root, for example:

    python -m scripts.maintenance stats
    python -m scripts.maintenance purge-uploads --hours 24
    python -m scripts.maintenance purge-cache
    python -m scripts.maintenance vacuum

`purge-uploads` and `purge-cache` are the intended cron jobs; without them
abandoned uploads and expired cache rows accumulate forever.
"""

import argparse
import sys
from pathlib import Path

from sqlalchemy import func, select, text

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import settings  # noqa: E402
from app.db.session import SessionLocal, engine  # noqa: E402
from app.models import Attachment, ChatSession, Message, Project, User  # noqa: E402
from app.repositories.cache import ResponseCacheRepository  # noqa: E402
from app.services.attachment import AttachmentService  # noqa: E402


def command_stats() -> None:
    with SessionLocal() as session:
        counts = {
            "users": session.scalar(select(func.count()).select_from(User)),
            "projects": session.scalar(select(func.count()).select_from(Project)),
            "chats": session.scalar(select(func.count()).select_from(ChatSession)),
            "messages": session.scalar(select(func.count()).select_from(Message)),
            "attachments": session.scalar(select(func.count()).select_from(Attachment)),
        }
        for label, value in counts.items():
            print(f"{label:14} {value}")

        largest = session.scalar(select(func.max(func.length(Message.content)))) or 0
        print(f"{'largest msg':14} {largest} chars")

        # A non-zero count here would mean base64 payloads leaked back into the
        # transcript, which is what the restructure was meant to eliminate.
        inlined = session.scalar(
            select(func.count())
            .select_from(Message)
            .where(Message.content.like("%data:image%"))
        )
        print(f"{'inline base64':14} {inlined}")

        stored = 0
        upload_root = Path(settings.UPLOAD_DIR)
        if upload_root.exists():
            stored = sum(1 for path in upload_root.rglob("*") if path.is_file())
        print(f"{'files on disk':14} {stored}")


def command_purge_uploads(hours: int) -> None:
    with SessionLocal() as session:
        removed = AttachmentService(session).purge_orphans(older_than_hours=hours)
    print(f"Removed {removed} unsent upload(s) older than {hours}h.")


def command_purge_cache() -> None:
    with SessionLocal() as session:
        removed = ResponseCacheRepository(session).purge_expired()
        session.commit()
    print(f"Removed {removed} expired cache entr(ies).")


def command_vacuum() -> None:
    """Reclaim space SQLite keeps after large deletions."""
    if not settings.DATABASE_URL.startswith("sqlite"):
        print("VACUUM is only run for SQLite here; use your DB's tooling instead.")
        return
    with engine.connect() as connection:
        connection.execute(text("VACUUM"))
    print("Database vacuumed.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    subcommands = parser.add_subparsers(dest="command", required=True)

    subcommands.add_parser("stats", help="Show row counts and storage health.")

    uploads = subcommands.add_parser(
        "purge-uploads", help="Delete uploads that were never sent with a message."
    )
    uploads.add_argument("--hours", type=int, default=24)

    subcommands.add_parser("purge-cache", help="Delete expired response cache rows.")
    subcommands.add_parser("vacuum", help="Reclaim free pages (SQLite only).")

    args = parser.parse_args()

    if args.command == "stats":
        command_stats()
    elif args.command == "purge-uploads":
        command_purge_uploads(args.hours)
    elif args.command == "purge-cache":
        command_purge_cache()
    elif args.command == "vacuum":
        command_vacuum()


if __name__ == "__main__":
    main()
