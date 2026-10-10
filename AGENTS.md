# AGENTS.md

Guidelines and instructions for autonomous agents working in this repository.

## Change Request Workflow

Whenever you are asked to make a change in this codebase, you must strictly follow this lifecycle:

1. **Open a Ticket (Issue)**
   - Before modifying code or files, create a new GitHub issue using the GitHub CLI:
     ```bash
     gh issue create --title "<Issue title>" --body "<Description of requested changes and plan>"
     ```
   - Note the created issue number (e.g. `#12`).

2. **Implement Changes and Verify**
   - Make the required modifications to the code or documentation.
   - Verify tests pass and no regressions are introduced:
     ```bash
     uv run pytest
     ```

3. **Commit Changes**
   - Stage and commit all relevant changes with a clear commit message referencing the issue:
     ```bash
     git add <changed-files>
     git commit -m "<summary of changes> (closes #<issue-number>)"
     ```

4. **Close the Ticket**
   - Close the ticket using `gh` once the work is verified and committed:
     ```bash
     gh issue close <issue-number> --comment "Completed in commit $(git rev-parse --short HEAD)"
     ```
   - Push the commit to the remote tracking branch:
     ```bash
     git push
     ```

---

## Development Environment & Commands

- **Package Manager**: `uv`
- **Run CLI**: `uv run wallet-look`
- **Run Tests**: `uv run pytest`
- **GitHub CLI**: `gh`
