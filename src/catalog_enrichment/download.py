"""Download the pinned model into the gitignored cache. Run by setup; safe to repeat."""

from .config import load_config
from .model import download


def main() -> None:
    m = load_config()["model"]
    path = download(m["id"], m["revision"], m["cache_dir"])
    print(f"Model ready: {m['id']} @ {m['revision'][:7]} in {path}")


if __name__ == "__main__":
    main()
