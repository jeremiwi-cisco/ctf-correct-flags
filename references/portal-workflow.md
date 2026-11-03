# Demonstrated Cisco CTF portal workflow

Use the invoker's existing authenticated Chrome session. This procedure preserves the original skill's demonstrated Cisco CTF workflow. Treat labels as navigation guidance, and derive live controls from the current screen. Mission names, flag numbers, UUIDs, and accessibility indices from other runs are not reusable constants.

## Locate the mission and flag

The portal origin is `https://play-security.ciscoctf.io/`. Creator access exposes **Content Mgmt** and **Manage Flags / Missions**. Use the observed navigation to reach that page after confirming authentication. Do not hardcode the portal's encoded path prefix or an example mission URL.

The **All Missions** sidebar groups missions into sections. Match the full user-provided mission name; open its link and verify the corresponding **Mission:-** heading in the main content. Multiple missions can coexist in the page DOM, so scope flag selection to that mission's container. An anchor or matching sidebar link alone does not establish that the desired flag belongs to the correct mission.

Each flag row displays its sequence number, title, points, and a **+** expand button. Expansion reveals the question, expected answer, type, case-sensitivity indicator, hints, and **Available Actions for this Flag**.

## Open the correct editor

Choose **Available Actions for this Flag → Edit this Flag's Content**. This opens the **Edit Flag** dialog. The **Read More Task Details Page → Edit** button edits a different page and is not the answer editor.

Within the dialog, scroll its own content area as needed. Inspect:

- **Flag Name** and **Flag Type** to confirm the target.
- **Answer is Case-sensitive?** Yes/No radio buttons.
- **Expected Flag (Answer)**: the stored regex to replace.
- **Test Flag (Answer)**: the concrete verified answer used for validation.
- **Save** and **Cancel** at the dialog's bottom.

The summary indicator `[NCS]` denotes a case-insensitive answer; it is not part of the regex.

Observed input IDs were `edit-flag-token`, `edit-flag-test-token`, and `edit-flag-submit` for expected answer, test answer, and Save. Use these only when confirmed in the live UI. Accessibility indices change after editing, testing, opening menus, and saving; get fresh state before relying on them.

## Transfer regex text faithfully

Some handoffs use doubled backslashes inside Markdown inline code to represent regex backslashes. For an artifact explicitly using that convention, `^Example\\sAnswer$` represents the browser field text `^Example\sAnswer$`.

Do not assume every Markdown report uses doubled escapes. Future reports may contain a single backslash already. Compare the report's representation with known regex syntax and, when needed, the source definitions or corresponding run-history entry read-only. Decode the display layer exactly once. Never globally strip backslashes, use a broad Unicode escape decoder, or collapse a genuine regex literal-backslash sequence. If meaning is ambiguous, request clarification for that flag.

Remove surrounding Markdown backticks. A Markdown-escaped `\|` used to preserve a table cell may represent a regex alternation `|`; distinguish it from an intentionally escaped literal pipe using the source context. The Changed Flags section can provide an equivalent pattern outside the table. Do not use a naive split on every pipe to parse the table.

The actual test string is separate from the regex. Preserve its spaces, punctuation, casing, and provider list. Do not submit the regex text as the test answer.

## Validate, save, and verify

After filling **Test Flag (Answer)**, move focus away (Tab worked in the trial). Wait for and inspect **Test Flag matches with the Expected Flag**, accompanied by a checkmark. Merely seeing a filled test field is not a pass.

The portal notes that it normalizes leading/trailing whitespace and spacing around some punctuation. Its visible tester is the acceptance check; a local regex test alone does not establish portal acceptance.

Click **Save** once. The button may briefly disable while saving. Wait for the dialog heading to disappear, then inspect the flag-specific **SUCCESS** message: **The flag - [flag title] is updated**. Saving can reposition the page, and the flag may need to be brought back into view.

Reopen **Edit this Flag's Content** and read **Expected Flag (Answer)** and the checked case-sensitivity option. Compare them with the intended saved values. Close with **Cancel** after this read-only confirmation. Capture screenshot evidence with the flag number/title, saved regex, and success message visible when possible.

If the current question clearly matches but its format guidance conflicts with the verified answer, record that discrepancy in the report. This workflow changes only the answer regex; do not repair hints or question text as a side effect.
