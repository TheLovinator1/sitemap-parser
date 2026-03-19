from __future__ import annotations

import logging
import re
import typing
from datetime import datetime
from json import dumps
from typing import Any
from typing import Literal

import niquests
import xmltodict
from dateutil import parser

if typing.TYPE_CHECKING:
    from collections.abc import Generator
    from collections.abc import Iterator

    from niquests import Response

__all__: list[str] = [
    "JSONExporter",
    "SiteMapParser",
    "Sitemap",
    "SitemapIndex",
    "Url",
    "UrlSet",
]

logger: logging.Logger = logging.getLogger("sitemap_parser")

type Freqs = Literal[
    "always",
    "hourly",
    "daily",
    "weekly",
    "monthly",
    "yearly",
    "never",
]
type ValidFreqs = tuple[
    Literal["always"],
    Literal["hourly"],
    Literal["daily"],
    Literal["weekly"],
    Literal["monthly"],
    Literal["yearly"],
    Literal["never"],
]
type Fields = tuple[
    Literal["loc"],
    Literal["lastmod"],
    Literal["changefreq"],
    Literal["priority"],
]
type UrlFields = tuple[
    Literal["loc"],
    Literal["lastmod"],
    Literal["changefreq"],
    Literal["priority"],
]
type SitemapFields = tuple[
    Literal["loc"],
    Literal["lastmod"],
]


# MARK: BaseData
class BaseData:
    """Base class for sitemap data.

    Provides common properties and methods for sitemap and sitemap index entries,
    such as location (`loc`) and last modified time (`lastmod`).
    """

    def __init__(self) -> None:
        self._lastmod: datetime | None = None
        self._loc: str | None = None

    @property
    def lastmod(self) -> datetime | None:
        """Get the last modified datetime of the resource.

        Returns:
            datetime | None: The datetime when the resource was last modified, or None if not set.
        """
        return self._lastmod

    @lastmod.setter
    def lastmod(self, value: str | None) -> None:
        """Set the last modified datetime of the resource.

        Parses an ISO-8601 datetime string into a datetime object.

        Args:
            value (str | None): An ISO-8601 formatted datetime string, or None.
        """
        self._lastmod = parser.isoparse(value) if value is not None else None

    @property
    def loc(self) -> str | None:
        """Get the location URL of the resource.

        Returns:
            str | None: The URL of the resource.
        """
        return self._loc

    @loc.setter
    def loc(self, value: str | None) -> None:
        """Set the location URL of the resource.

        Validates that the provided value is a valid URL.

        Args:
            value (str | None): The URL to set.

        Raises:
            TypeError: If the value is not a string.
            ValueError: If the value is not a valid URL.
        """
        if not isinstance(value, str):
            msg = "URL must be a string"
            raise TypeError(msg)

        if not re.match(r"http[s]?://", value):
            msg: str = f"{value} is not a valid URL"
            raise ValueError(msg)

        self._loc = value


def download_uri_data(
    uri: str,
    *,
    raise_on_http_error: bool = True,
    **kwargs: Any,  # noqa: ANN401
) -> bytes:
    """Download the data from the uri.

    Args:
        uri(str): The uri to download. Expected format: HTTP/HTTPS URL.
        **kwargs: Additional keyword arguments passed to niquests.get().
        raise_on_http_error (bool): Whether to raise an exception on HTTP errors.

    Returns:
        bytes: The data from the uri

    Raises:
        ValueError: If no content was found at the uri.
    """
    logger.info("Downloading from %s", uri)
    r: Response = niquests.get(uri, **kwargs)

    if raise_on_http_error:
        r.raise_for_status()

    logger.debug("Downloaded data from %s", uri)

    content: bytes | None = r.content
    if not content:
        logger.warning("No content found at %s", uri)
        msg: str = f"No content found at {uri}"
        raise ValueError(msg)

    return content


# MARK: Sitemap
class Sitemap(BaseData):
    """Representation of the <sitemap> element."""

    fields: tuple[Literal["loc"], Literal["lastmod"]] = "loc", "lastmod"

    def __init__(self, loc: str, lastmod: str | None = None) -> None:
        """Representation of the <sitemap> element.

        Args:
            loc: String, URL of the page.
            lastmod: str | None, The date of last modification of the file.
        """
        self.loc = loc
        self.lastmod = lastmod

    def __str__(self) -> str:
        """String representation of the Sitemap instance.

        Returns:
            The URL of the page.

        Raises:
            ValueError: If loc is None.
        """
        if self.loc is None:
            msg = "loc cannot be None"
            raise ValueError(msg)

        return self.loc

    def __repr__(self) -> str:
        """String representation of the Sitemap instance.

        Returns:
            The URL of the page.
        """
        return f"<Sitemap {self.loc}>"


