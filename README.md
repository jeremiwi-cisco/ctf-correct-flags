# CTF Correct Flags

Maintain Cisco CTF mission answers from a completed check-flags verification report. The skill audits every PASS row against the live portal, applies each CHANGED row's suggested regex, verifies saved answers, and maintains a mission-specific baseline and append-only history.

**Start here:** open [the visual workflow guide](workflow-guide.html) in your browser for the seven-step workflow, interactive status examples, and invocation builder.

## What you need

- An agent that supports skills, local file access, and computer use of your existing Chrome session.
- Access to [Cisco CTF](https://play-security.ciscoctf.io/) mission content management in Chrome. You handle sign-in if the agent requests it; passwords are not supplied to the skill.
- The exact name of the Cisco CTF mission you want to audit and correct.
- A completed check-flags artifact in the original report format, at a path the agent can read.
- Python 3 on macOS/Linux for the bundled audit helper, which uses standard-library POSIX file locking. The helper is not a standalone browser automation tool.

## Install the shared package

### Step 1 of 2 — Extract the ZIP in your file manager

Extract `ctf-correct-flags.zip`. Keep the complete `ctf-correct-flags` folder together, including `SKILL.md`, the guide, references, and scripts.

### Step 2 of 2 — Place the folder in your agent's skills directory

For the default Codex location, use `~/.codex/skills/ctf-correct-flags/`. The `SKILL.md` file must sit directly inside that folder, rather than inside another nested copy of the folder. If your environment uses a custom skills directory, use that configured location.

The skill requires the agent's existing Chrome computer-use capability; copying the folder does not install that capability or grant portal access.

## Run the skill

### Step 1 of 3 — Send the invocation in your agent conversation

Replace both example values with the exact mission name and the full artifact path for this run:

```text
Use $ctf-correct-flags for mission "YOUR EXACT MISSION NAME".
The completed check-flags artifact for this run is at:
"/full/path/to/completed-results.md"
Audit all PASS rows, apply CHANGED suggested regexes,
verify saved changes, and record the results.
```

**Supply the artifact path for every invocation, even when the location is unchanged.** If it is absent, the agent asks for it before report preparation or portal operations. A remembered path, a previous run's path, and a default/latest-results location do not satisfy this requirement. If the supplied file is missing or unreadable, the agent requests a corrected path.

### Step 2 of 3 — Complete Chrome sign-in if the agent requests it

Use your existing Chrome session to authenticate to Cisco CTF. The agent then checks creator access and verifies the exact mission heading and identity before editing answers. If the mission or a flag is ambiguous, resolve the specific question the agent raises.

### Step 3 of 3 — Review the linked run report in your agent conversation

Check correction outcomes, live PASS audit coverage, test results, persistence verification, and unresolved issues. A source PASS is not proof that the live portal stores the correct answer pattern.

The example invocation authorizes answer updates in the named mission. If you want a read-only audit or teaching session, state that scope in your request.

## How report rows are handled

| Source status | Skill behavior |
| --- | --- |
| PASS | Inspect the live pattern and case setting, compare with the verified baseline, test Actual Value and durable examples, and close with Cancel. A different suggested regex alone does not authorize an edit. |
| CHANGED | Apply Suggested Regex, test Actual Value and durable examples, Save once, reopen, and verify persistence. If the intended pattern is already stored, test and record it as already applied. |
| ERROR | Report incomplete coverage and retain the previous verified baseline. |

The skill preserves case sensitivity, question text, hints, points, visibility, and flag type. Failed tests block saving. It does not generate replacement regexes or automatically run the upstream check-flags process.

## Report compatibility

Use the same artifact format as the original `correct-ctf-flags` skill: Date, Time, and Tenant metadata; optional Summary and Tenant URL; and a Results table with ID, Status, Question, Actual Value, Expected Pattern, Suggested Regex, and Notes in that order.

Actual Value is the concrete portal test input. Suggested Regex is the proposed expected-answer expression for CHANGED rows. Preserve regex characters and use only the report's documented escaping convention; see the [portal reference](references/portal-workflow.md).

## Where results are stored

Run evidence is saved in timestamped folders under `~/ctf-flag-correction-runs/`. Persistent state lives in:

- `~/ctf-flag-correction-runs/state/change-log.jsonl` — append-only event history.
- `~/ctf-flag-correction-runs/state/baseline.json` — current verified state projected from that history.

The original storage default is retained. Baselines are scoped by portal origin, observed mission UUID, and artifact tenant. Each mission's durable examples belong to its confirmed flag identities. A new mission does not inherit another mission's rules.

The shared skill package contains no personal run history, baseline files, screenshots, or credentials.

## Files in this package

| File | Purpose |
| --- | --- |
| [README.md](README.md) | Human-facing setup and usage instructions. |
| [workflow-guide.html](workflow-guide.html) | Self-contained visual guide; works offline without external assets. |
| [SKILL.md](SKILL.md) | Instructions loaded by the agent when the skill is used. |
| [references/portal-workflow.md](references/portal-workflow.md) | Cisco CTF editor navigation, regex transfer, testing, and save verification. |
| [references/change-log.md](references/change-log.md) | Baseline rules, observation format, and audit helper commands. |
| [scripts/audit_log.py](scripts/audit_log.py) | Local comparison and journal helper; `--artifact` is required on every call. |
| [agents/openai.yaml](agents/openai.yaml) | Skill display metadata and a suggested invocation. |

This is a distinct copy of `correct-ctf-flags`. It retains the original workflow and parameters, with a required artifact path supplied by the invoker for each run and portable installation references.
