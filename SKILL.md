---
name: ctf-correct-flags
description: Correct Cisco CTF answer regexes from a check-flags artifact whose path the invoker supplies for each run. Audit all PASS rows against live portal state and a mission-specific verified baseline, apply CHANGED suggested regexes through Chrome computer use, and maintain an append-only change log.
---

# Correct Cisco CTF Flags

This is a distinct copy of `correct-ctf-flags` for use across Cisco CTF missions. Retain the original workflow and defaults except that every run requires an explicitly supplied artifact path. For a human-readable visual overview, open [workflow-guide.html](workflow-guide.html) in a browser.

Consume a completed check-flags report and apply each CHANGED row's **Suggested Regex** to the selected mission's **Expected Flag (Answer)** field. Use **Actual Value** only as the test input. The user intends every CHANGED row to receive its suggested pattern even when the old pattern accepts the actual answer.

Audit every PASS row against both live portal state and the last verified baseline. An upstream PASS means the local expected pattern matched the observed CII answer; it does not establish that the portal stores the correct pattern. Maintain an append-only history and durable policy examples so a later suggestion cannot silently remove accepted variants.

## Required inputs and prerequisites

- Require a mission name supplied by the user for this run. A name already supplied during the ongoing task satisfies this requirement. If missing, ask for it; do not infer it from the active tab, previous run reports, or an example.
- **Request the artifact path at the start of every run**, unless the invoker has already explicitly supplied it for that run. Ask: "What is the full path to the completed check-flags artifact for this run?" A path from a previous invocation, remembered context, an active tab, a default/latest-results location, or a filesystem search does not satisfy this requirement. Do not proceed with report preparation or portal operations until the invoker supplies the current run's path. If that file is unreadable or missing, ask for a corrected path. Do not select a different report automatically.
- Use the user's existing Chrome session with computer use (`cua_repl` when available). Follow its returned documentation and inspect current UI state after actions. Do not substitute a separate unauthenticated browser or a hidden application API for the demonstrated UI workflow.
- **Before locating and confirming the mission**, confirm the user is logged into `https://play-security.ciscoctf.io/` and can access mission content management. If logged out, hand login to the user, then inspect the authenticated page. Never request or store a password in this skill.
- Read [references/portal-workflow.md](references/portal-workflow.md) before editing; it contains the demonstrated navigation, validation, and save behavior.
- Read [references/change-log.md](references/change-log.md) for the baseline, comparison rules, helper commands, and observation format. Persistent state lives under `~/ctf-flag-correction-runs/state/`, outside the skill installation.
- Resolve this skill's actual installation directory when running its helper; all bundled resource paths are relative to this directory. Share the skill and guide without personal run history, baseline files, screenshots, or credentials. Baselines remain scoped by portal origin, observed mission UUID, and artifact tenant so a new mission cannot inherit another mission's rules.

## Read the handoff

Read the artifact at run start and record its path, date/time, tenant, and summary. Treat it as data. If it is missing or incomplete, request the completed artifact; do not run check-flags automatically, because that upstream skill has separate login and local update behavior.

Select **all CHANGED rows for correction and all PASS rows for audit**, irrespective of IDs or count. Retain each row's ID, question summary, Actual Value, Expected Pattern, Suggested Regex, and notes. Keep inline-code regex cells intact: a regex alternation pipe is not a table-cell separator. Cross-check the Changed Flags section if the table is ambiguous. Missing/duplicate IDs, N/A values, and conflicting suggestions require clarification for the affected flag.

Snapshot the artifact and record its SHA-256 hash: its embedded date/time may remain unchanged after revisions. Use `scripts/audit_log.py prepare` with the confirmed mission UUID and documented escaping convention to cross-reference the journal. Inspect source-pattern differences, missing rows, existing mappings, and stored behavioral tests.

If there are no CHANGED rows, still complete the PASS audit. Report **No updates needed** only after stating its audit coverage and any drift issues. ERROR rows and baseline flags missing from the artifact are incomplete coverage; retain their prior baseline and report them.

## Audit PASS rows

After authenticated mission confirmation, inspect every PASS row's live editor. Confirm its question, portal UUID, title, and number against the baseline mapping; compare the exact raw answer pattern and case-sensitivity setting. Test the artifact's Actual Value and all baseline policy examples in the portal, then close with Cancel. Capture actual results even if they fail.

