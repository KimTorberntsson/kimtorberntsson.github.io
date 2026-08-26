"""Behaviour of the fullscreen photo viewer (scripts/lightbox.js).

Photo counts are read from the page rather than hardcoded, so adding posts does
not break the suite. Tests that name a specific album skip themselves if that
post is gone.
"""

import pytest

# Titles with characters that have to survive being used as both a URL path and
# an attribute value.
AWKWARD_ALBUMS = ["Superbowl & San Francisco", "St Patrick's in San Francisco"]

# One album per aspect ratio, to check the photo is fitted and never stretched.
SHAPES = [
    "Arriving at Stanford",          # 1080x1620, portrait
    "Point Reyes",                   # 1620x1080, landscape
    "Astrid",                        # 1920x1920, square
    "San Francisco With Family I",   # 1920x452, panorama
]


def _per_row(view, album):
    """Widest row of thumbnails belonging to one album."""
    return view.page.evaluate(
        """name => {
            var all = [...document.querySelectorAll('[data-lightbox]')]
                .filter(a => a.dataset.lightbox === name);
            var rows = {};
            all.forEach(a => {
                var top = Math.round(a.getBoundingClientRect().top);
                rows[top] = (rows[top] || 0) + 1;
            });
            return Math.max(...Object.values(rows));
        }""",
        album,
    )


def require(view, album):
    if view.count(album) == 0:
        pytest.skip("album %r is not on the page" % album)
    return view.count(album)


# --------------------------------------------------------------- opening and closing


def test_thumbnail_opens_the_viewer(desktop):
    desktop.goto("/gallery/")
    assert not desktop.page.evaluate("!!document.querySelector('.lb-overlay')"), \
        "the overlay should not exist until it is needed"
    desktop.open()
    assert desktop.is_open()


def test_counter_and_caption_describe_the_photo(desktop):
    desktop.goto("/gallery/")
    total = require(desktop, "Astrid")
    desktop.open("Astrid", 0)
    assert desktop.counter() == "1 / %d" % total
    assert desktop.caption(), "photos in this album have titles in the front matter"


def test_counter_leads_the_bar_and_is_legible(desktop):
    """It used to be dim grey in the opposite corner from the caption."""
    desktop.goto("/gallery/")
    require(desktop, "Astrid")
    desktop.open("Astrid", 1)
    layout = desktop.page.evaluate("""() => {
        var c = document.querySelector('.lb-counter');
        var p = document.querySelector('.lb-caption');
        var cr = c.getBoundingClientRect(), pr = p.getBoundingClientRect();
        return {colour: getComputedStyle(c).color,
                counterLeft: cr.left, captionLeft: pr.left,
                sameRow: Math.abs(cr.top - pr.top) < 6};
    }""")
    assert layout["colour"] == "rgb(255, 255, 255)"
    assert layout["counterLeft"] < layout["captionLeft"]
    assert layout["sameRow"]


def test_escape_closes_and_releases_the_scroll_lock(desktop):
    desktop.goto("/gallery/")
    desktop.open()
    assert desktop.locked()
    desktop.close_with_escape()
    assert not desktop.is_open()
    assert not desktop.locked()


def test_backdrop_closes_but_the_photo_itself_does_not(desktop):
    """A stray click must not eject you from a thirty photo album."""
    desktop.goto("/gallery/")
    require(desktop, "Astrid")
    desktop.open("Astrid", 0)

    box = desktop.photo_box()
    desktop.page.mouse.click(720, 450)          # centre of the photo
    desktop.page.wait_for_timeout(350)
    assert desktop.is_open(), "clicking the photo should do nothing"

    # Left edge, below the prev button, which occupies the vertical middle.
    desktop.page.mouse.click(60, 830)
    desktop.page.wait_for_timeout(350)
    assert not desktop.is_open(), "clicking the backdrop should close"


def test_browser_back_closes_the_viewer(desktop):
    desktop.goto("/gallery/")
    desktop.open()
    desktop.page.go_back()
    desktop.page.wait_for_timeout(350)
    assert not desktop.is_open()
    assert "/gallery/" in desktop.page.url, "back should not leave the page"


