# Contributing a new rule, start to finish

This is a worked example of the smallest useful rule: a presence-only check
that an AI tool's config file exists, with no content validation. It's the
shape every `good first issue`-labeled "detect X" issue in this repo wants —
copy this pattern for any of them. For the full rule-authoring contract
(applicability, severity, the ERROR gate, tests, `docs/RULES.md`), see
[`CONTRIBUTING.md`](../CONTRIBUTING.md) § "Adding a rule" first; this doc is
the concrete walkthrough, that one is the reference.

Worked example: detect Cursor's rules directory (`.cursor/rules/*.mdc`) or
the legacy root `.cursorrules` file.

## 1. Pick the pillar module and write the rule function

New detection-only rules for "does this AI tool's config exist" usually
belong in `src/airx/rules/tooling.py` (environment/tooling signals) unless
the config is clearly safety-relevant (secrets exposure, exclusion lists —
those go in `safety.py`) or it's a genuine entry-point alternative to
`AGENTS.md`/`CLAUDE.md` (those go in `foundation.py`). When in doubt, open an
issue or ask in the PR — pillar placement is cheap to fix in review.

The simplest possible check uses `index.tree.resolves(...)` directly — it
needs no new `ArtifactKind` or `patterns.py` change, because you're only
asking "does this path exist in the scanned tree", not "read and validate its
contents":

```python
# src/airx/rules/tooling.py

@rule(
    id="tooling.cursor-rules.present", pillar=Pillar.TOOLING, scope=RuleScope.REPO,
    applicability=Applicability.PRESENCE, weight=2, severity=Severity.INFO,
    source=RuleSource.ADVISORY,
    doc_url="https://docs.cursor.com/context/rules",
    summary="A Cursor rules file/directory (.cursor/rules/*.mdc or legacy "
            ".cursorrules) exists.",
    why="Cursor is a widely used AI code editor; repositories already "
        "configured for it get no credit or visibility in this report "
        "without this rule.",
    fix="Add .cursor/rules/*.mdc (or a legacy .cursorrules file) with "
        "project-specific instructions for Cursor.",
    effort="additive",
)
def check_cursor_rules_present(index: ArtifactIndex):
    tree = index.tree
    if tree is None:
        return None
    if tree.resolves(".cursor/rules") or tree.resolves(".cursorrules"):
        return 1.0, []
    return 0.0, [Diagnostic(
        rule_id="tooling.cursor-rules.present", severity=Severity.INFO,
        message="No .cursor/rules/ directory or .cursorrules file found.",
    )]
```

Notes that generalize to every "detect tool X's config" issue:

- **`applicability=PRESENCE`, `severity=INFO`, `source=ADVISORY`.** This is a
  "did you configure this optional tool" signal, not a defect — it must never
  be `ERROR` (the registry enforces this for advisory rules; see
  `CONTRIBUTING.md`).
- **`doc_url` must point at the tool's own documentation** for the file path
  you're matching — copy the exact path/filename from there, don't guess.
- **Return `None` when there's no tree to check**, not `0.0` — a rule that
  can't evaluate must stay out of both the satisfied and failed buckets
  (`plan.md` §6.3).
- **Ask `index.tree.resolves(...)`, never `Path.exists()` or similar.** The
  scanned snapshot, not the live filesystem, is the source of truth (D3/D4;
  see `CONTRIBUTING.md` § "never accuse a file you did not read").

## 2. Add tests: pass, fail, and (if applicable) not-applicable

Follow the existing pattern in `tests/test_rules_tooling.py` — find
`test_devcontainer_satisfied_by_fixture` / `test_devcontainer_violated` for
the closest analogue and mirror its shape:

```python
# tests/test_rules_tooling.py

def test_cursor_rules_present_satisfied(tmp_path):
    _write(tmp_path, ".cursor/rules/style.mdc", "# style\n")
    sat, diags = rules.check_cursor_rules_present(_index(tmp_path))
    assert sat == 1.0
    assert diags == []


def test_cursor_rules_present_satisfied_legacy(tmp_path):
    _write(tmp_path, ".cursorrules", "Use type hints.\n")
    sat, diags = rules.check_cursor_rules_present(_index(tmp_path))
    assert sat == 1.0


def test_cursor_rules_present_violated(tmp_path):
    _write(tmp_path, "README.md", "# hello\n")
    sat, diags = rules.check_cursor_rules_present(_index(tmp_path))
    assert sat == 0.0
    assert diags[0].severity == Severity.INFO
```

A presence-only rule like this one is never `None` (it always has a tree to
check against a repo that was scanned at all), so there's no
not-applicable case to test here. If your rule *can* be N/A — e.g. it only
makes sense when some other artifact is present — add that test too.

Run just this module while iterating:

```bash
pytest tests/test_rules_tooling.py -v
```

## 3. Regenerate the rule catalog

```bash
airx rules --format md > docs/RULES.md
```

CI diffs this file against what's committed, so a PR that adds a rule without
regenerating it will fail CI.

## 4. Run the full suite and the determinism check

```bash
pytest -v
```

This includes `tests/test_determinism.py` (byte-identical output across 10
runs) and `tests/test_partial_snapshot.py` (no finding may reference a path
the snapshot never read) — both apply to every rule, including this one.

## 5. Open the PR

Reference the issue it closes, and include the `docs/RULES.md` diff — a
reviewer should be able to see the new row in the catalog table without
running the tool themselves.
