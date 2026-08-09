"""`.vscode/*.json` is JSON with comments; everything else is strict JSON.

The bug this guards against: `.vscode/mcp.json` in `microsoft/vscode-copilot-chat`
contains a `//` comment and a trailing comma, both of which VS Code documents as
valid in its own config files. The analyzer parsed it with `json.loads`, called
it a syntax error, and raised an ERROR that capped the repository's grade at C
— an accusation against a file written correctly by the team that owns the
format.

The other half matters just as much: Claude Code documents `.claude/settings.json`
as strict ("a file that fails validation is rejected as a whole and reported"),
so a comment there is a genuine defect and must keep failing.
"""
from __future__ import annotations

import json

import pytest

from airx.discovery import build_index
from airx.jsonc import strip_jsonc
from airx.rules.tooling import check_mcp_valid

# The file that exposed the bug, byte-for-byte from
# https://github.com/microsoft/vscode-copilot-chat/blob/main/.vscode/mcp.json
VSCODE_COPILOT_CHAT_MCP_JSON = """{
\t"servers": {
\t\t"vscode-playwright-mcp": {
\t\t\t"type": "stdio",
\t\t\t"command": "npm",
\t\t\t// See https://github.com/microsoft/vscode/blob/main/test/mcp/README.md for supported arguments
\t\t\t"args": [
\t\t\t\t"run",
\t\t\t\t"start-stdio",
\t\t\t\t"--",
\t\t\t\t"--extensionDevelopmentPath=${workspaceFolder}",
\t\t\t],
\t\t\t"cwd": "${workspaceFolder}/../vscode/test/mcp"
\t\t}
\t},
\t"inputs": []
}
"""


# --- the transform itself ---------------------------------------------------

@pytest.mark.parametrize(
    "text, expected",
    [
        ('{"a": 1} // trailing note', {"a": 1}),
        ('// leading note\n{"a": 1}', {"a": 1}),
        ('{/* block */ "a": 1}', {"a": 1}),
        ('{\n/* multi\n   line\n*/\n"a": 1}', {"a": 1}),
        ('{"a": 1,}', {"a": 1}),
        ('{"a": [1, 2,]}', {"a": [1, 2]}),
        ('{"a": [1, 2, /* note */ ]}', {"a": [1, 2]}),
        ('{"a": 1,\n}', {"a": 1}),
        ('{"a": {"b": 2,},}', {"a": {"b": 2}}),
    ],
)
def test_jsonc_syntax_is_accepted(text, expected):
    assert json.loads(strip_jsonc(text)) == expected


@pytest.mark.parametrize(
    "text, expected",
    [
        # A comment marker inside a string is data, not a comment.
        ('{"url": "https://example.com/x"}', {"url": "https://example.com/x"}),
        ('{"a": "// not a comment"}', {"a": "// not a comment"}),
        ('{"a": "/* not a comment */"}', {"a": "/* not a comment */"}),
        # ...including when the string ends in an escaped quote.
        (r'{"a": "he said \"hi\" // ok"}', {"a": 'he said "hi" // ok'}),
        # A comma inside a string is not a trailing comma.
        ('{"a": "x,]"}', {"a": "x,]"}),
        (r'{"a": "back\\slash", "b": 2}', {"a": "back\\slash", "b": 2}),
    ],
)
def test_string_contents_are_left_alone(text, expected):
    assert json.loads(strip_jsonc(text)) == expected


def test_strict_json_is_unchanged():
    text = '{\n  "a": 1,\n  "b": [2, 3]\n}\n'
    assert strip_jsonc(text) == text


def test_offsets_are_preserved_so_error_positions_stay_true():
    """Comments are blanked, not deleted, so a real syntax error still reports
    the line and column it occupies in the file the user will open."""
    text = '{\n  // note\n  "a" 1\n}'
    stripped = strip_jsonc(text)
    assert len(stripped) == len(text)
    assert stripped.count("\n") == text.count("\n")
    with pytest.raises(json.JSONDecodeError) as exc:
        json.loads(stripped)
    assert exc.value.lineno == 3


def test_unterminated_block_comment_runs_to_end_of_file():
    assert json.loads(strip_jsonc('{"a": 1}\n/* never closed')) == {"a": 1}


def test_broken_jsonc_is_still_broken():
    """Leniency about comments is not leniency about everything."""
    with pytest.raises(json.JSONDecodeError):
        json.loads(strip_jsonc('{"a": 1 "b": 2}  // still wrong'))


# --- wired into discovery ---------------------------------------------------

def _index(tmp_path, files):
    from airx.fs import scan

    for rel, body in files.items():
        p = tmp_path / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(body, encoding="utf-8")
    return build_index(scan(tmp_path))


def test_vscode_mcp_json_with_comments_parses(tmp_path):
    index = _index(tmp_path, {".vscode/mcp.json": VSCODE_COPILOT_CHAT_MCP_JSON})
    artifact = index.mcp[0]
    assert artifact.parse_error is None
    assert "vscode-playwright-mcp" in artifact.json_data["servers"]


def test_vscode_mcp_json_with_comments_produces_no_finding(tmp_path):
    """The end-to-end shape of the bug: an ERROR that capped the grade at C."""
    index = _index(tmp_path, {".vscode/mcp.json": VSCODE_COPILOT_CHAT_MCP_JSON})
    satisfaction, diagnostics = check_mcp_valid(index)
    assert satisfaction == 1.0
    assert diagnostics == []


def test_vscode_mcp_json_that_is_genuinely_broken_still_reports(tmp_path):
    index = _index(tmp_path, {".vscode/mcp.json": '{"servers": {'})
    _, diagnostics = check_mcp_valid(index)
    assert len(diagnostics) == 1
    assert "not valid JSON" in diagnostics[0][1].message


def test_claude_settings_stay_strict(tmp_path):
    """Claude Code documents settings.json as strict, so a comment there is a
    real defect and must keep being reported."""
    index = _index(tmp_path, {".claude/settings.json": '{\n  // note\n  "a": 1\n}'})
    artifact = index.claude_settings
    assert artifact.parse_error is not None


def test_project_root_mcp_json_stays_strict(tmp_path):
    """`.mcp.json` is Claude Code's format, and no comment support is documented
    for it — only `.vscode/` is treated as jsonc."""
    index = _index(tmp_path, {".mcp.json": '{\n  // note\n  "servers": {}\n}'})
    artifact = index.mcp[0]
    assert artifact.parse_error is not None


def test_github_hooks_stay_strict(tmp_path):
    index = _index(tmp_path, {".github/hooks/x.json": '{"a": 1,}'})
    artifact = index.hooks[0]
    assert artifact.parse_error is not None
