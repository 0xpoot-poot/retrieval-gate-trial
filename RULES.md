# RULES

## Part A. The access rules the choke point must enforce

These are the rules for this kit, a model of the rules our real choke point must enforce. A correct `retrieve()` obeys all of them.

1. **Users.** Only users listed in `matters.json` may retrieve anything. Anyone else is denied.
2. **No matter.** With `matter_id=None`, a user may retrieve public-law chunks only (chunks whose `matter_id` is null).
3. **Matter access.** For a matter, the user must be listed in its `members`, must not be listed in its `walled_off`, and the matter's client must not have `"ai_use": "prohibited"` in `clients.json`. Otherwise the call raises `PermissionDenied`.
4. **Within a matter,** the user may see public-law chunks plus that matter's chunks, except:
   - a chunk whose document has `restricted_to` is visible only to the users listed there;
   - a chunk of class `BLACK` (sensitive personal data such as health) is visible only to users in the matter's `black_cleared` list.
5. **Classify up.** A chunk with no class, or an unrecognised class, is treated as `BLACK`.
6. **Prohibited clients are never indexed.** Chunks of a client with `"ai_use": "prohibited"` must not be searchable by anyone, in any call.
7. **Changes take effect immediately.** `matters.json` may be replaced while the service runs (for example, a new ethical wall). The next call must obey the new file.
8. **Narrow candidates, not results.** A chunk the user may not see must not reach any search leg's candidates, the fusion step, the reranker, the cache or the audit log, not only the final results.
9. **Denials are logged.** Every denied call writes an audit record with `"decision": "deny"`.

## Part B. Excerpts from the posture (for Part 2)

Summaries and excerpts, lightly edited. Section numbers refer to the source documents.

**B1. Firm data-processing agreement v5, Schedule 2: the seven minimum measures (summary)**
1. Named accounts with multi-factor authentication.
2. Role-based access enforced **before retrieval**, by matter, client and document.
3. Encryption at rest and in transit.
4. Every access and every query logged, including the passages retrieved, kept at least 12 months.
5. Segregation: no indexes or models shared with other customers.
6. No removable media, personal devices, personal cloud or consumer AI tools; secure deletion including backups,
   within 14 days of a request, certified by a director.
7. Security briefing, patching, tested backups, physical security.

**B2. Firm AI policy (draft for adoption, clause numbers as in the document)**
- 5.1 four data classes GREEN / AMBER / RED / BLACK (BLACK = PDPA section 26 sensitive data); 5.2 classify up when in doubt.
- 9.1 a client preference register: no restriction / prior approval / AI prohibited.
- 11.3 "Verification is never performed by another AI tool, and never by the tool that produced the text."
- 13.4 index deletion at matter closure; 13.5 un-indexing on client request, at any time.
- 14.1 ethical walls: "no shared assistants, no shared indexes"; 14.3 "No AI system is given access to a matter a
  person on the team could not lawfully open."
- 15.6 "If personal data is absorbed into a vendor's model, the rights of erasure and rectification cannot be honoured."
- 17.3 no AI communicates with a client without a human in the loop.

**B3. Approved environments (project brief)**
- Client material only on the firm's on-premise server.
- SaangAI's Thailand servers for non-client firm data and public law.
- International cloud GPUs for legislation and synthetic data only.
- One whitelisted exit from the firm server: a sanctions-screening provider, a company-registry lookup, and a cloud GPU for public data.

**B4. Product description (project brief)**
- A lawyer reviews each draft and gives one-line feedback. Over time the feedback trains rules and, with the firm's consent and on the firm's hardware, firm-owned model adapters.
- Every statement of law must cite a section whose text supports it, checked by a deterministic citation gate.
- Models run locally via Ollama.

**B5. SaangAI Secure Build and Deployment Guide (excerpts)**
- §1.3: "The person who builds a release must not be the person who signs it."
- §2.1: Firm → SaangAI: "Nothing by default. No telemetry, no phone-home, no remote access."
- §3, decision D5: tuning on firm data "Not in version 1; revisit after the pilot."
- §5.3: Personal laptops are not enrolled in device management; they reach SaangAI systems through Cloudflare Zero Trust with browser isolation.
- §8.2: The model is served by vLLM in a container.
- §9.2 step 7: "The app checks every cited chunk_id was among the retrieved passages; otherwise it removes the claim."
- §9.3: The rules engine allows a request if the user is in the matter's members and not in its walled_off list. Matter membership and walls come from the practice management system by **nightly export**.
- §9.4: "The model has no tools with side effects: it cannot send email, call URLs, write files or change permissions."
- §9.5: The audit record stores user, matter, decision, policy/library/model versions and `sources_cited`. "Whether the full question and answer text is kept is the firm's choice (question_logged)."
- §10.3: The signing subkey is moved "onto two YubiKeys, one per engineer."
- §11.1: Outbound from the firm server: "None needed; optional HTTPS to releases.<domain> for updates." The firm backs up `/etc/saangai` and the audit log.
- §11.2 config: `audit: syslog: tcp://<FIRM_SIEM_HOST>:514` and `matters: source: file` (nightly export).

**B6. Notes from the project's own design review (excerpts)**
- Every retrieval in the current prototype goes through one function with exactly two callers; two helper functions
  that expand a query (cross-references, statute wording) "may reach the store directly: unverified".
- The prototype's "never does" gate reserves a fixed list of actions (send, sign, quote a fee, file, delete) to named
  human roles. Its own docstring: "Unknown actions are allowed (only the listed ones are reserved)."
- The prototype's access check gives the CEO and the Executive Director firm-wide reach over every matter.
- A lawyer's hand edit that fails the drafting guards is stored as a new version, flagged. The module's comment: the
  deliverable builder excludes a flagged version, but "nothing on the send path reads it".
- The audit log records each query and the retrieved passages. The review's question: does the log respect the walls,
  or can a partner auditing compliance read a matter they are walled off from?
- Eight trust boundaries were listed for the review: class tagging at ingestion; index topology (one index with ACLs
  or separate indexes per wall); the retrieval choke point; the model-context boundary (can retrieved text change what
  the agent does); egress; tuning versus retrieval; deletion reach (chunks, vectors, lexical postings, rows, cached
  summaries, backups, logs); and the audit log as a data store.
