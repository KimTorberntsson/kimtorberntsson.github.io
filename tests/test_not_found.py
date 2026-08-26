"""The 404 page.

There wasn't one, so a bad address got GitHub Pages' generic 404: no nav, no
way back into the site.
"""

import urllib.error
import urllib.request

import pytest


@pytest.fixture
def page(browser, base_url):
    context = browser.new_context(viewport={"width": 1280, "height": 900})
    page = context.new_page()
    page.goto(base_url + "/404.html", wait_until="load")
    page.wait_for_timeout(500)
    yield page
    context.close()


def test_the_page_is_built(base_url):
    request = urllib.request.Request(base_url + "/404.html", method="HEAD")
    assert urllib.request.urlopen(request, timeout=20).status == 200


def test_it_carries_the_usual_furniture(page):
    """The point of having one: the reader keeps the nav and a way onward."""
    assert page.evaluate("document.querySelectorAll('nav a').length") == 5
    assert page.evaluate("document.querySelectorAll('footer a').length") == 5
    assert page.evaluate("!!document.querySelector('#background')")


def test_it_offers_a_way_back(page):
    hrefs = page.evaluate(
        "[...document.querySelectorAll('article a')].map(a => a.getAttribute('href'))")
    for destination in ("/", "/archive/", "/gallery/"):
        assert destination in hrefs, "no link to %s, only %s" % (destination, hrefs)


def test_it_has_a_hero_photo_that_exists(page, base_url):
    """The hero is named after the page title, and there is no
    "Not Found.jpg" -- hence the `hero` front matter override."""
    url = page.evaluate("""() => {
        var bg = getComputedStyle(document.querySelector('#background')).backgroundImage;
        return bg.replace(/^url\\("?/, '').replace(/"?\\)$/, '');
    }""")
    assert "/assets/backgrounds/" in url, url
    request = urllib.request.Request(
        url.replace(" ", "%20").replace("'", "%27"), method="HEAD")
    assert urllib.request.urlopen(request, timeout=20).status == 200, url


def test_the_head_is_complete(page):
    """It goes through the same layout, so it should not have lost the tags."""
    assert page.evaluate("document.documentElement.lang") == "en"
    for selector in ('meta[name="description"]', 'link[rel="canonical"]',
                     'meta[property="og:title"]'):
        assert page.evaluate("!!document.querySelector('%s')" % selector), selector


def test_a_missing_address_is_not_silently_fine(base_url):
    """Jekyll's dev server returns the 404 page with a 404 status; GitHub Pages
    does the same. Worth pinning so a stray permalink change cannot make every
    bad URL return 200."""
    try:
        urllib.request.urlopen(base_url + "/no-such-page-here/", timeout=20)
    except urllib.error.HTTPError as exc:
        assert exc.code == 404
    else:
        pytest.fail("a missing address returned a success status")