# ------------------------------------------------------------------------ navigation


def test_arrow_keys_move_through_the_album(desktop):
    desktop.goto("/gallery/")
    total = require(desktop, "Point Reyes")
    desktop.open("Point Reyes", 0)

    desktop.page.keyboard.press("ArrowRight")
    desktop.wait_counter("2 / %d" % total)
    desktop.page.keyboard.press("ArrowRight")
    desktop.wait_counter("3 / %d" % total)
    desktop.page.keyboard.press("ArrowLeft")
    desktop.wait_counter("2 / %d" % total)


def test_home_end_and_wrap_around(desktop):
    desktop.goto("/gallery/")
    total = require(desktop, "Point Reyes")
    desktop.open("Point Reyes", 0)

    desktop.page.keyboard.press("End")
    desktop.wait_counter("%d / %d" % (total, total))
    desktop.page.keyboard.press("ArrowRight")
    desktop.wait_counter("1 / %d" % total)          # wraps past the last photo
    desktop.page.keyboard.press("ArrowLeft")
    desktop.wait_counter("%d / %d" % (total, total))  # and wraps backwards
    desktop.page.keyboard.press("Home")
    desktop.wait_counter("1 / %d" % total)


def test_prev_and_next_buttons(desktop):
    desktop.goto("/gallery/")
    total = require(desktop, "Point Reyes")
    desktop.open("Point Reyes", 0)

    desktop.page.click(".lb-next")
    desktop.wait_counter("2 / %d" % total)
    desktop.page.click(".lb-prev")
    desktop.wait_counter("1 / %d" % total)


@pytest.mark.parametrize("album", AWKWARD_ALBUMS)
def test_albums_with_awkward_titles_open(desktop, album):
    """Album names double as directory names, so & and ' must survive."""
    desktop.goto("/gallery/")
    total = require(desktop, album)
    desktop.open(album, 0)
    assert desktop.counter() == "1 / %d" % total
    assert desktop.caption()


def test_each_thumbnail_opens_only_its_own_album(desktop):
    """The blog index carries several albums on one page."""
    desktop.goto("/")
    albums = desktop.albums()
    assert len(albums) >= 2, "expected several posts with photos on the index"
    for album in albums[:3]:
        total = desktop.count(album)
        desktop.open(album, 0)
        assert desktop.counter() == "1 / %d" % total, \
            "%r leaked photos from another album" % album
        desktop.close_with_escape()


# ------------------------------------------------------------------------- fitting


@pytest.mark.parametrize("album", SHAPES)
def test_photo_is_fitted_and_never_stretched_on_desktop(desktop, album):
    desktop.goto("/gallery/")
    require(desktop, album)
    desktop.open(album, 0)
    box = desktop.photo_box()

    source = box["nw"] / box["nh"]
    shown = box["w"] / box["h"]
    assert abs(source - shown) < 0.02, "%s was distorted" % album

    fills_width = box["w"] >= box["sw"] - 1
    fills_height = box["h"] >= box["sh"] - 1
    assert fills_width or fills_height, \
        "%s filled neither axis: %sx%s in %sx%s" % (
            album, box["w"], box["h"], box["sw"], box["sh"])


@pytest.mark.parametrize("album", SHAPES)
def test_photo_is_fitted_and_never_stretched_on_a_phone(phone, album):
    phone.goto("/gallery/")
    require(phone, album)
    phone.open(album, 0)
    box = phone.photo_box()

    assert abs(box["nw"] / box["nh"] - box["w"] / box["h"]) < 0.02, \
        "%s was distorted" % album
    assert box["w"] >= box["sw"] - 1, "%s should span the full width" % album


# ---------------------------------------------------------------- focus behaviour


