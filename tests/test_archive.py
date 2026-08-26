"""The archive list.

Each row is a title with its date to the right. The date used to be
`float: right`, which places it on whichever line it fits: a title long enough
to wrap pushed the date down, where it sat beside the title's second line or on
a line of its own directly above the next post, reading as that post's date.
"""

import pytest

LONG_TITLE = "Another Five Short Movie Reviews"   # long enough to wrap on a phone
WIDTHS = [320, 360, 390, 414, 768]


@pytest.fixture
def at_width(browser, base_url):
    made = []

    def open_at(width, height=900):
        context = browser.new_context(viewport={"width": width, "height": height})
        made.append(context)
        page = context.new_page()
        page.goto(base_url + "/archive/", wait_until="load")
        page.wait_for_timeout(500)
        return page

    yield open_at
    for context in made:
        context.close()


ROWS = """() => [...document.querySelectorAll('.list-posts li')].map(li => {
    var pEl = li.querySelector('p');
    var span = li.querySelector('.date-link');
    var pr = pEl.getBoundingClientRect(), sr = span.getBoundingClientRect();
    var line = parseFloat(getComputedStyle(pEl).lineHeight);
    return {title: pEl.firstChild.textContent.trim().slice(0, 34),
            date: span.textContent.trim(),
            dateOffset: sr.top - pr.top,
            lineHeight: line,
            height: li.getBoundingClientRect().height};
})"""


@pytest.mark.parametrize("width", WIDTHS)
def test_every_date_sits_on_the_first_line(at_width, width):
    rows = at_width(width).evaluate(ROWS)
    assert rows, "no archive rows"
    stray = [r for r in rows if r["dateOffset"] > r["lineHeight"]]
    assert not stray, "dates pushed off the first line at %dpx: %s" % (
        width, [(r["title"], r["date"]) for r in stray])


@pytest.mark.parametrize("width", WIDTHS)
def test_a_wrapping_title_does_not_move_its_date(at_width, width):
    """The row that showed the bug on a real phone."""
    rows = at_width(width).evaluate(ROWS)
    row = next((r for r in rows if r["title"].startswith(LONG_TITLE[:20])), None)
    if row is None:
        pytest.skip("%r is not in the archive any more" % LONG_TITLE)
    assert row["dateOffset"] <= row["lineHeight"], \
        "date is %.0fpx down a %.0fpx line at %dpx" % (
            row["dateOffset"], row["lineHeight"], width)


def test_dates_stay_on_the_first_line_however_long_the_title(at_width):
    """Synthetic titles, so this holds for posts that do not exist yet."""
    page = at_width(390)
    stray = page.evaluate("""() => {
        var rows = [...document.querySelectorAll('.list-posts li')];
        var long = 'A Weekend on the Country Side with Mikaela and the Whole Family';
        rows.slice(0, 6).forEach((li, i) => {
            li.querySelector('p').firstChild.textContent =
                long + ' '.repeat(1) + 'Word '.repeat(i * 3);
        });
        return rows.slice(0, 6).map(li => {
            var pEl = li.querySelector('p'), span = li.querySelector('.date-link');
            var pr = pEl.getBoundingClientRect(), sr = span.getBoundingClientRect();
            return Math.round(sr.top - pr.top);
        }).filter(offset => offset > parseFloat(
            getComputedStyle(document.querySelector('.list-posts p')).lineHeight));
    }""")
    assert not stray, "dates moved off the first line: %s" % stray


@pytest.mark.parametrize("width", WIDTHS)
def test_a_date_never_ends_up_nearer_the_next_row(at_width, width):
    """The visible symptom: the date read as belonging to the post below it."""
    rows = at_width(width).evaluate("""() => {
        var out = [];
        var items = [...document.querySelectorAll('.list-posts li')];
        items.forEach((li, i) => {
            var span = li.querySelector('.date-link').getBoundingClientRect();
            var own = li.querySelector('p').getBoundingClientRect();
            var next = items[i + 1]
                ? items[i + 1].querySelector('p').getBoundingClientRect() : null;
            if (!next) return;
            out.push({title: li.querySelector('p').firstChild.textContent.trim().slice(0, 30),
                      toOwnTop: span.top - own.top,
                      toNextTop: next.top - span.top});
        });
        return out;
    }""")
    confusing = [r for r in rows if r["toNextTop"] < r["toOwnTop"]]
    assert not confusing, "dates closer to the next row than their own at %dpx: %s" % (
        width, [r["title"] for r in confusing])


@pytest.mark.parametrize("width", WIDTHS)
def test_row_spacing_does_not_depend_on_the_column_width(at_width, width):
    """Vertical padding was a percentage, and a percentage resolves against the
    containing block's *width* -- including for padding-top and bottom. So rows
    were 54px on a phone and 67px once the article hit its 40em cap.
    """
    measured = at_width(width).evaluate("""() => {
        var rows = [...document.querySelectorAll('.list-posts li')];
        var s = getComputedStyle(rows[0].querySelector('p'));
        var line = parseFloat(s.lineHeight);
        // Only rows whose title fits on one line are comparable: a narrow
        // viewport wraps the longer titles, which is not what is being measured.
        var single = rows.filter(li =>
            li.querySelector('p').getBoundingClientRect().height
                < line + 2 * parseFloat(s.paddingTop) + 2);
        return {padding: parseFloat(s.paddingTop),
                singleLineRows: single.length,
                row: single.length
                    ? Math.round(single[0].getBoundingClientRect().height) : null};
    }""")
    assert measured["padding"] == pytest.approx(11.2, abs=0.5), \
        "vertical padding is %.1fpx at %dpx wide" % (measured["padding"], width)
    assert measured["singleLineRows"], "no single line rows to compare at %dpx" % width
    assert measured["row"] == pytest.approx(57, abs=2), \
        "a single line row is %dpx at %dpx wide" % (measured["row"], width)
