"""JSON with Comments (jsonc), for the VS Code configuration files that use it.

VS Code documents a distinct mode for its own config files:

    "This mode is used for the VS Code configuration files such as
    settings.json, tasks.json, or launch.json."

    "When in the JSON with Comments mode, you can use single line (//) as well
    as block comments (/* */) as used in JavaScript. The mode also accepts
    trailing commas, but they are discouraged and the editor will display a
    warning."

    -- https://code.visualstudio.com/docs/languages/json

`.vscode/mcp.json` is one of those files, and Microsoft's own
`microsoft/vscode-copilot-chat` ships one containing both a `//` comment and a
trailing comma. Parsing it with `json.loads` reports a syntax error in a file
that is valid for the tool that reads it, so the analyzer would be accusing a
correct repository of a defect.

This leniency is scoped to `.vscode/`, and deliberately not extended to the
other JSON artifacts, because the opposite is documented for them. Claude
Code's settings reference states of `.claude/settings.json`:

    "This file remains strict: a file that fails validation is rejected as a
    whole and reported."

    -- https://code.claude.com/docs/en/settings

A comment there really is a defect, and reporting it is the right answer. The
Claude Code MCP reference documents no comment support for `.mcp.json` either,
so that path stays strict as well.

Both transforms below preserve byte offsets: comments and dropped commas are
overwritten with spaces rather than deleted, and newlines inside block comments
are kept. A `json.JSONDecodeError` raised on the result therefore still reports
the line and column where the problem sits in the original file.
"""
from __future__ import annotations

__all__ = ["strip_jsonc"]

_LINE_BREAKS = "\n\r"
_CLOSERS = "}]"


def _blank_comments(text: str) -> str:
    """Overwrite `//` and `/* */` comments with spaces, ignoring both inside
    string literals."""
    out = list(text)
    i, n = 0, len(text)
    in_string = False

    while i < n:
        ch = text[i]

        if in_string:
            if ch == "\\":
                # Skip the escaped character so an escaped quote does not end
                # the string. A trailing backslash just runs off the end.
                i += 2
                continue
            if ch == '"':
                in_string = False
            i += 1
            continue

        if ch == '"':
            in_string = True
            i += 1
            continue

        if ch == "/" and i + 1 < n:
            following = text[i + 1]
            if following == "/":
                j = i
                while j < n and text[j] not in _LINE_BREAKS:
                    out[j] = " "
                    j += 1
                i = j
                continue
            if following == "*":
                end = text.find("*/", i + 2)
                # An unterminated block comment runs to end of file, which is
                # what an editor shows too.
                stop = n if end == -1 else end + 2
                for j in range(i, stop):
                    if text[j] not in _LINE_BREAKS:
                        out[j] = " "
                i = stop
                continue

        i += 1

    return "".join(out)


def _blank_trailing_commas(text: str) -> str:
    """Overwrite each comma that is followed only by whitespace and a closing
    brace or bracket."""
    out = list(text)
    i, n = 0, len(text)
    in_string = False

    while i < n:
        ch = text[i]

        if in_string:
            if ch == "\\":
                i += 2
                continue
            if ch == '"':
                in_string = False
            i += 1
            continue

        if ch == '"':
            in_string = True
            i += 1
            continue

        if ch == ",":
            j = i + 1
            while j < n and text[j].isspace():
                j += 1
            if j < n and text[j] in _CLOSERS:
                out[i] = " "

        i += 1

    return "".join(out)


def strip_jsonc(text: str) -> str:
    """Return `text` with jsonc-only syntax blanked out, ready for `json.loads`.

    Comments are removed before trailing commas are looked for, so a comma
    separated from its closing bracket by a comment is still recognised:

        [1, 2, /* note */ ]
    """
    return _blank_trailing_commas(_blank_comments(text))