def test_focus_returns_to_the_thumbnail_it_was_opened_from(desktop):
    desktop.goto("/gallery/")
    require(desktop, "Astrid")
    thumb = desktop.thumbs("Astrid").nth(1)
    expected = thumb.get_attribute("href")

    desktop.open("Astrid", 1)
    desktop.close_with_escape()
    assert desktop.page.evaluate(
        "document.activeElement && document.activeElement.getAttribute('href')"
    ) == expected, "keyboard users would otherwise restart from the top of the page"


def test_keyboard_focus_lifts_the_thumbnail_instead_of_ringing_it(desktop):
    """Focus reuses the hover lift, so there is no separate ring to design."""
    desktop.goto("/gallery/")
    require(desktop, "Astrid")
    desktop.open("Astrid", 1)
    desktop.close_with_escape()

    state = desktop.page.evaluate("""() => {
        var a = document.activeElement;
        var s = getComputedStyle(a), img = getComputedStyle(a.querySelector('img'));
        return {focusVisible: a.matches(':focus-visible'),
                outline: s.outlineStyle,
                scale: new DOMMatrix(img.transform).a,
                shadow: img.boxShadow};
    }""")
    assert state["focusVisible"], "a keyboard close should show where focus went"
    assert state["outline"] == "none", "no outline: the lift is the indicator"
    assert state["scale"] > 1.02, "the focused thumbnail should lift"
    assert state["shadow"] != "none"


def test_pointer_users_get_focus_back_with_no_indicator(desktop):
    desktop.goto("/gallery/")
    require(desktop, "Astrid")
    desktop.open("Astrid", 1)
    desktop.page.mouse.click(60, 830)   # backdrop, clear of the controls
    desktop.page.wait_for_timeout(350)

    state = desktop.page.evaluate("""() => {
        var a = document.activeElement;
        var s = getComputedStyle(a), img = getComputedStyle(a.querySelector('img'));
        return {onThumb: a.hasAttribute('data-lightbox'),
                focusVisible: a.matches(':focus-visible'),
                outline: s.outlineStyle,
                scale: new DOMMatrix(img.transform).a};
    }""")
    assert state["onThumb"], "focus should still be restored"
    assert not state["focusVisible"]
    assert state["outline"] == "none"
    assert state["scale"] == pytest.approx(1, abs=0.001), \
        "a mouse user should see nothing happen"


def test_a_lifted_thumbnail_does_not_overlap_its_neighbours(desktop):
    """The lift grows the photo, so the grid needs room for it."""
    desktop.goto("/gallery/")
    require(desktop, "Canon FD")
    thumbs = desktop.thumbs("Canon FD")
    if thumbs.count() < 2:
        pytest.skip("need at least two photos in a row")

    target = thumbs.nth(1)
    target.scroll_into_view_if_needed()
    box = target.bounding_box()
    desktop.page.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
    desktop.page.wait_for_timeout(350)

    overlap = desktop.page.evaluate(
        """name => {
            var all = [...document.querySelectorAll('[data-lightbox]')]
                .filter(a => a.dataset.lightbox === name);
            var me = all[1].querySelector('img').getBoundingClientRect();
            return all.map((a, i) => {
                if (i === 1) return null;
                var r = a.querySelector('img').getBoundingClientRect();
                if (Math.abs(r.top - me.top) > me.height / 2) return null;  // other row
                var gap = r.left > me.left ? r.left - me.right : me.left - r.right;
                return Math.round(gap * 100) / 100;
            }).filter(v => v !== null);
        }""",
        "Canon FD",
    )
    assert overlap, "expected at least one neighbour in the same row"
    assert all(gap > 0 for gap in overlap), \
        "the lifted photo overlaps a neighbour, gaps: %s" % overlap


# ------------------------------------------------------------- thumbnail treatment


def test_thumbnails_do_not_behave_like_selectable_text(desktop):
    desktop.goto("/gallery/")
    style = desktop.page.eval_on_selector(
        "[data-lightbox]",
        """e => { var s = getComputedStyle(e);
                  return {select: s.webkitUserSelect || s.userSelect,
                          tap: s.webkitTapHighlightColor}; }""",
    )
    assert style["select"] == "none"
    assert "rgba(0, 0, 0, 0)" in style["tap"], "no grey flash when tapped"


