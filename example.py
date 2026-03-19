import json
import logging

from sitemap_parser import JSONExporter
from sitemap_parser import SiteMapParser

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger: logging.Logger = logging.getLogger(__name__)


def main() -> None:
    """Example usage of the SiteMapParser."""
    # Sitemap with URLs to other sitemaps
    parser = SiteMapParser(source="https://ttvdrops.lovinator.space/sitemap.xml")
    exporter = JSONExporter(data=parser)

    if parser.has_urls():
        json_data: str = exporter.export_urls()
        json_data = json.loads(json_data)
        logger.info("Exported URLs: %s", json_data)

    if parser.has_sitemaps():
        json_data: str = exporter.export_sitemaps()
        json_data = json.loads(json_data)
        logger.info("Exported sitemaps: %s", json_data)

    logger.info("----" * 10)

    # Sitemap with "real" URLs
    parser2 = SiteMapParser(
        source="https://ttvdrops.lovinator.space/sitemap-static.xml",
    )
    exporter2 = JSONExporter(data=parser2)
    if parser2.has_urls():
        json_data: str = exporter2.export_urls()
        json_data = json.loads(json_data)
        logger.info("Exported URLs: %s", json_data)

    if parser2.has_sitemaps():
        json_data: str = exporter2.export_sitemaps()
        json_data = json.loads(json_data)
        logger.info("Exported sitemaps: %s", json_data)


if __name__ == "__main__":
    main()
