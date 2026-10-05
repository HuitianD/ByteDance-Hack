"""Admin CLI: python -m app.manage invite | check-planner | events | reset-limits."""

import argparse
import asyncio
import json
from app.core.config import get_settings
from app.runtime.store import Store


async def check(settings):
    from app.llm.factory import get_llm_client
    from app.core.errors import public_error

    client = get_llm_client(settings)
    try:
        result = await client.generate_json(
            'Return only {"ok":true}', max_tokens=64, temperature=0
        )
        print(
            json.dumps(
                {"provider": client.provider_name, "ok": result.get("ok") is True}
            )
        )
    except Exception as exc:
        print(json.dumps({"ok": False, "error": public_error(exc)}))
    finally:
        await client.aclose()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "command",
        choices=["invite", "check-planner", "events", "reset-limits", "migrate-search"],
    )
    parser.add_argument("--quota", type=int, default=3)
    args = parser.parse_args()
    settings = get_settings()
    store = Store(settings.data_dir_path())
    if args.command == "invite":
        if not 1 <= args.quota <= 100:
            parser.error("quota must be 1–100")
        print(store.create_invite(args.quota))
    elif args.command == "check-planner":
        asyncio.run(check(settings))
    elif args.command == "migrate-search":
        from app.services.retrieval import migrate

        migrate(settings)
        print("Search schema ready.")
    elif args.command == "reset-limits":
        with store.connection() as db:
            db.execute("DELETE FROM counters")
        print("Usage counters reset; existing invites and jobs preserved.")
    else:
        with store.connection() as db:
            for row in db.execute(
                "SELECT name,body,created FROM events ORDER BY id DESC LIMIT 100"
            ):
                print(json.dumps(dict(row)))


if __name__ == "__main__":
    main()
