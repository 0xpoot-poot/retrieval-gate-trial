"""Try the retriever from the command line.

  python -m saangai_retrieval --user u02 --matter M-2026-101 "purchase price"
  python -m saangai_retrieval --user u02 "lease registration"      (public law only)
"""
import argparse
from pathlib import Path

from .retrieve import PermissionDenied, Retriever

DATA = Path(__file__).resolve().parents[1] / "data"


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("query")
    p.add_argument("--user", required=True)
    p.add_argument("--matter", default=None)
    p.add_argument("-k", type=int, default=5)
    p.add_argument("--data", default=str(DATA))
    a = p.parse_args()
    r = Retriever(a.data)
    try:
        for res in r.retrieve(a.user, a.matter, a.query, a.k):
            print(f"{res.score:8.4f}  {res.chunk_id:22s} {res.cls:12s} {res.text[:90]}")
    except PermissionDenied as exc:
        print(f"DENIED: {exc}")


if __name__ == "__main__":
    main()
