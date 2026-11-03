#!/usr/bin/env python3
"""Compare check-flags artifacts with verified portal state and journal audits.

This helper never controls Chrome or decides regex acceptance. Observations and
test results must come from the portal UI; the journal is the source of truth
and baseline.json is a rebuildable projection of that journal.
"""

import argparse
import fcntl
import hashlib
import json
import os
import re
import sys
import tempfile
import uuid
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_STATE = Path.home() / "ctf-flag-correction-runs" / "state"


def table_cells(line):
    """Do not mistake alternation pipes inside code spans for cell boundaries."""
    cells, current, fence = [], [], 0
    index = 0
    while index < len(line):
        char = line[index]
        if char == "`":
            end = index
            while end < len(line) and line[end] == "`":
                end += 1
            run = end - index
            if fence == 0:
                fence = run
            elif fence == run:
                fence = 0
            current.append(line[index:end])
            index = end
            continue
        slashes = 0
        for previous in reversed(current):
            if previous != "\\":
                break
            slashes += 1
        if char == "|" and fence == 0 and slashes % 2 == 0:
            cells.append("".join(current).strip())
            current = []
        else:
            current.append(char)
        index += 1
    if fence:
        raise ValueError("Unclosed inline code span in Results table")
    cells.append("".join(current).strip())
    if cells and not cells[0]:
        cells.pop(0)
    if cells and not cells[-1]:
        cells.pop()
    return cells


def uncode(value):
    return value[1:-1] if value.startswith("`") and value.endswith("`") else value


def pattern_text(value, escaping):
    value = uncode(value)
    if escaping == "legacy-markdown":
        # Explicit input convention, not a guess about regex semantics.
        value = value.replace("\\\\", "\\").replace("\\|", "|")
    return value


def read_artifact(path, escaping):
    raw = path.read_bytes()
    text = raw.decode("utf-8")
    metadata = dict(re.findall(r"^- \*\*(Date|Time|Tenant|Tenant URL|Summary):\*\*\s*(.+)$", text, re.M))
    for required in ("Date", "Time", "Tenant"):
        if required not in metadata:
            raise ValueError(f"Artifact is missing {required}")
    body = re.search(r"^## Results\s*\n(.*?)(?=^## |\Z)", text, re.M | re.S)
    if not body:
        raise ValueError("Artifact is missing the Results section")
    flags = []
    for line in body[1].splitlines():
        if not line.lstrip().startswith("|"):
            continue
        cells = table_cells(line)
        if not cells or not cells[0].isdigit():
            continue
        if len(cells) != 7:
            raise ValueError(f"Flag {cells[0]}: expected 7 table columns, found {len(cells)}")
        flag_id, status, question, actual, expected, suggested, notes = cells
        if status not in ("PASS", "CHANGED", "ERROR"):
            raise ValueError(f"Flag {flag_id}: unknown status {status}")
        if status != "ERROR" and (uncode(actual) == "N/A" or uncode(suggested) == "N/A"):
            raise ValueError(f"Flag {flag_id}: missing answer or suggested regex")
        flags.append({"artifact_flag_id": int(flag_id), "status": status,
                      "question": question, "actual_value": uncode(actual),
                      "expected_pattern_raw": uncode(expected),
                      "suggested_regex_raw": uncode(suggested),
                      "expected_pattern": pattern_text(expected, escaping),
                      "suggested_regex": pattern_text(suggested, escaping), "notes": notes})
    ids = [flag["artifact_flag_id"] for flag in flags]
    if not ids or len(ids) != len(set(ids)):
        raise ValueError("Artifact has no flag rows or contains duplicate flag IDs")
    declared = {status: int(count) for count, status in re.findall(r"(\d+)\s+(PASS|CHANGED|ERROR)", metadata.get("Summary", ""))}
    counts = Counter(flag["status"] for flag in flags)
    if declared and any(declared.get(status, 0) != counts[status] for status in ("PASS", "CHANGED", "ERROR")):
        raise ValueError("Artifact summary disagrees with Results table")
    return {"path": str(path.resolve()), "sha256": hashlib.sha256(raw).hexdigest(),
            "date": metadata["Date"], "time": metadata["Time"], "tenant": metadata["Tenant"],
            "tenant_url": metadata.get("Tenant URL"), "escaping": escaping,
            "summary": dict(counts), "flags": flags}


def scope_key(mission, tenant):
    identity = [mission["portal_origin"], mission["portal_mission_id"], tenant]
    return hashlib.sha256(json.dumps(identity, ensure_ascii=False).encode()).hexdigest()


