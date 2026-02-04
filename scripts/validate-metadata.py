import json
import os
import sys


def main() -> int:
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    metadata_path = os.path.join(repo_root, "build", "metadata.json")

    try:
        with open(metadata_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"Missing metadata file: {metadata_path}", file=sys.stderr)
        return 1
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON in {metadata_path}: {exc}", file=sys.stderr)
        return 1

    required = [
        "app_name",
        "app_display_name",
        "app_version",
        "app_publisher",
        "app_exe_name",
        "app_setup_base_name",
    ]
    missing = [key for key in required if not data.get(key)]
    if missing:
        print(
            "metadata.json is missing required keys or values: "
            + ", ".join(missing),
            file=sys.stderr,
        )
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