def test_photos_render_at_full_strength(desktop):
    """a { opacity: 0.6 } in text.sass used to fade every photo on the site."""
    desktop.goto("/gallery/")
    desktop.page.mouse.move(2, 2)
    desktop.page.wait_for_timeout(300)
    opacities = desktop.page.evaluate(
        "[...document.querySelectorAll('[data-lightbox]')]"
        ".slice(0, 8).map(a => getComputedStyle(a).opacity)"
    )
    assert set(opacities) == {"1"}, "photos should not be dimmed at rest: %s" % opacities


def test_hovering_lifts_only_the_photo_under_the_cursor(desktop):
    """Fading the siblings made the whole grid flash on cursor entry."""
    desktop.goto("/gallery/")
    require(desktop, "Canon FD")
    thumbs = desktop.thumbs("Canon FD")
    if thumbs.count() < 2:
        pytest.skip("need at least two photos to compare")

    target = thumbs.nth(1)
    target.scroll_into_view_if_needed()
    box = target.bounding_box()
    desktop.page.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
    desktop.page.wait_for_timeout(350)

    state = desktop.page.evaluate(
        """name => [...document.querySelectorAll('[data-lightbox]')]
            .filter(a => a.dataset.lightbox === name)
            .map(a => { var s = getComputedStyle(a.querySelector('img'));
                        return {scale: new DOMMatrix(s.transform).a,
                                opacity: parseFloat(getComputedStyle(a).opacity),
                                shadow: s.boxShadow}; })""",
        "Canon FD",
    )

    assert state[1]["scale"] > 1.02, "the hovered photo should lift"
    assert state[1]["shadow"] != "none", "and cast a shadow"
    for i, other in enumerate(state):
        if i == 1:
            continue
        assert other["scale"] == pytest.approx(1, abs=0.001), \
            "sibling %d moved, which is what made it blink" % i
        assert other["opacity"] == 1.0, "siblings must not be dimmed: %s" % state


# ------------------------------------------------------------------ trackpad pinch


def test_trackpad_pinch_zooms_the_photo_not_the_page(desktop):
    """macOS sends a ctrl-modified wheel event, never touch events."""
    desktop.goto("/gallery/")
    require(desktop, "Point Reyes")
    desktop.open("Point Reyes", 0)

    assert desktop.scale() == pytest.approx(1, abs=0.01)
    desktop.pinch(-40, times=4)
    assert desktop.scale() > 1.4, "pinching in should magnify the photo"
    assert desktop.page_zoom() == 1, "the browser must not zoom the whole page"


def test_pinching_back_out_returns_to_a_centred_fit(desktop):
    desktop.goto("/gallery/")
    require(desktop, "Point Reyes")
    desktop.open("Point Reyes", 0)

    desktop.pinch(-40, times=6)
    desktop.pinch(40, times=25)
    assert desktop.scale() == pytest.approx(1, abs=0.02)
    x, y = desktop.translation()
    assert abs(x) + abs(y) < 0.5, "a fitted photo should sit centred"


def test_zoom_stops_at_the_ceiling(desktop):
    desktop.goto("/gallery/")
    require(desktop, "Point Reyes")
    desktop.open("Point Reyes", 0)
    desktop.pinch(-50, times=40)
    assert desktop.scale() == pytest.approx(4, abs=0.01)


def test_a_wheel_notch_is_not_a_huge_jump(desktop):
    """Undamped, a single notch multiplied the scale by about 1.5."""
    desktop.goto("/gallery/")
    require(desktop, "Point Reyes")
    desktop.open("Point Reyes", 0)
    desktop.pinch(-100, times=1)
    assert 1.1 < desktop.scale() < 1.45, "one notch moved %.3fx" % desktop.scale()


def test_an_ordinary_scroll_is_not_a_pinch(desktop):
    desktop.goto("/gallery/")
    require(desktop, "Point Reyes")
    desktop.open("Point Reyes", 0)
    desktop.wheel(-120)
    assert desktop.scale() == pytest.approx(1, abs=0.01)


