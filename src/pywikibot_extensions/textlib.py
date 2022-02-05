"""
Functions for manipulating wikitext.

This module extends pywikibot.textlib.
"""
from __future__ import annotations

from typing import Iterable

from pywikibot.page import BasePage


# The namespace names must be substituted into this regex,
# e.g., FILE_LINK_REGEX.format("|".join(site.namespaces.FILE)).
# Adds named groups to pywikibot.textlib.FILE_LINK_REGEX
# and uses str.format instead of %.
FILE_LINK_REGEX = r"""
    \[\[\s*
    (?P<namespace>{})
    \s*:
    (?=(?P<filename>
        [^]|]*
    ))(?P=filename)
    (
        \|
        (
            (
                (?=(?P<inner_link>
                    \[\[.*?\]\]
                ))(?P=inner_link)
            )?
            (?=(?P<other_chars>
                [^\[\]]*
            ))(?P=other_chars)
        |
            (?=(?P<not_wikilink>
                \[[^]]*\]
            ))(?P=not_wikilink)
        )*?
    )??
    \]\]
"""


def iterable_to_wikitext(
    items: Iterable[object], *, prefix: str = "\n* "
) -> str:
    """
    Convert iterable to wikitext.

    Pages are converted to links.
    All other objects use their string representation.

    :param items: Items to iterate
    :param prefix: Prefix for each item when there is more than one item
    """
    if not items:
        return ""
    if len(list(items)) == 1:
        prefix = ""
    text = ""
    for item in items:
        if isinstance(item, BasePage):
            item = item.title(as_link=True, textlink=True)
        text += f"{prefix}{item}"
    return text
