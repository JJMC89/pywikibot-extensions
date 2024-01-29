"""Test the page module."""

from __future__ import annotations

from typing import Iterable

import pytest
import pywikibot
from pytest_mock import MockerFixture

from pywikibot_extensions.page import FilePage, Page, get_redirects


SITE = pywikibot.Site("test", "wikipedia")


@pytest.mark.parametrize(
    "pages, redirects, expected",
    [
        (
            frozenset(
                [
                    pywikibot.Page(SITE, "Template:Foo"),
                    Page(SITE, "Tempalte:Example"),
                ]
            ),
            [],
            frozenset(
                [
                    pywikibot.Page(SITE, "Template:Foo"),
                    Page(SITE, "Tempalte:Example"),
                ]
            ),
        ),
        (
            frozenset(
                [
                    pywikibot.Page(SITE, "Template:Baz"),
                    Page(SITE, "Tempalte:Example"),
                ]
            ),
            [pywikibot.Page(SITE, "Template:Bar")],
            frozenset(
                [
                    pywikibot.Page(SITE, "Template:Baz"),
                    Page(SITE, "Tempalte:Example"),
                    pywikibot.Page(SITE, "Template:Bar"),
                ]
            ),
        ),
    ],
)
def test_get_redirects(
    mocker: MockerFixture,
    pages: frozenset[pywikibot.Page],
    redirects: Iterable[pywikibot.Page],
    expected: frozenset[pywikibot.Page],
) -> None:
    """Test get_redirects."""
    mocker.patch(
        "pywikibot_extensions.page.pywikibot.Page.redirects",
        return_value=redirects,
    )
    mocker.patch(
        "pywikibot_extensions.page.pywikibot.Page.isRedirectPage",
        return_value=False,
    )

    mocker.patch(
        "pywikibot_extensions.page.pywikibot.Page.exists", return_value=True
    )
    get_redirects.cache_clear()
    assert get_redirects(pages) == expected

    mocker.patch(
        "pywikibot_extensions.page.pywikibot.Page.exists", return_value=False
    )
    get_redirects.cache_clear()
    assert get_redirects(pages) == frozenset()


def test_get_redirects_for_redirect(mocker: MockerFixture) -> None:
    """Test get_redirects for a redirect."""
    test_page = pywikibot.Page(SITE, "Testing")
    test_target = pywikibot.Page(SITE, "Test")
    test_page._isredir = True
    test_page._redirtarget = test_target
    test_target._isredir = False
    expected = frozenset([test_target, test_page])
    mocker.patch(
        "pywikibot_extensions.page.pywikibot.Page.redirects",
        return_value=[test_page],
    )
    mocker.patch(
        "pywikibot_extensions.page.pywikibot.Page.exists", return_value=True
    )
    assert get_redirects(frozenset([test_page])) == expected


@pytest.mark.parametrize(
    "wikilink, namespace, expected",
    [
        ("[[Foo]]", 0, Page(SITE, "Foo")),
        ("[[Baz_]]", 1, Page(SITE, "Talk:Baz")),
        ("Bar_", 2, Page(SITE, "User:Bar")),
        ("[[Foo \u200e]]", 0, Page(SITE, "Foo")),
    ],
)
def test_page_from_wikilink(
    wikilink: object, namespace: int, expected: Page
) -> None:
    """Test Page.from_wikilink."""
    assert Page.from_wikilink(wikilink, SITE, namespace) == expected


def test_page_from_wikilink_error() -> None:
    """Test Page.from_wikilnk raises ValueError."""
    with pytest.raises(ValueError, match=r"Cannot create a FilePage from .+:"):
        FilePage.from_wikilink("[[User:Foo]]", SITE)


@pytest.mark.parametrize(
    "wikilink, expected",
    [
        ("[[File:Foo.svg|thumb|Example]]", FilePage(SITE, "File:Foo.svg")),
        ("Baz_.jpg", FilePage(SITE, "File:Baz_.jpg")),
        ("Bar_.png_", FilePage(SITE, "File:Bar_.png")),
    ],
)
def test_filepage_from_wikilink(wikilink: object, expected: FilePage) -> None:
    """Test FilePage.from_wikilink."""
    assert FilePage.from_wikilink(wikilink, SITE) == expected


@pytest.mark.parametrize(
    "templates, redirects, has_templates, expected",
    [
        (
            [Page(SITE, "Template:Example")],
            frozenset(),
            [Page(SITE, "Template:Example")],
            True,
        ),
        (
            [Page(SITE, "Template:Foo")],
            frozenset(
                [Page(SITE, "Template:Foo"), Page(SITE, "Template:Bar")]
            ),
            [Page(SITE, "Template:Bar")],
            True,
        ),
        (
            [Page(SITE, "Template:Example")],
            frozenset(),
            [Page(SITE, "Template:Example2")],
            False,
        ),
        (
            "Template:Example",
            frozenset([Page(SITE, "Template:Example")]),
            [Page(SITE, "Template:Example")],
            True,
        ),
    ],
)
def test_page_has_template(
    mocker: MockerFixture,
    templates: str | Iterable[pywikibot.Page | str],
    redirects: frozenset[pywikibot.Page],
    has_templates: Iterable[pywikibot.Page],
    expected: bool,
) -> None:
    """Test Page.has_template."""
    if not redirects:
        redirects = frozenset(templates)
    test_page = Page(SITE, "Project:Sandbox")
    mocker.patch(
        "pywikibot_extensions.page.get_redirects",
        return_value=redirects,
    )
    mocker.patch(
        "pywikibot_extensions.page.Page.templates",
        return_value=has_templates,
    )
    assert test_page.has_template(templates) is expected


