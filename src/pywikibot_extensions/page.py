"""
Objects representing various MediaWiki pages.

This module extends pywikibot.page.
"""
from __future__ import annotations

import re
import unicodedata
from contextlib import suppress
from functools import lru_cache
from typing import Any, Generator, Iterable, TypeVar, Union

import pywikibot
from pywikibot.site import Namespace
from pywikibot.textlib import removeDisabledParts


FilePageT = TypeVar("FilePageT", bound="FilePage")
NamespaceType = Union[int, str, Namespace]
PageSource = Union[
    pywikibot.page.Page, pywikibot.site.BaseSite, pywikibot.page.BaseLink
]
PageT = TypeVar("PageT", bound="Page")


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
            link_pages.update(page.redirects(namespaces=namespaces))
    return frozenset(link_pages)


class Page(pywikibot.Page):
    """Represents a MediaWiki page."""

    BOT_START_END = re.compile(
        r"^(.*?<!--\s*bot start\s*-->)(.*?)(<!--\s*bot end\s*-->.*)$",
        flags=re.I | re.S,
    )

    @classmethod
    def from_wikilink(
        cls: type[PageT],
        wikilink: object,
        site: pywikibot.site.BaseSite,
        default_namespace: int = 0,
    ) -> PageT:
        """
        Create a Page from a wikilink.

        :param wikilink: the wikilink text
        :param site: Site with the wikilink
        :param default_namespace: a namespace to use if the link does not
            contain one (defaults to 0)
        """
        text = removeDisabledParts(str(wikilink), site=site)
        # Remove unicode control characters
        text = "".join(c for c in text if unicodedata.category(c)[0] != "C")
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
        try:
            return (
                self.namespace() == 0
                and not self.isDisambig()
                and not self.isRedirectPage()
            )
        except pywikibot.exceptions.Error:
            return False

    def save_bot_start_end(
        self,
        text: str,
        *,
        minor: bool | None = False,
        botflag: bool | None = False,
        force: bool = False,
        **kwargs: Any,
    ) -> None:
        """
        Save text to the specified area of the page.

        The area is specified by <!--bot start--> and <!--bot end-->.

        :param text: text to save to the page
        :param minor: mark this edit as minor
        :param botflag: mark this edit as made by a bot
        :param force: ignore bot restrictions and create if nonexistent

        See :meth:`pywikibot.page.Page.save` for other arguments.
        """
        if not force and not self.exists():
            pywikibot.warning(f"{self.title()} does not exist. Skipping.")
            return
        text = text.strip()
        current_text = self.text  # type: ignore[has-type]
        match_ = self.BOT_START_END.match(current_text)
        if match_:
            # re.sub will raise if text contains a bad escape
            self.text = f"{match_.group(1)}\n{text}{match_.group(3)}"
        else:
            self.text = text
        self.save(minor=minor, botflag=botflag, force=force, **kwargs)


class FilePage(pywikibot.FilePage, Page):
    """Represents a file description page."""

    @classmethod
    def from_wikilink(
        cls: type[FilePageT],
        wikilink: object,
        site: pywikibot.site.BaseSite,
        default_namespace: int = 6,
    ) -> FilePageT:
        """
        Create a FilePage from a wikilink.

        :param wikilink: the wikilink text
        :param site: Site with the wikilink
        :param default_namespace: a namespace to use if the link does not
            contain one (defaults to 6)
        """
        return super().from_wikilink(wikilink, site, default_namespace)

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

    def using_pages(self, **kwargs: Any) -> Generator[Page, None, None]:
        """Yield pages on which the file is displayed."""
        count = 0
        total = kwargs.pop("total", None)
        for page in super().using_pages(**kwargs):
            if total and count >= total:
                return
            page = Page(page)
            # MediaWiki considers file redirects to be using the target flie,
            # but they are not actually using it.
            try:
                if (
                    page.namespace() != 6
                    or not page.isRedirectPage()
                    or page.getRedirectTarget() != self
                ):
                    count += 1
                    yield page
            except pywikibot.exceptions.Error:  # pragma: no cover
                count += 1
                yield page
