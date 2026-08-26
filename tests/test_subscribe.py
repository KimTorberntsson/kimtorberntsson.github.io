"""The subscribe page.

The footer used to link straight at /feed.xml, so anyone who clicked it landed
on "This XML file does not appear to have any style information associated with
it" — alarming if you do not know what a feed is. This page explains it, while
keeping the direct route one click away for people who do.
"""

import os
import urllib.request

import pytest


@pytest.fixture
def page(browser, base_url):
    context = browser.new_context(viewport={"width": 1280, "height": 900})
    context.grant_permissions(["clipboard-read", "clipboard-write"], origin=base_url)
    page = context.new_page()
    page.goto(base_url + "/subscribe/", wait_until="load")
    page.wait_for_timeout(500)
    page.base = base_url
    yield page
    context.close()


def test_the_page_exists_and_uses_the_site_layout(page):
    assert page.evaluate("document.querySelectorAll('nav a').length") == 5
    assert page.evaluate("!!document.querySelector('#background')")
    assert page.evaluate("document.querySelector('#hero h1').textContent.trim()") \
        == "Subscribe"


def test_the_address_is_shown_and_can_be_copied(page):
    shown = page.evaluate("document.getElementById('feed-url').textContent.trim()")
    assert shown.endswith("/feed.xml"), shown

    assert page.evaluate("!document.getElementById('copy-feed').hidden"), \
        "the copy button never appeared"
    page.click("#copy-feed")
    page.wait_for_timeout(400)
    assert page.evaluate("navigator.clipboard.readText()") == shown
    assert page.evaluate("document.getElementById('copy-feed').textContent") == "Copied"


def test_the_address_is_absolute_in_a_real_build(production_site):
    """`jekyll serve` rewrites site.url to localhost, so the address only reads
    correctly in a production build."""
    built = open(os.path.join(production_site, "subscribe/index.html"),
                 encoding="utf-8").read()
    assert "https://kimtorberntsson.com/feed.xml" in built
    assert "localhost" not in built


def test_people_who_know_what_they_want_are_one_click_away(page):
    """The reason for the shortcut line: the explanation should not be a toll."""
    shortcut = page.evaluate("""() => {
        var paras = [...document.querySelectorAll('article p')];
        var i = paras.findIndex(p => p.querySelector('a[href$="feed.xml"]'));
        return {present: i >= 0, order: i};
    }""")
    assert shortcut and shortcut["present"], "no direct feed link on the page"
    assert shortcut["order"] <= 2, \
        "the shortcut is the %dth paragraph, too far down" % shortcut["order"]


def test_the_raw_feed_still_works(page):
    request = urllib.request.Request(page.base + "/feed.xml", method="HEAD")
    assert urllib.request.urlopen(request, timeout=20).status == 200


def test_the_nav_leads_here_not_to_the_raw_file(page):
    """It belongs in the nav now that it is a page rather than an XML file."""
    hrefs = page.evaluate(
        "[...document.querySelectorAll('nav a')].map(a => a.getAttribute('href'))")
    assert "/subscribe/" in hrefs, hrefs
    assert not [h for h in hrefs if h.endswith("feed.xml")], \
        "the nav still points at the raw file: %s" % hrefs


def test_readers_can_still_discover_the_feed_automatically(page):
    """Which is how anyone experienced actually subscribes: they paste the
    domain and the reader follows the alternate link."""
    alternate = page.evaluate("""() => {
        var l = document.querySelector('link[rel="alternate"]');
        return l && {type: l.getAttribute('type'), href: l.getAttribute('href')};
    }""")
    assert alternate, "no alternate link in the head"
    assert alternate["type"] == "application/rss+xml"
    assert alternate["href"].endswith("/feed.xml")


def test_the_explanation_stays_short(page):
    """A signpost, not an essay, and not written down to the reader."""
    article = page.evaluate("document.querySelector('article').innerText")
    words = len(article.split())
    for patronising in ("algorithm", "without an account"):
        assert patronising not in article.lower(), \
            "the copy still says %r" % patronising
    assert words < 90, "the page is %d words" % words
