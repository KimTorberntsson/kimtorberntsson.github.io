"""robots.txt and sitemap.xml.

Neither existed. These read the production build, not the served site, because
`jekyll serve` rewrites site.url to localhost and both files are full of
absolute URLs.
"""

import os
import re

import pytest


@pytest.fixture
def built(production_site):
    def read(path):
        full = os.path.join(production_site, path)
        assert os.path.exists(full), "%s was not built" % path
        return open(full, encoding="utf-8").read()

    return read


def test_robots_allows_crawling_and_points_at_the_sitemap(built):
    robots = built("robots.txt")
    assert "User-agent: *" in robots
    assert re.search(r"^Allow: /$", robots, re.M), robots
    assert "Sitemap: https://kimtorberntsson.com/sitemap.xml" in robots, robots


def test_the_sitemap_lists_every_post(built):
    sitemap = built("sitemap.xml")
    urls = re.findall(r"<loc>([^<]+)</loc>", sitemap)
    posts = [u for u in urls if re.search(r"/\d{4}/\d{2}/\d{2}/", u)]
    assert len(posts) >= 38, "only %d posts in the sitemap" % len(posts)


def test_the_sitemap_lists_the_sections(built):
    urls = re.findall(r"<loc>([^<]+)</loc>", built("sitemap.xml"))
    paths = {u.replace("https://kimtorberntsson.com", "") for u in urls}
    for section in ("/", "/archive/", "/gallery/", "/about/"):
        assert section in paths, "%s is not in the sitemap: %s" % (
            section, sorted(paths)[:8])


def test_every_sitemap_url_is_absolute_https(built):
    urls = re.findall(r"<loc>([^<]+)</loc>", built("sitemap.xml"))
    assert urls, "the sitemap is empty"
    bad = [u for u in urls if not u.startswith("https://kimtorberntsson.com/")]
    assert not bad, "not absolute https: %s" % bad[:5]


def test_the_404_page_is_not_advertised(built):
    """A crawler has no use for it, and jekyll-sitemap excludes it by default.
    Pinned so a later change of that default is noticed."""
    assert "/404" not in built("sitemap.xml")


def test_every_post_in_the_sitemap_carries_its_date(built):
    """Only posts have one. The section pages have no date to report, so
    requiring it of every entry would be wrong."""
    entries = re.findall(r"<url>\s*<loc>([^<]+)</loc>\s*(<lastmod>[^<]+</lastmod>)?",
                         built("sitemap.xml"))
    posts = [(loc, mod) for loc, mod in entries
             if re.search(r"/\d{4}/\d{2}/\d{2}/", loc)]
    assert posts, "no posts in the sitemap"
    undated = [loc for loc, mod in posts if not mod]
    assert not undated, "posts with no lastmod: %s" % undated[:5]
