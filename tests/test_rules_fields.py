"""Tests for the shared unknown-frontmatter-field classifier.

The calibration is the point: the split has to put real slips on the typo side
and deliberate extension keys on the other, or it just relabels the false
positives it was written to remove.
"""
from airx import config
from airx.rules.fields import UnknownFields, classify_unknown_fields, extensions_message


def test_fields_in_the_schema_produce_nothing():
    verdict = classify_unknown_fields(
        {"name": "x", "description": "y", "tools": "Read"}, config.KNOWN_AGENT_FIELDS
    )
    assert verdict == UnknownFields()
    assert not verdict


def test_near_misses_are_reported_as_typos_with_the_field_they_meant():
    verdict = classify_unknown_fields(
        {"descriptoin": 1, "mdoel": 2, "toosl": 3}, config.KNOWN_AGENT_FIELDS
    )
    assert verdict.typos == (
        ("descriptoin", "description"), ("mdoel", "model"), ("toosl", "tools"),
    )
    assert verdict.extensions == ()


def test_case_and_separator_variants_are_typos():
    """The author meant the field; the loader will not see it."""
    verdict = classify_unknown_fields(
        {"Description": 1, "permission_mode": 2}, config.KNOWN_AGENT_FIELDS
    )
    assert verdict.typos == (("Description", "description"), ("permission_mode", "permissionMode"))


def test_deliberate_extension_keys_are_not_typos():
    """The fields a repository adds for its own dispatcher, and the ones a
    third-party tool reads under its own prefix. None of these misspells
    anything in the schema."""
    verdict = classify_unknown_fields(
        {
            "team": 1, "queue": 2, "stage": 3,
            "mytool-model": 4, "mytool-effort": 5, "mytool-sandbox": 6,
            "requires-approval": 7,
        },
        config.KNOWN_AGENT_FIELDS,
    )
    assert verdict.typos == ()
    assert verdict.extensions == (
        "mytool-effort", "mytool-model", "mytool-sandbox",
        "queue", "requires-approval", "stage", "team",
    )


def test_x_prefixed_keys_are_never_typos():
    """RFC 6648's convention: the prefix declares the key as an extension, so
    it is exempt even where the rest of it resembles a schema field."""
    verdict = classify_unknown_fields({"x-model": 1, "x_tools": 2}, config.KNOWN_AGENT_FIELDS)
    assert verdict.typos == ()
    assert verdict.extensions == ("x-model", "x_tools")


def test_non_string_keys_are_stringified_not_crashed_on():
    verdict = classify_unknown_fields({1: "oops"}, config.KNOWN_AGENT_FIELDS)
    assert verdict.extensions == ("1",)


def test_output_is_independent_of_input_order():
    fields = ["stage", "descriptoin", "team", "mdoel"]
    first = classify_unknown_fields(fields, config.KNOWN_AGENT_FIELDS)
    second = classify_unknown_fields(list(reversed(fields)), config.KNOWN_AGENT_FIELDS)
    assert first == second


def test_extensions_message_names_every_field_once():
    message = extensions_message(("mytool-model", "team"), "agent")
    assert "'mytool-model'" in message and "'team'" in message
    assert "agent schema" in message