# MARK: Url
class Url(BaseData):
    """Representation of the <url> element.

    Args:
        BaseData: Base class for all data classes

    Raises:
        ValueError: If `changefreq` is not an allowed value.
        ValueError: If `priority` is not between 0.0 and 1.0.
    """

    fields: Fields = ("loc", "lastmod", "changefreq", "priority")
    valid_freqs: ValidFreqs = (
        "always",
        "hourly",
        "daily",
        "weekly",
        "monthly",
        "yearly",
        "never",
    )

    def __init__(
        self: Url,
        loc: str | None,
        lastmod: str | None = None,
        changefreq: str | None = None,
        priority: str | float | None = None,
    ) -> None:
        """Creates a Url instance.

        Args:
            loc: Location.
            lastmod: Last modified.
            changefreq: Change frequency.
            priority: Priority.
        """
        self.loc = loc
        self.lastmod = lastmod
        self.changefreq = changefreq
        self.priority = float(priority) if priority is not None else None

    @property
    def changefreq(self: Url) -> Freqs | None:
        """Get changefreq."""
        return self._changefreq

    @changefreq.setter
    def changefreq(self: Url, frequency: str | None) -> None:
        """Set changefreq.

        Args:
            self: The Url instance
            frequency: Change frequency.

        Raises:
            ValueError: Value is not an allowed value
        """
        if frequency is not None and frequency not in Url.valid_freqs:
            msg: str = f"'{frequency}' is not an allowed value: {Url.valid_freqs}"
            raise ValueError(msg)
        self._changefreq: Freqs | None = frequency

    @property
    def priority(self: Url) -> float | None:
        """Get priority.

        Returns:
            Priority
        """
        return self._priority

    @priority.setter
    def priority(self: Url, priority: float | None) -> None:
        if priority is not None:
            min_value = 0.0
            max_value = 1.0
            if priority < min_value or priority > max_value:
                msg: str = f"'{priority}' is not between 0.0 and 1.0"
                raise ValueError(msg)

        self._priority: float | None = priority

    def __str__(self: Url) -> str:
        """Return a string representation of the Url instance.

        Returns:
            String representation of the Url instance
        """
        return self.loc or ""

    def __repr__(self: Url) -> str:
        """Return a string representation of the Url instance.

        Returns:
            String representation of the Url instance
        """
        return f"Url(loc={self.loc}, lastmod={self.lastmod}, changefreq={self.changefreq}, priority={self.priority})"


# MARK: UrlSet
class UrlSet:
    r"""Represents a <urlset\> element.

    It contains multiple <url> entries, each represented by a Url instance.

    Example usage:
        ```python
        # Example of creating a UrlSet instance from a dict representing a <urlset> element.
        # This is how the data would look after being parsed by xmltodict.
        urlset_data = {
            "url": [
                {
                    "loc": "https://example.com/",
                    "lastmod": "2024-01-01T00:00:00Z",
                    "changefreq": "daily",
                    "priority": "0.8",
                },
                {
                    "loc": "https://example.com/about",
                    "lastmod": "2024-01-02T00:00:00Z",
                    "changefreq": "weekly",
                    "priority": "0.5",
                },
            ]
        }
        # Create a UrlSet instance and iterate over the Url entries.
        url_set = UrlSet(urlset_data)
        for url in url_set:
            print(url)
        ```
    """

    allowed_fields: typing.ClassVar[tuple[str, ...]] = (
        "loc",
        "lastmod",
        "changefreq",
        "priority",
    )

    def __init__(self, urlset_data: dict[str, Any]) -> None:
        r"""Initialize the UrlSet instance with the parsed <urlset\> data."""
        self.urlset_data: dict[str, Any] = urlset_data

    @staticmethod
    def url_from_dict(url_dict: dict[str, Any]) -> Url:
        """Creates a Url instance from a dict representing a <url> element.

        Args:
            url_dict: A dict as returned by xmltodict for a <url> element.

        Returns:
            Url: A Url instance populated from the provided dict.
        """
        logger.debug("url_from_dict %s", url_dict)
        url_data: dict[str, str | None] = {}
        for fld in UrlSet.allowed_fields:
            value = url_dict.get(fld)
            if value is not None:
                url_data[fld] = value

        logger.debug("url_data %s", url_data)
        return Url(**url_data)

    @staticmethod
    def urls_from_url_set_data(
        url_set_data: dict[str, Any],
    ) -> Generator[Url, typing.Any]:
        r"""Generate Url instances from xmltodict output for a <urlset\>.

        Args:
            url_set_data: Parsed xmltodict output for the <urlset\> element.

        Yields:
            Url: A Url instance for each <url\> entry.
        """
        logger.debug("urls_from_url_set_data %s", url_set_data)

        url_items: list[dict[str, Any]] | dict[str, Any] = url_set_data.get("url", [])
        if isinstance(url_items, dict):
            url_items = [url_items]

        for url_dict in url_items:
            yield UrlSet.url_from_dict(url_dict)

    def __iter__(self) -> Iterator[Url]:
        """Generator for Url instances from a <urlset> element.

        Returns:
            Url instance
        """
        return UrlSet.urls_from_url_set_data(self.urlset_data)


