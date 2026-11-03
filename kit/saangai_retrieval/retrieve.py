"""SaangAI retrieval choke point (trial kit, synthetic).

Every retrieval for a lawyer passes through Retriever.retrieve(). It:
  1. loads the matter permissions export,
  2. authorises the user for the matter,
  3. works out which chunks the user may see,
  4. runs two search legs (vector and keyword), fuses them, reranks,
  5. caches the result and writes an audit record.

The "vector" search uses hashed character trigrams instead of a neural model,
and the reranker is a word-overlap stub, so the kit runs anywhere with plain
Python. The access logic is what matters here, not search quality.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
import time
import zlib
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable

CLASS_RANK = {"GREEN": 0, "AMBER": 1, "RED": 2, "BLACK": 3}
CAND_N = 20        # candidates taken from each search leg
RRF_K = 60         # reciprocal rank fusion constant
DIM = 256          # size of the hashed trigram vectors
BM25_K1, BM25_B = 1.5, 0.75

_TOKEN = re.compile(r"[a-z0-9]+")


class PermissionDenied(Exception):
    """Raised when the user may not retrieve for this matter."""


@dataclass(frozen=True)
class Result:
    chunk_id: str
    doc_id: str | None
    matter_id: str | None
    client_id: str | None
    cls: str
    text: str
    score: float


def tokenize(text: str) -> list[str]:
    return _TOKEN.findall(text.lower())


def embed(text: str) -> list[float]:
    vec = [0.0] * DIM
    padded = f" {text.lower()} "
    for i in range(len(padded) - 2):
        vec[zlib.crc32(padded[i:i + 3].encode()) % DIM] += 1.0
    norm = math.sqrt(sum(x * x for x in vec)) or 1.0
    return [x / norm for x in vec]


def default_reranker(query: str, passages: list[dict]) -> list[float]:
    """Stand-in for a cross-encoder: word overlap, length-normalised."""
    q = set(tokenize(query))
    scores = []
    for p in passages:
        toks = tokenize(p["text"])
        overlap = sum(1 for t in toks if t in q)
        scores.append(overlap / math.sqrt(len(toks) or 1))
    return scores


class Retriever:
    def __init__(self, data_dir: str | Path, audit_path: str | Path | None = None,
                 reranker: Callable[[str, list[dict]], list[float]] | None = None):
        self.data_dir = Path(data_dir)
        self.audit_path = Path(audit_path) if audit_path else self.data_dir / "audit.jsonl"
        self.reranker = reranker or default_reranker
        self._register = json.loads((self.data_dir / "clients.json").read_text())
        self._docs = {d["doc_id"]: d for d in json.loads((self.data_dir / "documents.json").read_text())}
        self._perms = self._load_perms()
        self._cache: dict[tuple, list[Result]] = {}

        # Build the index. Clients on the AI-prohibited register are never indexed.
        self._chunks: dict[str, dict] = {}
        with (self.data_dir / "chunks.jsonl").open() as f:
            for line in f:
                chunk = json.loads(line)
                if chunk["client_id"] is not None and not self._client_allowed(chunk["client_id"]):
                    continue
                self._chunks[chunk["chunk_id"]] = chunk
        self._vectors = {cid: embed(c["text"]) for cid, c in self._chunks.items()}
        self._tf = {cid: self._term_freq(c["text"]) for cid, c in self._chunks.items()}
        self._len = {cid: sum(tf.values()) for cid, tf in self._tf.items()}
        self._avg_len = sum(self._len.values()) / max(len(self._len), 1)
        self._df: dict[str, int] = {}
        for tf in self._tf.values():
            for term in tf:
                self._df[term] = self._df.get(term, 0) + 1

    # ---------- permissions ----------

    def _load_perms(self) -> dict:
        raw = (self.data_dir / "matters.json").read_text()
        perms = json.loads(raw)
        perms["_digest"] = hashlib.sha256(raw.encode()).hexdigest()
        return perms

    def _client_allowed(self, client_id: str) -> bool:
        entry = self._register.get(client_id, {})
        return not entry.get("ai_prohibited", False)

    def _authorise(self, user: str, matter_id: str | None, perms: dict) -> dict | None:
        if user not in perms["users"]:
            raise PermissionDenied("unknown user")
        if matter_id is None:
            return None  # public law only
        matter = perms["matters"].get(matter_id)
        if matter is None:
            raise PermissionDenied("unknown matter")
        if user not in matter["members"]:
            raise PermissionDenied("not a member of the matter")
        if user in matter.get("walled_off", []):
            raise PermissionDenied("behind an ethical wall")
        if not self._client_allowed(matter["client_id"]):
            raise PermissionDenied("client has prohibited AI use")
        return matter

    def _visible(self, user: str, matter: dict | None, chunk: dict) -> bool:
        if chunk["matter_id"] is None:
            return True  # public law
        if matter is None or chunk["matter_id"] != matter["matter_id"]:
            return False
        doc = self._docs.get(chunk["doc_id"], {})
        restricted = chunk.get("restricted_to")
        if restricted and user not in restricted:
            return False
        rank = CLASS_RANK.get(chunk.get("class"), CLASS_RANK["GREEN"])
        if rank >= CLASS_RANK["BLACK"] and user not in matter.get("black_cleared", []):
            return False
        return True

    # ---------- search legs ----------

    @staticmethod
    def _term_freq(text: str) -> dict[str, int]:
        tf: dict[str, int] = {}
        for t in tokenize(text):
            tf[t] = tf.get(t, 0) + 1
        return tf

    def _vector(self, query: str, n: int, restrict_to: Iterable[str] | None = None) -> list[str]:
        q = embed(query)
        ids = restrict_to if restrict_to is not None else self._chunks.keys()
        scored = [(sum(a * b for a, b in zip(q, self._vectors[cid])), cid) for cid in ids]
        scored.sort(key=lambda x: (-x[0], x[1]))
        return [cid for _, cid in scored[:n]]

    def _lexical(self, query: str, n: int, restrict_to: Iterable[str] | None = None) -> list[str]:
        terms = tokenize(query)
        total = len(self._chunks)
        ids = restrict_to if restrict_to is not None else self._chunks.keys()
        scored = []
        for cid in ids:
            tf, length, s = self._tf[cid], self._len[cid], 0.0
            for t in terms:
                if t not in tf:
                    continue
                idf = math.log(1 + (total - self._df[t] + 0.5) / (self._df[t] + 0.5))
                s += idf * tf[t] * (BM25_K1 + 1) / (tf[t] + BM25_K1 * (1 - BM25_B + BM25_B * length / self._avg_len))
            if s > 0:
                scored.append((s, cid))
        scored.sort(key=lambda x: (-x[0], x[1]))
        return [cid for _, cid in scored[:n]]

    @staticmethod
    def _fuse(*rankings: list[str]) -> list[str]:
        scores: dict[str, float] = {}
        for ranking in rankings:
            for rank, cid in enumerate(ranking):
                scores[cid] = scores.get(cid, 0.0) + 1.0 / (RRF_K + rank + 1)
        return [cid for cid, _ in sorted(scores.items(), key=lambda x: (-x[1], x[0]))]

    # ---------- audit ----------

    def _audit(self, record: dict) -> None:
        record = {"ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"), **record}
        with self.audit_path.open("a") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    # ---------- the choke point ----------

    def retrieve(self, user: str, matter_id: str | None, query: str, k: int = 5) -> list[Result]:
        perms = self._perms
        try:
            matter = self._authorise(user, matter_id, perms)
        except PermissionDenied as exc:
            self._audit({"user": user, "matter_id": matter_id, "query": query,
                         "decision": "deny", "reason": str(exc)})
            raise

        key = (" ".join(tokenize(query)), k)
        if key in self._cache:
            results = self._cache[key]
            self._audit({"user": user, "matter_id": matter_id, "query": query, "decision": "allow",
                         "cache_hit": True, "reranked": [], "returned": [r.chunk_id for r in results]})
            return list(results)

        allowed = {cid for cid, c in self._chunks.items() if self._visible(user, matter, c)}
        vec = self._vector(query, CAND_N, restrict_to=allowed)
        lex = self._lexical(query, CAND_N)
        fused = self._fuse(vec, lex)[:CAND_N]

        passages = [{"chunk_id": cid, "text": self._chunks[cid]["text"]} for cid in fused]
        scores = self.reranker(query, passages) if passages else []
        ranked = sorted(zip(fused, scores), key=lambda x: (-x[1], x[0]))

        returned = [(cid, s) for cid, s in ranked if cid in allowed][:k]
        results = []
        for cid, s in returned:
            c = self._chunks[cid]
            results.append(Result(cid, c["doc_id"], c["matter_id"], c["client_id"],
                                  c.get("class", "UNCLASSIFIED"), c["text"], round(s, 6)))

        self._cache[key] = results
        self._audit({"user": user, "matter_id": matter_id, "query": query, "decision": "allow",
                     "cache_hit": False, "reranked": [cid for cid, _ in ranked],
                     "returned": [r.chunk_id for r in results]})
        return list(results)
