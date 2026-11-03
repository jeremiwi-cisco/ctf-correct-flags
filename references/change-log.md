# Verified baseline and append-only change log

## Storage and identity

Store persistent state outside the installed skill:

- `~/ctf-flag-correction-runs/state/change-log.jsonl`: one JSON event per run, appended after observations. Records source hash, source timestamp, mission, observed patterns, prior baseline, test evidence, and baseline decisions.
- `~/ctf-flag-correction-runs/state/baseline.json`: current verified patterns and durable behavioral tests, projected from that journal. The helper reconstructs this state from the log before comparisons, so a stale projection cannot hide a recorded change.
- A timestamped run folder: artifact snapshot, browser observations, comparison output, report, and screenshots.

Scope each baseline by portal origin, observed mission UUID, and CII tenant. Keep the user-provided exact mission name in the record. Each source flag ID maps to a stable portal flag UUID, displayed sequence number, title, question, regex, and case-sensitivity setting. A numbering mismatch is an explicit issue; the recorded mapping supports read-only audits but does not authorize edits to a differently numbered flag.

Establish an initial baseline only after confirming the user-named mission and testing its artifact answers in the live portal. No mission baseline is bundled with this skill. Historical correction reports are supporting evidence; do not turn their hand-escaped Markdown/JSON strings into a baseline when exact browser field values are available.

## Comparisons on every run

Run `scripts/audit_log.py prepare` after reading the artifact and confirming mission identity. It compares every PASS and CHANGED row with the last verified baseline. It never controls the browser or edits the artifact.

| Signal | Meaning and handling |
|---|---|
| Artifact Expected Pattern differs from baseline | Upstream source difference. Test the actual answer in the portal; report the difference even if accepted. Different regex strings can have equivalent behavior, so string inequality alone is not a failed answer. |
| PASS Suggested Regex differs from baseline | A proposal, not proof of drift. PASS suggestions often tighten a valid range. Preserve the verified portal pattern unless a correction is requested or portal testing shows a real failure. |
| Live portal pattern, identity, or case setting differs from baseline | Portal drift. Record it and preserve the previous baseline. Do not silently adopt it after a one-answer test. |
| Portal rejects the artifact Actual Value | Answer failure, regardless of upstream PASS. Record the failure and leave the baseline intact; do not automatically replace a PASS row's regex. |
| Durable acceptance/rejection example fails | Behavioral regression. Do not save the proposed regex. |
| No previous baseline | Inspect and test before seeding; a source PASS alone cannot establish a portal baseline. |
| Baseline flag missing from the artifact or artifact row is ERROR | Report incomplete coverage; preserve its previous record. |
| CHANGED suggestion already equals the live verified pattern | Test and log as already applied; a stale upstream CHANGED status does not require another save. |

Audit **all PASS rows in the live portal** on every normal run: read the field and case setting, compare with baseline, test Actual Value and stored durable examples, and close with Cancel. Do not claim a live PASS audit when only offline comparisons were performed. If the user explicitly limits a run, report the unaudited rows as not checked this run.

CHANGED rows still use the suggested-regex correction procedure, subject to the same identity and durable behavioral checks. Advance an existing baseline only after a requested correction has passed tests and been saved and reopened. For a PASS-row drift that the user wants to accept as a new intended policy, obtain that policy decision and update the recorded rules explicitly; a routine audit cannot adopt it automatically.

## Durable behavioral rules

Store stable policy examples separately from each run's Actual Value. Numeric counts and other dynamic observations are **not** permanent acceptance requirements. A future correction may legitimately stop accepting an old count.

Use the durable examples already stored for the confirmed mission and portal flag UUIDs. Establish any new examples from that mission's verified requirements and live tests. Never apply another mission's examples just because its flag numbers or titles resemble the current mission. The helper refuses to advance/refresh a baseline when previously stored examples were not retested successfully. Changing a durable policy requires an explicit user decision and documented migration of its examples.

## Helper commands

Run these in the terminal through the command tool. The helper uses Python 3 and POSIX `fcntl` file locking (macOS/Linux). Resolve `SKILL_DIR` to the actual installed `ctf-correct-flags` directory. Set `ARTIFACT_PATH` from the path the invoker explicitly supplied for this run; request a fresh path for every invocation rather than reusing either variable across runs. Replace the mission name and UUID with user input and the observed mission identifier.

`--artifact-escaping legacy-markdown` is appropriate only when the report is known to double regex backslashes and escape table alternation pipes. Otherwise use the original default `literal`. This affects source parsing only; browser observations and baseline JSON must contain the exact raw field text, serialized once. Keep the original artifact format: Date, Time, and Tenant metadata; optional Summary and Tenant URL; a Results table with ID, Status, Question, Actual Value, Expected Pattern, Suggested Regex, and Notes in that order. No alternate report format is introduced by this copy.

```bash
python3 "$SKILL_DIR/scripts/audit_log.py" prepare \
  --mission 'USER-PROVIDED MISSION NAME' \
  --mission-id 'OBSERVED-MISSION-UUID' \
  --artifact "$ARTIFACT_PATH" \
  --artifact-escaping literal
```

Save the prepare output and its `artifact.sha256` in the run folder. Snapshot the artifact at that point: its date/time can remain the same even after a correction. Record the browser observations as a JSON list. Each item uses:

```json
{
  "artifact_flag_id": 19,
  "portal_flag_id": "OBSERVED-FLAG-UUID",
  "display_number": 19,
  "title": "Observed flag title",
  "question": "Observed question",
  "pattern": "^Example;\\s?39$",
  "case_sensitive": false,
  "portal_verified": true,
  "tests": [{"answer": "Example; 39", "expected": true, "accepted": true}],
  "contract_tests": []
}
```

`portal_verified` means the stored pattern and test feedback were read in the current UI. For an actual update, also record `pattern_before` and `saved_and_reopened: true`. `tests` contains this run's actual-answer check and every stored policy example. `contract_tests` contains only deliberately durable examples to add, never dynamic counts. Keep the observed true/false result even if unexpected.

```bash
python3 "$SKILL_DIR/scripts/audit_log.py" record \
  --mission 'USER-PROVIDED MISSION NAME' \
  --mission-id 'OBSERVED-MISSION-UUID' \
  --artifact "$ARTIFACT_PATH" \
  --artifact-escaping literal \
  --expected-artifact-sha256 'HASH-FROM-PREPARE' \
  --observations /path/to/run/portal-observations.json \
  --kind audit \
  --reason 'Describe the verification or requested correction'
```

Use `--kind seed` for initial capture, `audit` for read-only verification, or `update` after confirmed saved corrections. The helper appends a log event and updates the baseline projection only from eligible verified observations. It records failed/drifted observations without replacing the last good baseline. It refuses a changed source hash, malformed artifact table, inconsistent summary, duplicate source IDs, and a malformed existing journal. State writes use a file lock; the projection is replaced atomically after the journal append.

The helper cannot verify that supplied observations genuinely came from Chrome. The agent must capture them from the browser; never populate successful test results from assumptions or from the upstream PASS label.
