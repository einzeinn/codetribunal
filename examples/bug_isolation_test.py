# bug_isolation_test.py
# Minimal test case for CodeTribunal scoring pipeline.
# Designed to isolate TWO specific bugs observed in prior runs:
#
#   BUG 1: LLM self-reports a score in its verdict text ("Security scores
#          X out of 10...") that does NOT match the deterministic
#          score_block appended afterward by _compute_rubric_scores().
#          Root cause candidate: the prompt's closing instruction
#          ("end with your final verdict: APPROVED/...REJECTED") is being
#          interpreted by the LLM as permission to restate numeric scores
#          it was never given, since scoring now happens AFTER generation.
#
#   BUG 2: Finding counts balloon across cross-exam rounds (e.g. "80
#          confirmed security findings" for a ~15-line file), suggesting
#          AgentFinding objects are being duplicated per round instead of
#          updated/deduplicated by finding_id.
#
# This file is intentionally tiny (one obvious vuln, one obvious
# false-positive-prone import) so that any inflation in the final
# finding count or any mismatch between the two score statements is
# unambiguous and easy to spot in the transcript — there is no way a
# correct pipeline produces dozens of findings or two different score
# triples from a file this small.

import hashlib

API_TOKEN = "tok_live_abc123"  # intentionally hardcoded, single obvious finding


def check_login(username, password):
    # Single, unambiguous SQL-injection-shaped string (no real DB call,
    # no subprocess, no pickle — keeps unrelated agents quiet so the
    # transcript stays small and any duplication is obvious)
    query = f"SELECT * FROM users WHERE username = '{username}' AND password = '{password}'"
    return query


def weak_hash(value):
    # Single, unambiguous weak-hash finding
    return hashlib.md5(value.encode()).hexdigest()