@pytest.mark.parametrize(
    "namespace, disambig, redirect, expected",
    [
        (0, False, False, True),
        (0, True, False, False),
        (0, False, True, False),
        (1, True, True, False),
        (1, False, False, False),
        (2, True, False, False),
        (3, False, True, False),
    ],
)
def test_page_is_article(
    mocker: MockerFixture,
    namespace: int,
    disambig: bool,
    redirect: bool,
    expected: bool,
) -> None:
    """Test Page.is_article."""
    mocker.patch(
        "pywikibot_extensions.page.Page.isDisambig",
        return_value=disambig,
    )
    mocker.patch(
        "pywikibot_extensions.page.Page.isRedirectPage",
        return_value=redirect,
    )
    test_page = Page(SITE, "Example", namespace)
    assert test_page.is_article is expected


def test_page_is_article_catches_exception(mocker: MockerFixture) -> None:
    """Test Page.is_article when it catches an exception."""
    test_page = Page(SITE, "ticket:99998877665544321")
    mocker.patch(
        "pywikibot_extensions.page.Page.isDisambig",
        side_effect=pywikibot.exceptions.SiteDefinitionError(
            "Invalid AutoFamily('ticket.wikimedia.org')"
        ),
    )
    mocker.patch(
        "pywikibot_extensions.page.Page.isRedirectPage",
        return_value=False,
    )
    mocker.patch(
        "pywikibot_extensions.page.Page.namespace",
        return_value=0,
    )
    assert test_page.is_article is False


@pytest.mark.parametrize(
    "text, old_text, exists, force, new_text",
    [
        (
            "Test",
            "",
            True,
            False,
            "Test",
        ),
        (
            r"\Poof",
            "<!--bot start-->Old<!--bot end-->",
            True,
            False,
            "<!--bot start-->\n\\Poof<!--bot end-->",
        ),
        (
            "\n* One\n* Two\n* Three",
            "<!--bot start -->\n* One\n* Two\n<!--bot END-->",
            True,
            False,
            "<!--bot start -->\n* One\n* Two\n* Three<!--bot END-->",
        ),
        (
            "Test",
            "",
            False,
            False,
            "",
        ),
        (
            "Test",
            "",
            False,
            True,
            "Test",
        ),
    ],
)
def test_page_save_bot_start_end(
    mocker: MockerFixture,
    text: str,
    old_text: str,
    exists: bool,
    force: bool,
    new_text: str,
) -> None:
    """Test Page.save_bot_start_end."""
    mocker.patch(
        "pywikibot_extensions.page.Page.botMayEdit", return_value=True
    )
    mocker.patch("pywikibot_extensions.page.Page.exists", return_value=exists)
    mocker.patch("pywikibot_extensions.page.Page.save", return_value=True)
    test_page = Page(SITE, "Project:Sandbox")
    test_page.text = old_text
    test_page.save_bot_start_end(text, force=force)
    assert test_page.text == new_text


class MockFileInfo:
    """Partial mock of pywikibot.page.FileInfo."""

    def __init__(self, height: float | None, width: float | None) -> None:
        """Initialize."""
        # Conditional so that AttributeError is raised for None
        if height is not None:
            self.height = height
        if width is not None:
            self.width = width


@pytest.mark.parametrize(
    "height, width, expected",
    [
        (0, 0, None),
        (None, 10, None),
        (10, None, None),
        (None, None, None),
        (300, 300, 300 * 300 / 1e6),
        (2e3, 4e5, 2e3 * 4e5 / 1e6),
    ],
)
def test_filepage_megapixels(
    mocker: MockerFixture,
    height: float | None,
    width: float | None,
    expected: float | None,
) -> None:
    """Test FilePage.megapixels."""
    mocker.patch(
        "pywikibot_extensions.page.FilePage.latest_file_info",
        MockFileInfo(height, width),
    )
    test_page = FilePage(SITE, "Sandbox.png")
    assert test_page.megapixels == expected


@pytest.mark.parametrize(
    "using_pages, total, expected",
    [
        (tuple(), None, []),
        ([pywikibot.Page(SITE, "1")], None, [Page(SITE, "1")]),
        (
            [pywikibot.FilePage(SITE, "2.png")],
            None,
            [Page(SITE, "File:2.png")],
        ),
        ([pywikibot.FilePage(SITE, "2.png")], 1, [Page(SITE, "File:2.png")]),
        (
            [
                pywikibot.Page(SITE, "2"),
                pywikibot.Page(SITE, "3"),
            ],
            1,
            [Page(SITE, "2")],
        ),
    ],
)
def test_filepage_using_pages(
    mocker: MockerFixture,
    using_pages: Iterable[pywikibot.Page],
    total: int | None,
    expected: list[Page],
) -> None:
    """Test FilePage.using_pages."""
    for page in using_pages:
        if isinstance(page, pywikibot.FilePage):
            page._isredir = True
            page._redirtarget = pywikibot.FilePage(SITE, "Foo.png")
    mocker.patch(
        "pywikibot_extensions.page.pywikibot.FilePage.using_pages",
        return_value=using_pages,
    )
    test_page = FilePage(SITE, "Sandbox.png")
    assert list(test_page.using_pages(total=total)) == expected


def test_file_page_using_pages_self(mocker: MockerFixture) -> None:
    """Test FilePage.using_pages with redirect to self."""
    test_page = FilePage(SITE, "Sandbox.png")
    test_redirect = FilePage(SITE, "Sandbox2.png")
    test_redirect._isredir = True
    test_redirect._redirtarget = test_page
    other_using_pages = [Page(SITE, "1"), Page(SITE, "2")]
    mocker.patch(
        "pywikibot_extensions.page.pywikibot.FilePage.using_pages",
        return_value=other_using_pages + [test_redirect],
    )
    assert list(test_page.using_pages()) == other_using_pages