def load_journal(state_dir):
    path = state_dir / "change-log.jsonl"
    if not path.exists():
        return []
    events = []
    for number, line in enumerate(path.read_text().splitlines(), 1):
        try:
            event = json.loads(line)
            if event["schema_version"] != 1 or not isinstance(event["rows"], list):
                raise ValueError("unsupported event")
            events.append(event)
        except (ValueError, KeyError, TypeError) as error:
            raise ValueError(f"Invalid journal line {number}; repair from evidence before appending") from error
    return events


def projection(events):
    result = {"schema_version": 1, "missions": {}}
    for event in events:
        key = scope_key(event["mission"], event["artifact"]["tenant"])
        mission = result["missions"].setdefault(key, {"mission": event["mission"], "tenant": event["artifact"]["tenant"], "flags": {}})
        for row in event["rows"]:
            if row["baseline_action"] in ("seed", "refresh", "update"):
                mission["flags"][str(row["artifact_flag_id"])] = row["baseline_after"]
    return result


def comparisons(artifact, baseline):
    rows = []
    for flag in artifact["flags"]:
        previous = baseline.get(str(flag["artifact_flag_id"]))
        row = dict(flag)
        row["baseline"] = previous
        row["source_expected_differs"] = bool(previous and flag["expected_pattern"] != previous["pattern"])
        row["suggested_differs"] = bool(previous and flag["suggested_regex"] != previous["pattern"])
        row["numbering_mismatch"] = bool(previous and previous["display_number"] != flag["artifact_flag_id"])
        row["needs_live_audit"] = flag["status"] != "ERROR"
        row["needs_update"] = flag["status"] == "CHANGED" and (not previous or row["suggested_differs"])
        row["already_applied"] = flag["status"] == "CHANGED" and previous is not None and not row["suggested_differs"]
        rows.append(row)
    missing = sorted(set(baseline) - {str(f["artifact_flag_id"]) for f in artifact["flags"]}, key=int)
    return {"rows": rows, "missing_from_artifact": missing}


def tests_pass(tests):
    return bool(tests) and all(isinstance(t.get("expected"), bool) and isinstance(t.get("accepted"), bool)
                               and t["expected"] == t["accepted"] for t in tests)


