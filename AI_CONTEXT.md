# Nightjar: AI Development Context

## Current baseline
- Project: Nightjar Data Analysis, a sailing/racing analytics website.
- Current working baseline: version 0.8.1.0, as confirmed by Bryn.
- The Java 0.9.x branch was rolled back because deployment and rapid prototyping were unsatisfactory.
- Do not reintroduce the Java migration or assume the 0.9.x architecture is current.
- Inspect the supplied current source files to establish the actual framework, dependencies, entry point and folder structure. Do not guess them.
- Source control: GitHub. Deployment: Railway. Local repository managed using GitHub Desktop on Windows. Folderpath: "C:\Users\Bryn.Phillips\OneDrive - Ward and Burke\Documents\99. MISC personal\Sailing\2026 - Nightjar\Website\github\NightjarRacing"
- Development priorities: reliable deployment, rapid iteration, preservation of working features.

## How to use this document
Provide this file with the current source files at the start of a coding session. Explicitly ask the assistant to read it. This document is project context, not a guarantee of automatic repository access, persistent memory or file-writing permissions.
Only claim to have read, edited, saved, committed, tested or deployed something when that action actually occurred using available access.

## Source of truth
1. The user's current request defines the requested change.
2. Current supplied source files define existing behaviour and implementation.
3. Verified tests and logs establish observed results.
4. CHANGELOG.md provides historical context, not proof that a feature exists in the current baseline.
If these conflict, identify the discrepancy rather than silently choosing an implementation.

## Scope and preservation
- Make the smallest coherent change that meets the request.
- Preserve unrelated behaviour, page layouts, styling, filters, exports and data compatibility.
- Do not remove features, rename endpoints or restructure the project unless necessary and explicitly requested.
- Avoid new dependencies unless justified; explain any required dependency changes.
- Keep changes easy to review and reverse.
- Do not increment the release version unless the user specifies the target version or requests a release.

## Restoring features from 0.9.x
- Treat the earlier proposed restoration list as an unverified candidate backlog, not an established comparison.
- Before restoring an item, check both the 0.8.1.0 source and the relevant 0.9.x source or release notes.
- Distinguish implemented features from requests, plans, bug fixes and Java-only refactoring.
- Mark items as confirmed missing, already present, partially present or not verified.
- Restore user-facing behaviour using the current baseline architecture, not by copying Java-specific infrastructure.

## Sailing data and analytical correctness
- Preserve variable names, units, sign conventions and timestamp handling unless a change is requested.
- Distinguish VMG values from VMG percentages. Never substitute one for the other.
- For requested VMG performance comparisons, use VMG values rather than VMG percentages unless instructed otherwise.
- Verify tack-colour and angle conventions against current source and user requirements before changing them.
- Keep raw analytical data separate from display-only downsampling.
- Do not invent input data or claim analytical results without actual data.

## Performance and reliability
- Avoid unnecessary copies of large datasets and repeated parsing.
- Review browser and server memory implications of changes.
- Preserve existing loading, filtering and downsampling behaviour unless changing it is in scope.
- Handle missing columns, malformed rows, empty selections and missing optional files explicitly.
- Do not hide exceptions behind empty results or silently discard data.

## Delivery requirements
- List changed files with exact repository-relative paths.
- Supply complete modified files when file output is available; avoid snippets requiring manual reconstruction unless requested.
- Do not replace omitted working code with placeholders such as 'existing code here'.
- State which checks actually ran, their results and which checks remain manual.
- Include a concise change summary, regression risks and rollback instructions.
- Never claim direct saving to a local folder or GitHub without a connected write capability and a successful action.

## Security and deployment
- Never include passwords, tokens, private keys or real secret values in source, examples or logs.
- Use placeholder variable names when discussing configuration.
- Inspect the current Railway configuration before proposing build or start commands.
- Do not assume the deployed branch or automatic deployment settings.
- Prefer reviewing changes on a branch before merging into the deployment branch.
- Do not push, merge or deploy without an explicit user request and available authorised tools.

## Project details to maintain
- Current release: 0.8.1.0
- Repository: \NightjarRacing
- Deployment branch: Dev
- Framework and runtime: 
- Local start command: 
- Test command:
- Railway build/start configuration: "python -m streamlit run app.py --server.address=0.0.0.0 --server.port=8080 --server.headless=true --browser.gatherUsageStats=false"
- Known issues: Known_Issues.md

## Maintenance
- Update the current release, verified commands, architecture and known issues after accepted changes. Record completed work in CHANGELOG.md by adding to existing file and keep unimplemented work clearly labelled as planned.