# ------------------------------------------------------------------------ on touch


def test_arrows_are_hidden_on_a_touch_screen(phone):
    phone.goto("/gallery/")
    phone.open()
    for control in (".lb-prev", ".lb-next"):
        assert phone.page.eval_on_selector(control, "e => getComputedStyle(e).display") == "none"
    assert phone.page.eval_on_selector(".lb-close", "e => getComputedStyle(e).display") != "none", \
        "closing must stay reachable without a swipe"


def test_swiping_moves_through_the_album(phone):
    phone.goto("/gallery/")
    total = require(phone, "Point Reyes")
    phone.open("Point Reyes", 0)

    phone.swipe(-220, 0)
    phone.wait_counter("2 / %d" % total)
    phone.swipe(220, 0)
    phone.wait_counter("1 / %d" % total)


def test_a_short_drag_springs_back(phone):
    phone.goto("/gallery/")
    total = require(phone, "Point Reyes")
    phone.open("Point Reyes", 0)
    phone.swipe(0, 30)
    phone.page.wait_for_timeout(400)
    assert phone.is_open(), "30px is not a dismissal"
    assert phone.counter() == "1 / %d" % total


def test_swiping_down_dismisses(phone):
    phone.goto("/gallery/")
    require(phone, "Point Reyes")
    phone.open("Point Reyes", 0)
    w, h = phone.viewport()
    phone.swipe(0, 260, y=h / 3)
    phone.page.wait_for_timeout(500)
    assert not phone.is_open()
    assert not phone.locked()


def test_double_tap_zooms_in_and_back_out(phone):
    phone.goto("/gallery/")
    require(phone, "Astrid")
    phone.open("Astrid", 0)

    phone.double_tap()
    assert phone.scale() > 2.0, "double tap should magnify"
    phone.double_tap()
    assert phone.scale() == pytest.approx(1, abs=0.05), "and toggle back to fit"


def test_dragging_a_zoomed_photo_pans_instead_of_navigating(phone):
    phone.goto("/gallery/")
    total = require(phone, "Astrid")
    phone.open("Astrid", 0)

    phone.double_tap()
    assert phone.scale() > 2.0
    before = phone.translation()
    phone.swipe(-150, 0)
    phone.page.wait_for_timeout(350)

    assert phone.counter() == "1 / %d" % total, "a zoomed drag must not change photo"
    assert phone.translation() != before, "it should pan the photo instead"


# ------------------------------------------------------------------ gallery layout


def test_four_thumbnails_per_row_on_desktop(desktop):
    """Was three, clamped by article's 40em text column."""
    desktop.goto("/gallery/")
    album = "San Francisco With Family I"
    if desktop.count(album) < 8:
        pytest.skip("need a reasonably large album")
    assert _per_row(desktop, album) == 4


def test_two_thumbnails_per_row_on_a_phone(phone):
    phone.goto("/gallery/")
    album = "San Francisco With Family I"
    if phone.count(album) < 4:
        pytest.skip("need a reasonably large album")
    assert _per_row(phone, album) == 2


@pytest.mark.parametrize("root_font_px", [14, 16, 18, 20, 24])
def test_column_count_ignores_the_readers_font_size(desktop, root_font_px):
    """An em wide container against px thumbnails gave four columns at 16px and
    five at 18px. The grid states the count, so it no longer drifts."""
    desktop.goto("/gallery/")
    album = "San Francisco With Family I"
    if desktop.count(album) < 8:
        pytest.skip("need a reasonably large album")

    desktop.page.add_style_tag(content="html { font-size: %dpx }" % root_font_px)
    desktop.page.wait_for_timeout(150)
    assert _per_row(desktop, album) == 4, \
        "column count drifted at a %dpx root font" % root_font_px


def test_no_horizontal_overflow_on_desktop(desktop):
    """Breaking out of the column must not push the page sideways."""
    desktop.goto("/gallery/")
    assert not desktop.page.evaluate(
        "document.documentElement.scrollWidth > window.innerWidth"
    ), "page scrolls horizontally"


