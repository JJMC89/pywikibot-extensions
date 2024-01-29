"""Test the textlib module."""

from __future__ import annotations

from typing import Iterable

import pytest
import pywikibot

from pywikibot_extensions import textlib


@pytest.mark.parametrize(
    "items, prefix, expected",
    [
        (
            [],
            "",
            "",
        ),
        (
            ["foo"],
            "\n* ",
            "foo",
        ),
        (
            ["foo", "baz", "bar"],
            "\n* ",
            "\n* foo\n* baz\n* bar",
        ),
        (
            [
                pywikibot.Page(pywikibot.Site(), "foo"),
                None,
                pywikibot.FilePage(pywikibot.Site(), "Bar.png"),
            ],
            "\n* ",
            "\n* [[Foo]]\n* None\n* [[:File:Bar.png]]",
        ),
    ],
)
def test_iterable_to_wikitext(
    items: Iterable[object], prefix: str, expected: str
) -> None:
    """Test iterable_to_wikitext."""
    assert textlib.iterable_to_wikitext(items, prefix=prefix) == expected
