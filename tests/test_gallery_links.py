"""Every photo the viewer can be asked to load must actually resolve.

Album directories are derived from post titles, so a renamed title silently
breaks a gallery. No browser needed for this one.
"""

import re
import urllib.parse
import urllib.request

import pytest

ANCHOR = re.compile(
    r'<a href="([^"]+)" data-lightbox="([^"]*)" data-title="([^"]*)">'
)


def anchors(base_url, path):
    html = urllib.request.urlopen(base_url + path, timeout=30).read().decode("utf-8")
    return ANCHOR.findall(html)


@pytest.fixture(scope="module")
def gallery(base_url):
    found = anchors(base_url, "/gallery/")
    assert found, "no photo anchors found on /gallery/"
    return found


def test_gallery_lists_every_album(base_url, gallery):
    albums = {group for _, group, _ in gallery}
    assert len(albums) >= 20, "expected every post with photos: got %d" % len(albums)


def test_every_photo_has_a_caption(gallery):
    missing = [(group, href) for href, group, title in gallery if not title.strip()]
    assert not missing, "photos without a data-title: %s" % missing[:10]


def test_every_full_size_photo_resolves(base_url, gallery):
    broken = []
    for href, group, _ in gallery:
        url = base_url + urllib.parse.quote(href, safe="/:&?=")
        request = urllib.request.Request(url, method="HEAD")
        try:
            if urllib.request.urlopen(request, timeout=30).status != 200:
                broken.append((group, href))
        except Exception as exc:
            broken.append((group, href, repr(exc)))
    assert not broken, "%d unreachable photos, first few: %s" % (len(broken), broken[:5])


def test_thumbnails_resolve_too(base_url, gallery):
    broken = []
    for href, group, _ in gallery:
        thumb = href.replace("/full-size/", "/thumbs/")
        url = base_url + urllib.parse.quote(thumb, safe="/:&?=")
        request = urllib.request.Request(url, method="HEAD")
        try:
            if urllib.request.urlopen(request, timeout=30).status != 200:
                broken.append((group, thumb))
        except Exception as exc:
            broken.append((group, thumb, repr(exc)))
    assert not broken, "%d unreachable thumbnails, first few: %s" % (len(broken), broken[:5])