# MARK: SitemapIndex
class SitemapIndex:
    """Represents a <sitemapindex> element."""

    def __init__(self, index_data: dict[str, Any]) -> None:
        """Initialize the SitemapIndex instance with the parsed <sitemapindex> data."""
        self.index_data: dict[str, Any] = index_data

    @staticmethod
    def sitemap_from_dict(sitemap_dict: dict[str, Any]) -> Sitemap:
        """Creates a Sitemap instance from a dict representing a <sitemap> element.

        Args:
            sitemap_dict: A dict as returned by xmltodict for a <sitemap> element.

        Returns:
            Sitemap: A Sitemap instance populated from the provided dict.
        """
        sitemap_data: dict[str, str] = {}
        for fld in ("loc", "lastmod"):
            value = sitemap_dict.get(fld)
            if value is not None:
                sitemap_data[fld] = value

        msg = "Returning sitemap object with data: {}"
        logger.debug(msg, sitemap_data)
        return Sitemap(**sitemap_data)

    @staticmethod
    def sitemaps_from_index_data(index_data: dict[str, Any]) -> Generator[Sitemap, Any]:
        """Generate Sitemap instances from xmltodict output for a <sitemapindex>.

        Args:
            index_data: Parsed xmltodict output for the <sitemapindex> element.

        Yields:
            Sitemap: A Sitemap instance for each <sitemap> entry.
        """
        logger.debug("Generating sitemaps from %s", index_data)

        sitemap_items: list[dict[str, Any]] | dict[str, Any] = index_data.get(
            "sitemap",
            [],
        )
        if isinstance(sitemap_items, dict):
            sitemap_items = [sitemap_items]

        for sitemap_dict in sitemap_items:
            yield SitemapIndex.sitemap_from_dict(sitemap_dict)

    def __iter__(self) -> Iterator[Sitemap]:
        """Generator for Sitemap instances from a <sitemapindex> element.

        Args:
            self: The SitemapIndex instance

        Returns:
            Sitemap instance
        """
        return SitemapIndex.sitemaps_from_index_data(self.index_data)

    def __str__(self) -> str:
        return f"<SitemapIndex: {self.index_data}>"


