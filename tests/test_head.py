"""Document head: language, description, canonical and share tags.

None of this existed: no lang attribute, no description, no Open Graph, the feed
advertised as Atom when it is RSS 2.0, and site.url on http.
"""

import re
import urllib.parse
import urllib.request

import pytest

# These read a dedicated production build (the `production_site` fixture), not
# _site: `jekyll serve` regenerates _site with site.url pointing at localhost.
PAGES = [
    "index.html",
    "gallery/index.html",
    "archive/index.html",
    "about/index.html",
    "2019/04/24/astrid.html",
]
AWKWARD = [
    "2016/02/07/super-bowl.html",          # ampersand in the title
    "2016/03/20/st-patricks.html",         # apostrophe in the title
]


@pytest.fixture
def built(production_site):
    import os

    def read(path):
        full = os.path.join(production_site, path)
        assert os.path.exists(full), "%s was not built" % path
        return open(full, encoding="utf-8").read()

    return read


def meta(html, attr, name):
    m = re.search(r'<meta %s="%s" content="([^"]*)"' % (attr, re.escape(name)), html)
    return m.group(1) if m else None


@pytest.mark.parametrize("path", PAGES)
def test_the_page_declares_its_language(built, path):
    assert '<html lang="en">' in built(path)


@pytest.mark.parametrize("path", PAGES)
def test_there_is_a_description(built, path):
    html = built(path)
    description = meta(html, "name", "description")
    assert description, "no meta description"
    assert len(description) > 30, "description is too short: %r" % description


@pytest.mark.parametrize("path", PAGES)
def test_canonical_and_og_url_are_absolute_https(built, path):
    html = built(path)
    canonical = re.search(r'<link rel="canonical" href="([^"]*)"', html)
    assert canonical, "no canonical link"
    assert canonical.group(1).startswith("https://"), canonical.group(1)
    assert meta(html, "property", "og:url") == canonical.group(1)


@pytest.mark.parametrize("path", PAGES)
def test_the_share_tags_are_complete(built, path):
    html = built(path)
    for attr, name in [("property", "og:type"), ("property", "og:site_name"),
                       ("property", "og:title"), ("property", "og:description"),
                       ("property", "og:image"), ("name", "twitter:card"),
                       ("name", "twitter:title"), ("name", "twitter:image")]:
        assert meta(html, attr, name), "missing %s" % name


def test_posts_are_articles_and_pages_are_not(built):
    assert meta(built("2019/04/24/astrid.html"), "property", "og:type") == "article"
    assert meta(built("about/index.html"), "property", "og:type") == "website"
    assert meta(built("2019/04/24/astrid.html"), "property", "article:published_time")


@pytest.mark.parametrize("path", PAGES + AWKWARD)
def test_the_share_image_is_a_usable_url(built, path, base_url):
    """Titles double as filenames, so spaces, ampersands and apostrophes all
    have to survive being put in an attribute and then fetched."""
    image = meta(built(path), "property", "og:image")
    assert image and image.startswith("https://"), image
    assert "&" not in image, "bare ampersand in an attribute: %s" % image
    assert " " not in image, "unencoded space: %s" % image

    # Fetch it from the local server to prove the encoding resolves to a file.
    local = base_url + urllib.parse.urlsplit(image).path
    request = urllib.request.Request(local, method="HEAD")
    assert urllib.request.urlopen(request, timeout=30).status == 200, local


@pytest.mark.parametrize("path", PAGES)
def test_the_feed_is_advertised_as_rss_not_atom(built, path):
    """feed.xml declares <rss version="2.0">."""
    html = built(path)
    link = re.search(r'<link rel="alternate"[^>]*>', html)
    assert link, "no feed link"
    assert 'type="application/rss+xml"' in link.group(0), link.group(0)
    assert "http://kimtorberntsson" not in link.group(0), "feed link is on http"


@pytest.mark.parametrize("path", PAGES)
def test_nothing_still_points_at_http(built, path):
    html = built(path)
    offenders = [u for u in re.findall(r'http://[^\s"\'<>]+', html)
                 if "kimtorberntsson" in u]
    assert not offenders, "http:// links to our own site: %s" % offenders


def test_the_feed_itself_uses_https(built):
    feed = built("feed.xml")
    assert "https://kimtorberntsson.com" in feed
    assert "http://kimtorberntsson.com" not in feed
