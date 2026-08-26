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


# ----------------------------------------------------------------- thumbnail size

SOF_MARKERS = {0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7,
               0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF}


def jpeg_dimensions(data):
    """Width and height from a JPEG's start-of-frame header.

    Avoids an image library for what is a dozen lines: the point is to catch a
    photo that was never resized before it lands in thumbs/.
    """
    i = 2
    while i + 9 < len(data):
        if data[i] != 0xFF:
            i += 1
            continue
        marker = data[i + 1]
        if marker in SOF_MARKERS:
            height = int.from_bytes(data[i + 5:i + 7], "big")
            width = int.from_bytes(data[i + 7:i + 9], "big")
            return width, height
        if marker == 0xD8 or marker == 0x01 or 0xD0 <= marker <= 0xD7:
            i += 2
            continue
        i += 2 + int.from_bytes(data[i + 2:i + 4], "big")
    return None


def test_no_thumbnail_is_a_full_size_photo(base_url, gallery):
    """Canon FD shipped four thumbnails that were never resized: 1080x1080 and
    1620x1080, 1.9 MB for four images where 55 KB does."""
    oversized = []
    for href, group, _ in gallery:
        thumb = href.replace("/full-size/", "/thumbs/")
        url = base_url + urllib.parse.quote(thumb, safe="/:&?=")
        data = urllib.request.urlopen(url, timeout=30).read()
        size = jpeg_dimensions(data)
        assert size, "could not read dimensions of %s" % thumb
        if max(size) > 256:
            oversized.append((group, thumb, "%dx%d" % size, "%d KB" % (len(data) // 1024)))
    assert not oversized, "thumbnails that were never resized: %s" % oversized


def test_thumbnails_are_uniformly_square(base_url, gallery):
    """The gallery grid crops to 1:1, so a stray aspect ratio wastes bytes."""
    shapes = {}
    for href, _, _ in gallery:
        thumb = href.replace("/full-size/", "/thumbs/")
        url = base_url + urllib.parse.quote(thumb, safe="/:&?=")
        size = jpeg_dimensions(urllib.request.urlopen(url, timeout=30).read())
        shapes["%dx%d" % size] = shapes.get("%dx%d" % size, 0) + 1
    assert len(shapes) == 1, "mixed thumbnail sizes: %s" % shapes