# MARK: SiteMapParser
class SiteMapParser:
    """Parses a sitemap or sitemap index and returns the appropriate object."""

    def __init__(
        self,
        source: str,
        *,
        is_data_string: bool = False,
    ) -> None:
        """Initialize the SiteMapParser instance with the URI.

        The source can be a URL or a raw XML string. The parser will determine
        whether to download the data or use the provided string.

        Args:
            source: The URL of the sitemap or raw XML string.
            is_data_string: Whether the source is a raw XML string or not.
        """
        self.source: str = source
        self.is_sitemap_index: bool = False
        self._sitemaps: SitemapIndex | None = None
        self._url_set: UrlSet | None = None
        self._parsed_dict: dict[str, Any] | None = None
        self._is_data_string: bool = is_data_string
        self._xml_bytes: bytes | None = None
        self._initialize()

    def _initialize(self) -> None:
        """Initialization processing."""
        # Determine if we're using raw XML data or downloading from a URL
        if self._is_data_string:
            data: bytes = self.source.encode("utf-8")
        else:
            data: bytes = download_uri_data(uri=self.source)

        self._xml_bytes = data

        # Use xmltodict to parse sitemap content into a dictionary.
        # This avoids relying on ElementTree/XPath for extraction.
        parsed: dict[str, Any] = xmltodict.parse(data, force_list=("url", "sitemap"))
        self._parsed_dict = parsed

        root_key = next(iter(parsed))
        root_tag = root_key.split(":")[-1]
        self.is_sitemap_index = root_tag == "sitemapindex"

        if self.is_sitemap_index:
            self._sitemaps = SitemapIndex(index_data=parsed[root_key])
        else:
            self._url_set = UrlSet(urlset_data=parsed[root_key])

    def get_sitemaps(self) -> SitemapIndex:
        """Retrieve the sitemaps.

        Can check if 'has_sitemaps()' returns True to determine
        if this should be used without calling it

        Returns:
            SitemapIndex: The sitemaps as a SitemapIndex instance

        Raises:
            KeyError: If the root is not a <sitemapindex>
        """
        if not self.has_sitemaps():
            error_msg = "Method called when root is not a <sitemapindex>"
            logger.critical(error_msg)
            raise KeyError(error_msg)

        if self._sitemaps is None:
            msg = "Sitemaps are not available"
            raise KeyError(msg)

        return self._sitemaps

    def get_urls(self) -> UrlSet:
        """Retrieve the URLs from the sitemap.

        Returns:
            UrlSet: The URLs as a UrlSet instance.

        Raises:
            KeyError: If the root is not a <urlset>.
        """
        if not self.has_urls():
            error_msg = "Method called when root is not a <urlset>"
            logger.critical(error_msg)

            # Check if the root is a <sitemapindex>
            if self.is_sitemap_index:
                error_msg = "Method called when root is a <sitemapindex>. Use 'get_sitemaps()' instead"

            raise KeyError(error_msg)

        if self._url_set is None:
            msg = "URLs are not available"
            raise KeyError(msg)

        return self._url_set

    def has_sitemaps(self) -> bool:
        """Determine if the URL's data contained sitemaps.

        A sitemap can contain other sitemaps. For example: <https://www.webhallen.com/sitemap.xml>

        Returns:
            Boolean
        """
        return self.is_sitemap_index

    def has_urls(self) -> bool:
        """Determine if the URL's data contained urls.

        Returns:
            Boolean
        """
        return not self.is_sitemap_index

    def to_dict(
        self,
        *,
        process_namespaces: bool = False,
        **xmltodict_kwargs: object,
    ) -> dict[str, Any]:
        """Parse the underlying XML input into a Python dict.

        Args:
            process_namespaces (bool): Expand namespaces into the returned dict.
            **xmltodict_kwargs: Additional keyword arguments passed to :func:`xmltodict.parse`.

        Returns:
            dict[str, Any]: The parsed XML as a Python dictionary.

        Raises:
            RuntimeError: If the parser does not have XML data available.
        """
        xml_bytes: bytes | None = self._xml_bytes
        if xml_bytes is None:
            msg = "No XML data available to parse"
            raise RuntimeError(msg)

        # If we have already parsed the XML and the caller is using default
        # options, just return the cached parse.
        if (
            not process_namespaces
            and not xmltodict_kwargs
            and self._parsed_dict is not None
        ):
            return self._parsed_dict

        kwargs: dict[str, Any] = {"process_namespaces": process_namespaces}
        kwargs.update(xmltodict_kwargs)  # type: ignore[arg-type]

        return xmltodict.parse(xml_bytes, **kwargs)

    def __str__(self) -> str:
        """String representation of the SiteMapParser instance.

        Returns:
            str
        """
        return str(self._sitemaps if self.has_sitemaps() else self._url_set)


# MARK: JSONExporter
class JSONExporter:
    """Export site map data to JSON format."""

    def __init__(self, data: SiteMapParser) -> None:
        """Initializes the JSONExporter instance with the site map data."""
        self.data: SiteMapParser = data

    @staticmethod
    def _collate(
        fields: SitemapFields | UrlFields,
        row_data: SitemapIndex | UrlSet,
    ) -> list[dict[str, Any]]:
        """Collate data from SitemapIndex or UrlSet into a list of dictionaries.

        Args:
            fields (SitemapFields | UrlFields): The fields to include in the output.
            row_data (SitemapIndex | UrlSet): An iterable containing Sitemap or Url objects.

        Returns:
            list: A list of dictionaries where each dictionary represents a Sitemap or Url object.
        """
        dump_data: list[dict[str, Any]] = []
        for sm in row_data:
            row: dict[str, Any] = {}
            for field_name in fields:
                field_value: Fields = getattr(sm, field_name)
                row[field_name] = (
                    field_value.isoformat()
                    if isinstance(field_value, datetime)
                    else field_value
                )
            dump_data.append(row)
        return dump_data

    def export_sitemaps(self) -> str:
        """Export site map data to JSON format.

        Returns:
            str: JSON data as a string
        """
        default_fields: SitemapFields = ("loc", "lastmod")
        sitemap_fields: SitemapFields = getattr(Sitemap, "fields", default_fields)

        return dumps(self._collate(sitemap_fields, self.data.get_sitemaps()))

    def export_urls(self) -> str:
        """Export site map data to JSON format.

        Returns:
            str: JSON data as a string
        """
        default_fields: UrlFields = ("loc", "lastmod", "changefreq", "priority")
        url_fields: UrlFields = getattr(Url, "fields", default_fields)

        return dumps(self._collate(url_fields, self.data.get_urls()))