def test_no_horizontal_overflow_on_a_phone(phone):
    phone.goto("/gallery/")
    assert not phone.page.evaluate(
        "document.documentElement.scrollWidth > window.innerWidth"
    ), "page scrolls horizontally"


def test_galleries_stay_centred(desktop):
    desktop.goto("/gallery/")
    gaps = desktop.page.evaluate("""() => {
        var g = document.querySelector('.photo-gallery').getBoundingClientRect();
        return [Math.round(g.left), Math.round(window.innerWidth - g.right)];
    }""")
    assert abs(gaps[0] - gaps[1]) <= 2, "gallery is off centre: %s" % gaps


# ----------------------------------------------------------------- the filmstrip


def test_the_next_photo_follows_the_finger(phone):
    """The point of the three slide track: the neighbour is really on screen
    during the gesture, not revealed once it is over."""
    phone.goto("/gallery/")
    total = require(phone, "Point Reyes")
    if total < 3:
        pytest.skip("need a few photos")
    phone.open("Point Reyes", 0)

    width, _ = phone.viewport()
    at_rest = phone.slide_boxes()
    assert at_rest[1]["left"] == pytest.approx(0, abs=2), "current slide is centred"
    assert at_rest[2]["left"] >= width, "the next slide starts off screen"

    phone.drag_hold(-width * 0.3, 0)
    mid = phone.slide_boxes()
    offset = phone.track_offset()

    # One step of tolerance: the final touch move may not be processed yet.
    assert offset == pytest.approx(-width * 0.3, abs=phone.drag_step + 4), \
        "the track should follow the finger, offset was %.1f" % offset
    assert mid[2]["left"] < width, "the next photo should now be partly visible"
    assert mid[2]["left"] > 0, "and not yet fully arrived"
    assert mid[1]["left"] < 0, "the current photo should have moved off centre"

    phone.release()
    phone.wait_counter("2 / %d" % total)


def test_an_incomplete_drag_springs_the_track_back(phone):
    phone.goto("/gallery/")
    total = require(phone, "Point Reyes")
    phone.open("Point Reyes", 0)

    width, _ = phone.viewport()
    phone.drag_hold(-width * 0.08, 0)   # under the commit threshold
    assert phone.track_offset() < -10, "the track should still follow the finger"
    phone.release()
    phone.page.wait_for_timeout(400)

    assert phone.counter() == "1 / %d" % total, "should not have moved on"
    assert phone.track_offset() == pytest.approx(0, abs=1.5), "and should re-centre"


def test_dragging_backwards_brings_in_the_previous_photo(phone):
    phone.goto("/gallery/")
    total = require(phone, "Point Reyes")
    phone.open("Point Reyes", 1)

    width, _ = phone.viewport()
    phone.drag_hold(width * 0.3, 0)
    mid = phone.slide_boxes()
    assert mid[0]["right"] > 0, "the previous photo should be partly visible"
    phone.release()
    phone.wait_counter("1 / %d" % total)


def test_the_track_carries_a_previous_and_a_next_slide(desktop):
    desktop.goto("/gallery/")
    require(desktop, "Point Reyes")
    desktop.open("Point Reyes", 2)

    srcs = desktop.page.evaluate(
        """() => [...document.querySelectorAll('.lb-slide img')].map(i => i.getAttribute('src'))"""
    )
    assert len(srcs) == 3
    assert all(srcs), "every slide should have a source: %s" % srcs
    assert len(set(srcs)) == 3, "the three slides should hold different photos"
    assert srcs[1].endswith("img3.jpg"), "middle slide is the current photo: %s" % srcs[1]