def atomic_json(path, data):
    fd, temporary = tempfile.mkstemp(prefix=path.name + ".", dir=path.parent)
    try:
        with os.fdopen(fd, "w") as output:
            json.dump(data, output, indent=2, ensure_ascii=False)
            output.write("\n")
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def record(args, artifact, mission):
    observations = json.loads(args.observations.read_text())
    if not isinstance(observations, list):
        raise ValueError("Observations must be a JSON list")
    ids = [obs["artifact_flag_id"] for obs in observations]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate observation flag IDs")
    source = {flag["artifact_flag_id"]: flag for flag in artifact["flags"]}
    if set(ids) - set(source):
        raise ValueError("Observation refers to a flag absent from the artifact")
    args.state_dir.mkdir(parents=True, exist_ok=True)
    with (args.state_dir / ".journal.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        events = load_journal(args.state_dir)
        baselines = projection(events)
        current = baselines["missions"].get(scope_key(mission, artifact["tenant"]), {}).get("flags", {})
        rows = []
        for obs in observations:
            flag = source[obs["artifact_flag_id"]]
            previous = current.get(str(obs["artifact_flag_id"]))
            # Preserve previous behavioral requirements: a one-answer success must
            # never erase prior accepted variants or negative examples.
            required_tests = previous.get("contract_tests", []) if previous else []
            tests = obs.get("tests", [])
            observed_cases = {(test.get("answer"), test.get("expected")) for test in tests}
            missing_tests = [t for t in required_tests if (t["answer"], t["expected"]) not in observed_cases]
            actual_tested = any(t.get("answer") == flag["actual_value"] and t.get("expected") is True and t.get("accepted") is True for t in tests)
            valid = obs.get("portal_verified") is True and flag["status"] != "ERROR" and tests_pass(tests) and actual_tested and not missing_tests
            for field in ("portal_flag_id", "title", "pattern", "display_number", "case_sensitive"):
                if field not in obs:
                    raise ValueError(f"Flag {obs['artifact_flag_id']}: missing live field {field}")
            if not isinstance(obs["case_sensitive"], bool):
                raise ValueError("case_sensitive must be a JSON boolean")
            drift = bool(previous and any(obs[field] != previous[field] for field in ("portal_flag_id", "title", "pattern", "display_number", "case_sensitive")))
            action = "retained"
            if valid and not previous:
                action = "seed"
            elif valid and not drift:
                action = "refresh"
            elif valid and args.kind == "update" and obs.get("saved_and_reopened") is True:
                if previous and obs.get("pattern_before") != previous["pattern"]:
                    raise ValueError("Update before-pattern does not match the baseline; resolve portal drift first")
                if obs["pattern"] != flag["suggested_regex"]:
                    raise ValueError("Updated pattern does not equal the artifact Suggested Regex")
                if previous and any(obs[field] != previous[field] for field in ("portal_flag_id", "title", "display_number", "case_sensitive")):
                    raise ValueError("A regex update cannot silently change flag identity or case sensitivity")
                if obs["display_number"] != flag["artifact_flag_id"]:
                    raise ValueError("Resolve numbering mismatch before recording an automatic update")
                action = "update"
            contract = list(required_tests)
            for test in obs.get("contract_tests", []):
                item = {"answer": test["answer"], "expected": test["expected"]}
                if (item["answer"], item["expected"]) not in observed_cases:
                    raise ValueError("A new contract test must be exercised in the portal before recording")
                if item not in contract:
                    contract.append(item)
            baseline_after = {field: obs[field] for field in ("portal_flag_id", "title", "pattern", "display_number", "case_sensitive")}
            baseline_after.update({"question": obs.get("question", flag["question"]),
                                   "contract_tests": contract, "verified_at": args.recorded_at,
                                   "artifact_sha256": artifact["sha256"], "evidence": str(args.observations.resolve())})
            rows.append({"artifact_flag_id": obs["artifact_flag_id"], "source_status": flag["status"],
                         "actual_value": flag["actual_value"], "expected_pattern": flag["expected_pattern"],
                         "suggested_regex": flag["suggested_regex"], "baseline_before": previous,
                         "observed": obs, "portal_drift": drift, "tests_passed": valid,
                         "missing_contract_tests": missing_tests, "baseline_action": action,
                         "baseline_after": baseline_after if action != "retained" else previous})
        not_observed = sorted(set(source) - set(ids))
        missing_from_artifact = sorted(set(current) - {str(flag_id) for flag_id in source}, key=int)
        event = {"schema_version": 1, "event_id": str(uuid.uuid4()), "recorded_at": args.recorded_at,
                 "kind": args.kind, "reason": args.reason, "mission": mission, "artifact": artifact,
                 "evidence": str(args.observations.resolve()), "not_observed": not_observed,
                 "missing_from_artifact": missing_from_artifact, "rows": rows}
        with (args.state_dir / "change-log.jsonl").open("a") as output:
            output.write(json.dumps(event, ensure_ascii=False) + "\n")
            output.flush()
            os.fsync(output.fileno())
        events.append(event)
        atomic_json(args.state_dir / "baseline.json", projection(events))
        return {"event_id": event["event_id"], "recorded_rows": len(rows),
                "verified_rows": sum(row["tests_passed"] for row in rows),
                "not_observed": not_observed, "missing_from_artifact": missing_from_artifact,
                "baseline_actions": dict(Counter(row["baseline_action"] for row in rows)),
                "journal": str(args.state_dir / "change-log.jsonl"), "baseline": str(args.state_dir / "baseline.json")}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("prepare", "record"))
    parser.add_argument("--mission", required=True, help="Exact user-supplied mission name")
    parser.add_argument("--mission-id", required=True, help="Portal mission UUID observed in the browser")
    parser.add_argument("--portal-origin", default="https://play-security.ciscoctf.io")
    parser.add_argument("--artifact", type=Path, required=True,
                        help="Artifact path explicitly supplied by the invoker for this run; no default")
    parser.add_argument("--artifact-escaping", choices=("literal", "legacy-markdown"), default="literal")
    parser.add_argument("--expected-artifact-sha256", help="Require the prepare-time hash before recording")
    parser.add_argument("--state-dir", type=Path, default=DEFAULT_STATE)
    parser.add_argument("--observations", type=Path)
    parser.add_argument("--kind", choices=("seed", "audit", "update"), default="audit")
    parser.add_argument("--reason", default="Portal verification")
    args = parser.parse_args()
    if not args.mission.strip() or not args.mission_id.strip():
        parser.error("Mission name and ID must not be blank")
    artifact = read_artifact(args.artifact.expanduser(), args.artifact_escaping)
    if args.expected_artifact_sha256 and artifact["sha256"] != args.expected_artifact_sha256:
        raise ValueError("Artifact changed since prepare; inspect the new artifact before recording")
    mission = {"name": args.mission, "portal_origin": args.portal_origin.rstrip("/"), "portal_mission_id": args.mission_id}
    args.recorded_at = datetime.now(timezone.utc).isoformat()
    if args.command == "prepare":
        baseline = projection(load_journal(args.state_dir))["missions"].get(scope_key(mission, artifact["tenant"]), {}).get("flags", {})
        result = {"mission": mission, "artifact": artifact, **comparisons(artifact, baseline)}
    else:
        if not args.observations or not args.expected_artifact_sha256:
            parser.error("record requires --observations and --expected-artifact-sha256")
        result = record(args, artifact, mission)
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError, KeyError, TypeError) as error:
        print(f"Error: {error}", file=sys.stderr)
        sys.exit(1)