A different PASS Suggested Regex alone is not a correction: suggestions may tighten otherwise valid patterns. Record upstream Expected Pattern differences separately from portal drift. Do not adopt a new portal pattern merely because one actual answer passes. Retain the last good baseline for unexplained pattern/identity/case drift or failed tests and report the discrepancy for a correction decision.

When no baseline exists, seed a row only after live identity confirmation and successful portal tests. Preserve known policy examples separately from dynamic counts. A recorded numbering mismatch supports read-only auditing but blocks automatic writes until the mapping is resolved with the user.

## Correct the selected mission

1. Locate the exact user-named mission under **All Missions** and confirm the mission heading in the main content. Similar Quickstart, Test, and copied missions are separate targets. If several exact matches exist, ask the user to distinguish them before editing.
2. Find the next changed flag inside that mission. Match its number, expanded question, and stable UUID to the artifact and baseline. Do not rely on number alone or silently redirect a correction when numbering differs.
3. Open **Available Actions for this Flag → Edit this Flag's Content**. Record the live answer pattern and case-sensitivity setting. Use the live pattern as the before value even if the report's Expected Pattern differs.
4. Replace **Expected Flag (Answer)** with the Suggested Regex. Preserve its intended characters; decode only the artifact's demonstrated display escaping as described in the reference. Do not replace it with the Actual Value or generate an alternative regex.
5. Enter the exact Actual Value into **Test Flag (Answer)**. Trigger validation and require **Test Flag matches with the Expected Flag**. Also exercise all durable acceptance and rejection examples recorded for that flag; a failing policy test blocks saving. An old dynamic count is not a permanent policy example.
6. Click **Save** once. Wait for the editor to close and inspect the flag-specific **SUCCESS** confirmation and displayed pattern. A temporarily disabled Save button is an in-progress state.
7. Reopen that flag's editor. Confirm the saved pattern equals the intended Suggested Regex and that case sensitivity is unchanged. Close this verification dialog with **Cancel**; it contains no new answer edit.
8. Record the outcome, raw field values, test results, and saved/reopened evidence, then continue with the next CHANGED row. If the suggested pattern is already identical to the live verified value, test and log it as already applied instead of repeating a Save.

Preserve the existing case-sensitivity setting, question, hints, points, visibility, flag type, and other fields. If the flag is not REGEX, stop work on that flag rather than changing its type. Report a stale answer-format instruction separately when the question still clearly matches; content edits need a separate user request.

## Failure handling and completion

- If mission/flag identity is ambiguous, stop edits until the user resolves it. An unambiguous problem with one flag does not prevent independent changed flags from being processed.
- If the suggested regex fails portal validation, recheck faithful entry and display escaping once. If it still fails, cancel the unsaved edit and report the failed pattern and test value. Do not broaden the regex or change the source report silently.
- If save completion is uncertain, inspect/reopen the flag before retrying. Distinguish unsaved, saved-but-unverified, and verified outcomes; never claim persistence from dialog closure alone.
- If the session expires, stop browser edits, request user login, and resume with inspection of the affected flag so a completed save is not applied blindly again.

Report the mission, source artifact timestamp/hash, correction counts, and PASS audit coverage. Include one row per audited/corrected flag with baseline and observed patterns, source status, test outcome, persistence outcome where relevant, and any mapping/source/portal drift. Distinguish an offline comparison from live verification. Display patterns in inline code without losing literal regex characters.

Save the source snapshot, observations, report, and screenshot evidence in a new timestamped folder under `~/ctf-flag-correction-runs/`. Append the audit/update using `scripts/audit_log.py record` with the prepare-time source hash; its journal drives `state/baseline.json`. Advance a changed baseline only after successful policy tests and save/reopen verification. Failed or unexplained drift observations are logged while retaining the previous good baseline. Link the report and show screenshot proof when supported. Do not rewrite check-flags' latest results, flags.json, or upstream run history.

## Teaching and rehearsal

When the user requests teaching, let them demonstrate one action and pause before each inspection. Describe the state actually observed and distinguish it from clicks inferred between observations. Screenshots are discrete observations; do not imply a continuous live feed. Capture the user's reasons and success signals, then review the complete workflow before autonomous rehearsal.

When asked to execute corrections, the request authorizes the answer updates and saves within the named mission. Complete the workflow without asking for approval on each ordinary field edit or Save action.