def test_a_single_photo_album_resists_dragging(phone):
    """Nowhere to go, so the track should barely move and never commit."""
    phone.goto("/")
    singles = [a for a in phone.albums() if phone.count(a) == 1]
    if not singles:
        pytest.skip("no single photo albums on the index")

    phone.open(singles[0], 0)
    width, _ = phone.viewport()
    phone.drag_hold(-width * 0.4, 0)
    offset = phone.track_offset()
    assert abs(offset) < width * 0.2, "drag should be resisted, offset %.1f" % offset
    phone.release()
    phone.page.wait_for_timeout(400)
    assert phone.is_open(), "a resisted drag must not close or navigate"


def test_every_arrow_press_counts_even_when_the_key_repeats(desktop):
    """Moves animate, and step() used to refuse while one was in flight, so a
    held arrow key dropped most presses: ten presses advanced two photos."""
    desktop.goto("/gallery/")
    total = require(desktop, "Point Reyes")
    if total < 12:
        pytest.skip("need at least twelve photos")

    for gap_ms in (400, 120, 33):   # deliberate, brisk, key repeat
        desktop.open("Point Reyes", 0)
        for _ in range(10):
            desktop.page.keyboard.press("ArrowRight")
            desktop.page.wait_for_timeout(gap_ms)
        desktop.wait_counter("11 / %d" % total)
        desktop.close_with_escape()


def test_grabbing_the_track_mid_animation_does_not_lose_the_move(phone):
    phone.goto("/gallery/")
    total = require(phone, "Point Reyes")
    phone.open("Point Reyes", 0)

    width, _ = phone.viewport()
    phone.swipe(-width * 0.5, 0)        # commits, starts animating
    phone.page.wait_for_timeout(40)     # grab it before it settles
    phone.drag_hold(-width * 0.4, 0)
    phone.release()
    phone.wait_counter("3 / %d" % total)


# ------------------------------------------------------------- review follow-ups


def test_hiding_a_nav_button_actually_hides_it(desktop):
    """.lb-btn sets a display, which beats the user agent rule for [hidden], so
    single photo albums were still showing the arrows."""
    desktop.goto("/gallery/")
    desktop.open()
    hidden = desktop.page.evaluate("""() => {
        var b = document.querySelector('.lb-prev');
        b.hidden = true;
        var display = getComputedStyle(b).display;
        b.hidden = false;
        return display;
    }""")
    assert hidden == "none", "[hidden] on a nav button was ignored"


def test_tab_stays_inside_the_viewer(desktop):
    """aria-modal promises focus does not escape to the page behind."""
    desktop.goto("/gallery/")
    require(desktop, "Point Reyes")
    desktop.open("Point Reyes", 0)

    seen = []
    for _ in range(6):
        desktop.page.keyboard.press("Tab")
        desktop.page.wait_for_timeout(40)
        seen.append(desktop.page.evaluate(
            "document.activeElement ? document.activeElement.className : null"
        ))

    assert all(c and "lb-" in c for c in seen), "focus left the viewer: %s" % seen
    assert len(set(seen)) > 1, "Tab should move between controls: %s" % seen


def test_shift_tab_also_stays_inside(desktop):
    desktop.goto("/gallery/")
    desktop.open()
    for _ in range(4):
        desktop.page.keyboard.press("Shift+Tab")
        desktop.page.wait_for_timeout(40)
    assert "lb-" in desktop.page.evaluate("document.activeElement.className")


def test_a_resize_mid_move_still_lands_it(desktop):
    """The resize handler used to drop the timer but keep the pending target,
    so the next keypress jumped to a stale photo."""
    desktop.goto("/gallery/")
    total = require(desktop, "Point Reyes")
    desktop.open("Point Reyes", 0)

    desktop.page.keyboard.press("ArrowRight")
    desktop.page.wait_for_timeout(40)               # interrupt mid-animation
    desktop.page.set_viewport_size({"width": 1100, "height": 800})
    desktop.wait_counter("2 / %d" % total)

    desktop.page.keyboard.press("ArrowRight")
    desktop.wait_counter("3 / %d" % total)          # not a jump to 4


