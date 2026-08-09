"""Shared classification of frontmatter fields outside a known schema.

Four rules ask the same question of four schemas — `skills.frontmatter.
unknown-fields`, `agents.unknown-fields`, `agents.commands.frontmatter.valid`,
`prompts.frontmatter.valid` — and each of them used to answer it the same
blunt way: any key not in the allowlist is a defect, one finding per key.

That answer does not match what those rules say they are for. Every one of
them justifies itself with the same sentence: unknown fields are *silently
ignored*, which hides *typos of real fields*. The harm named is the typo. A
key that is nobody's misspelling of anything — one a third-party tool reads
under its own prefix, or one a repository adds to route work through its own
dispatcher — is ignored by the platform exactly as its author intended, and
no cited page says an unrecognized key is an error. Reporting it as a WARNING
accuses a repository of a mistake it did not make, and doing so once per key
per file buries the findings that are real: a repository that adopts a handful
of such keys across its agents and skills can see them outnumber every other
finding in the report, without one of them being a typo.

So this module splits the question in two. A key close enough to a schema
field to be a misspelling of it is a *typo* — reported, scored, and told which
field it probably meant. Anything else is an *extension* — reported once per
file, at INFO, as a statement of what the platform will do with it.

This is the same correction already made to `safety.settings.valid`, whose
docstring records the reasoning: a snapshot of a schema that grows every
release cannot be the basis for accusing a repository of an error.
"""
from __future__ import annotations

import difflib
from dataclasses import dataclass

#: Similarity above which an unknown key is treated as a misspelling of a
#: schema field. Calibrated so that real slips (`descriptoin`, `mdoel`,
#: `toosl`, `tool`) match and deliberate extension keys (a `<tool>-<setting>`
#: pair, or a bare word naming a repository's own concept) do not. `difflib`
#: is deterministic and stdlib, which keeps this inside the no-network,
#: no-randomness contract.
_TYPO_CUTOFF = 0.8

#: Prefixes that declare a key as a deliberate extension rather than a schema
#: field (RFC 6648's convention, also OpenAPI's `x-`). Never treated as typos.
_EXTENSION_PREFIXES: tuple[str, ...] = ("x-", "x_")


@dataclass(frozen=True)
class UnknownFields:
    """The split verdict on one document's frontmatter.

    `typos` are `(field, suggestion)` pairs, sorted by field. `extensions` are
    the remaining unknown fields, sorted. Both are empty for a document whose
    frontmatter is entirely within the schema.
    """

    typos: tuple[tuple[str, str], ...] = ()
    extensions: tuple[str, ...] = ()

    def __bool__(self) -> bool:
        return bool(self.typos or self.extensions)


def _normalized(field: str) -> str:
    """Case- and separator-insensitive form, so `allowedTools`, `allowed_tools`
    and `Allowed-Tools` all collapse onto `allowedtools`."""
    return field.lower().replace("-", "").replace("_", "")


def classify_unknown_fields(fields, known: frozenset[str]) -> UnknownFields:
    """Split `fields` into likely misspellings of `known` and extension keys.

    Deterministic for a given input: the unknown keys are sorted before
    matching, and the schema is sorted before it is handed to `difflib`, so
    neither dict order nor set order can reach the output.
    """
    unknown = sorted(str(f) for f in fields if str(f) not in known)
    if not unknown:
        return UnknownFields()
    schema = sorted(known)
    by_normalized = {_normalized(k): k for k in schema}

    typos: list[tuple[str, str]] = []
    extensions: list[str] = []
    for field in unknown:
        if field.lower().startswith(_EXTENSION_PREFIXES):
            extensions.append(field)
            continue
        # A case/separator variant is a certain miss, not a near one: the author
        # meant that field and the loader will not see it.
        exact = by_normalized.get(_normalized(field))
        if exact is not None:
            typos.append((field, exact))
            continue
        close = difflib.get_close_matches(field, schema, n=1, cutoff=_TYPO_CUTOFF)
        if close:
            typos.append((field, close[0]))
        else:
            extensions.append(field)
    return UnknownFields(typos=tuple(typos), extensions=tuple(extensions))


def extensions_message(fields: tuple[str, ...], schema_name: str) -> str:
    """One sentence covering every extension key in a file, for the single
    aggregated INFO diagnostic that replaces the old per-key WARNINGs."""
    listed = ", ".join(f"'{f}'" for f in fields)
    plural = "fields" if len(fields) > 1 else "field"
    return (
        f"Frontmatter {plural} outside the known {schema_name} schema: {listed}. "
        f"The platform ignores these; they are only a problem if one is a misspelling."
    )


def typo_message(field: str, suggestion: str) -> str:
    return (
        f"Frontmatter field '{field}' is not in the known schema and looks like a "
        f"misspelling of '{suggestion}', which the platform would silently ignore."
    )
