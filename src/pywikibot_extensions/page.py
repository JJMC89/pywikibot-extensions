"""
Objects representing various MediaWiki pages.

This module extends pywikibot.page.
"""
from __future__ import annotations

import re
from contextlib import suppress
from functools import lru_cache
from typing import Any, Generator, Iterable, TypeVar, Union

import pywikibot
from pywikibot.site import Namespace
from pywikibot.textlib import removeDisabledParts


FilePageType = TypeVar("FilePageType", bound="FilePage")
NamespaceType = Union[int, str, Namespace]
PageSource = Union[
    pywikibot.page.Page, pywikibot.site.BaseSite, pywikibot.page.BaseLink
]
PageType = TypeVar("PageType", bound="Page")


@lru_cache()
def get_redirects(
    pages: frozenset[pywikibot.Page],
    namespaces: NamespaceType | frozenset[NamespaceType] | None = None,
) -> frozenset[pywikibot.Page]:
    """
    Return possible titles as pages for a set of pages.

    :param pages: Set of pages to get titles for
    :param namespaces: Limit redirects to these namespaces
    """
    link_pages = set()
    for page in pages:
        with suppress(pywikibot.exceptions.CircularRedirectError):
            while page.isRedirectPage():
                page = page.getRedirectTarget()
        if not page.exists():
            continue
        link_pages.add(page)
        with suppress(pywikibot.exceptions.CircularRedirectError):
            redirects = page.backlinks(
                filter_redirects=True, namespaces=namespaces
            )
            link_pages.update(redirects)
    return frozenset(link_pages)


class Page(pywikibot.Page):
    """Represents a MediaWiki page."""

    BOT_START_END = re.compile(
        r"^(.*?<!--\s*bot start\s*-->).*?(<!--\s*bot end\s*-->.*)$",
        flags=re.I | re.S,
    )

    @classmethod
    def from_wikilink(
        cls: type[PageType],
        wikilink: object,
        site: pywikibot.site.BaseSite,
        default_namespace: int = 0,
    ) -> PageType:
        """
        Create a Page from a wikilink.

        :param wikilink: the wikilink text
        :param site: Site with the wikilink
        :param default_namespace: a namespace to use if the link does not
            contain one (defaults to 0)
        """
        text = removeDisabledParts(str(wikilink), site=site)
        text = text.strip().lstrip("[").rstrip("]")
        try:
            link = pywikibot.Link(text, site, default_namespace)
            link.parse()  # To catch any exceptions
            return cls(link)
        except Exception as e:
            raise ValueError(
                f"Cannot create a {cls.__name__} from {wikilink!r}: {e}"
            ) from None

    def has_template(
        self, templates: str | Iterable[pywikibot.Page | str]
    ) -> bool:
        """
        Return True if the page has one of the templates. False otherwise.

        :param templates: templates to check
        """
        if isinstance(templates, str):
            templates = [templates]
        all_template_pages = get_redirects(
            frozenset(
                tpl
                if isinstance(tpl, pywikibot.Page)
                else Page(self.site, tpl, ns=10)
                for tpl in templates
            )
        )
        return bool(all_template_pages & set(self.templates()))

    @property
    def is_article(self) -> bool:
        """Return True if the page is an article. False otherwise."""
        return (
            self.namespace() == 0
            and not self.isDisambig()
            and not self.isRedirectPage()
        )

    def save_bot_start_end(
        self,
        text: str,
        *,
        minor: bool | None = False,
        botflag: bool | None = False,
        **kwargs: Any,
    ) -> None:
        """
        Save text to the specified area of the page.

        The area is specified by <!--bot start--> and <!--bot end-->.

        :param text: text to save to the page
        :param minor: if True, mark this edit as minor
        :param botflag: if True, mark this edit as made by a bot

        See :meth:`pywikibot.page.Page.save` for other arguments.
        """
        if not self.exists():
            pywikibot.warning(f"{self.title()} does not exist. Skipping.")
            return
        text = text.strip()
        current_text = self.text  # type: ignore[has-type]
        if self.BOT_START_END.match(current_text):
            self.text = self.BOT_START_END.sub(fr"\1\n{text}\2", current_text)
        else:
            self.text = text
        self.save(minor=minor, botflag=botflag, **kwargs)


class FilePage(pywikibot.FilePage, Page):
    """Represents a file description page."""

    @classmethod
    def from_wikilink(
        cls: type[FilePageType],
        wikilink: object,
        site: pywikibot.site.BaseSite,
        default_namespace: int = 6,
    ) -> FilePageType:
        """
        Create a FilePage from a wikilink.

        :param wikilink: the wikilink text
        :param site: Site with the wikilink
        :param default_namespace: a namespace to use if the link does not
            contain one (defaults to 6)
        """
        return super().from_wikilink(wikilink, site, default_namespace)

    @property
    def is_used(self) -> bool:
        """Return True if the file is used, False otherwise."""
        return len(set(self.usingPages())) > 0

    @property
    def megapixels(self) -> float | None:
        """
        Return the file's megapixels.

        Returns None if the dimensions are 0 or unknown.
        """
        try:
            height = self.latest_file_info.height
            width = self.latest_file_info.width
        except AttributeError:
            return None
        else:
            return height * width / 1e6 or None

    def usingPages(  # noqa: N802
        self, total: int | None = None, content: bool = False
    ) -> Generator[Page, None, None]:
        """Yield pages on which the file is displayed."""
        for page in super().usingPages(total=total, content=content):
            page = Page(page)
            # MediaWiki considers file redirects to be using the target flie,
            # but they are not actually using it.
            try:
                if (
                    page.namespace() != 6
                    or not page.isRedirectPage()
                    or page.getRedirectTarget() != self
                ):
                    yield page
            except pywikibot.exceptions.Error:  # pragma: no cover
                yield page