def test_the_gutter_is_defined_only_in_css(desktop):
    """pitch() is measured from layout, so the CSS gap is the one source."""
    desktop.goto("/gallery/")
    desktop.open()
    gap = desktop.page.evaluate("""() => {
        var slides = document.querySelectorAll('.lb-slide');
        var a = slides[1].getBoundingClientRect(), b = slides[2].getBoundingClientRect();
        return Math.round((b.left - a.right) * 10) / 10;
    }""")
    assert gap == pytest.approx(12, abs=0.6), "unexpected gutter: %s" % gap
    assert desktop.track_offset() == pytest.approx(0, abs=1.5), \
        "the track should centre using the measured pitch"


def test_the_bar_announces_changes(desktop):
    desktop.goto("/gallery/")
    desktop.open()
    assert desktop.page.eval_on_selector(
        ".lb-bar", "e => e.getAttribute('aria-live')"
    ) == "polite"


# ------------------------------------------------------------------ lazy loading


def test_thumbnails_are_lazy(desktop):
    desktop.goto("/gallery/")
    attrs = desktop.page.evaluate(
        """() => {
            var all = [...document.querySelectorAll('.thumb')];
            return {total: all.length,
                    lazy: all.filter(i => i.loading === 'lazy').length,
                    sized: all.filter(i => i.width && i.height).length};
        }"""
    )
    assert attrs["total"] > 100, "expected the whole gallery"
    assert attrs["lazy"] == attrs["total"], \
        "%d of %d thumbnails are not lazy" % (attrs["total"] - attrs["lazy"], attrs["total"])
    assert attrs["sized"] == attrs["total"], "every thumbnail should declare its size"


def test_the_gallery_only_downloads_what_is_on_screen(phone):
    """It used to pull all 324 thumbnails, 23 MB, before you scrolled."""
    fetched = []
    phone.page.on(
        "response",
        lambda r: fetched.append(r.url) if "/thumbs/" in r.url else None,
    )
    phone.goto("/gallery/")
    phone.page.wait_for_timeout(3000)

    on_page = phone.page.evaluate("document.querySelectorAll('.thumb').length")
    assert on_page > 100
    assert len(fetched) < on_page / 3, \
        "%d of %d thumbnails downloaded before scrolling" % (len(fetched), on_page)


def test_scrolling_does_bring_the_rest_in(phone):
    """Lazy loading must defer the work, not lose it."""
    fetched = set()
    phone.page.on(
        "response",
        lambda r: fetched.add(r.url) if "/thumbs/" in r.url else None,
    )
    phone.goto("/gallery/")
    phone.page.wait_for_timeout(1500)
    before = len(fetched)

    for _ in range(12):
        phone.page.mouse.wheel(0, 2500)
        phone.page.wait_for_timeout(150)
    phone.page.wait_for_timeout(2000)

    assert len(fetched) > before + 20, \
        "scrolling loaded only %d more thumbnails" % (len(fetched) - before)


def test_thumbnails_are_square(desktop):
    """The suite had no shape assertion, so a regression shipped: the img width
    and height attributes are presentational hints, and without an explicit
    height: auto the hinted height won and aspect-ratio was ignored."""
    desktop.goto("/gallery/")
    shapes = desktop.page.evaluate(
        """() => [...document.querySelectorAll('.thumb')].slice(0, 24).map(i => {
            var r = i.getBoundingClientRect();
            return Math.round(r.width) + 'x' + Math.round(r.height);
        })"""
    )
    assert shapes, "no thumbnails found"
    off = [s for s in shapes if s.split("x")[0] != s.split("x")[1]]
    assert not off, "non-square thumbnails: %s" % sorted(set(off))


def test_thumbnails_fill_their_grid_cell(desktop):
    """A tile smaller than its cell means the grid and the image disagree."""
    desktop.goto("/gallery/")
    gap = desktop.page.evaluate("""() => {
        var cell = document.querySelector('[data-lightbox]').getBoundingClientRect();
        var img = document.querySelector('.thumb').getBoundingClientRect();
        return {cell: Math.round(cell.width), img: Math.round(img.width)};
    }""")
    assert gap["img"] == gap["cell"], "image %spx in a %spx cell" % (gap["img"], gap["cell"])
