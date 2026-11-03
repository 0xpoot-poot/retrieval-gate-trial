# The retrieval choke point — a working session

This is a two-hour session with us, not a take-home. We will sit with you, talk through the problem, and you will test
your ideas on the kit as we go. Bring a laptop with Python 3.10+ and `pytest`; nothing else is needed, and no internet.
Use whatever tools you normally use, including AI assistants; we are interested in how you think and what you check.
Everything in the kit is invented: clients, people, matters and "law" are synthetic.

## The real problem

We are building an offline legal assistant for a law firm. A lawyer picks a matter (a client case) and asks a
question. The system searches the firm's documents for that matter, plus a public-law library, and hands the best
passages to a local AI model.

The firm's data-processing agreement says access must be enforced **before** retrieval: the permission filter must
*narrow the candidate set, not the result set*. A passage the lawyer may not see must never reach any stage of the
search, not just be removed at the end. In our system every search passes through one function. That function is the
choke point, and whether it really obeys that rule is a live question for us, not an exercise we invented.

## How the session goes

**First, before any code (about 20 minutes).** We describe the rules (`RULES.md` Part A) and the shape of the
function. You tell us how you would go about proving it obeys them. What would you test first, what would convince
you, what could a results-only test never see?

**Then, with the kit (about 70 minutes).** `kit/saangai_retrieval/retrieve.py` is a small model of our choke point,
and it has flaws. Write tests in `kit/tests/test_trial.py` that check the rules, run them, and show us what you find
as you find it. A test should pass on a correct implementation and fail on this one; each failure is a finding. We
have other versions of the function you have not seen, some correct and some broken, and at the end we run your
tests against them together.

**Then, the wider picture (about 20 minutes).** `RULES.md` Part B has excerpts from the firm's agreement, its AI
policy, and our own design review. Pick the three things you would escalate first and tell us why those three.

**Last (about 10 minutes).** What do your tests not prove?

`SESSION.md` lists the questions we will be asking along the way, so nothing is a surprise.

## Getting started

```bash
cd kit
python -m pytest                       # the two example tests should pass
python -m saangai_retrieval --user u02 --matter M-2026-101 "purchase price"
python -m saangai_retrieval --user u02 "lease registration"     # public law only
```

**API**

```python
from saangai_retrieval import Retriever, PermissionDenied, default_reranker

r = Retriever(data_dir, audit_path=None, reranker=None)
results = r.retrieve(user, matter_id_or_None, query, k=5)   # list[Result] or raises PermissionDenied
# Result fields: chunk_id, doc_id, matter_id, client_id, cls, text, score
# reranker: any callable (query, passages: list[dict{chunk_id, text}]) -> list[float]
# The audit log is JSON lines; each allowed call records "reranked" and "returned" chunk ids.
```

**Fixtures** (in `conftest.py`): `data_dir` gives each test a fresh writable copy of the data; `make_retriever(**kwargs)`
builds a `Retriever` on it; `audit_records()` reads its audit log.

**Data** (`kit/data/`): `matters.json` (the nightly permissions export: users, members, walls), `clients.json` (client
register), `documents.json`, `chunks.jsonl`.

## What we are looking for

Not a score. Whether your tests catch broken implementations without failing correct ones; whether you can say what
"narrow the candidates, not the results" means for a test; whether your claims match your evidence; and whether, when
you read the posture, you escalate the things that matter most. If you run out of time with findings unproven, say
so and tell us what you would do next.
