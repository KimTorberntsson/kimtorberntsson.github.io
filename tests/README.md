# Browser tests

End to end tests for the fullscreen photo viewer (`scripts/lightbox.js` and
`css/lightbox.css`), driving a real headless Chromium with
[Playwright](https://playwright.dev/python/).

## Running them

```sh
./tests/run.sh
```

First run creates `tests/.venv` and downloads Chromium (about 95 MB, cached in
`~/Library/Caches/ms-playwright`). After that it is just pytest. The whole suite
takes about 20 seconds.

`run.sh` starts a Jekyll server if nothing is answering on
`http://localhost:4000`, and builds the site once with the production config for
the tests that check absolute URLs. Both happen there rather than in a fixture so
that the parallel workers share them instead of racing to create their own.

```sh
./tests/run.sh -k swipe                  # only the swipe tests
./tests/run.sh -p no:xdist               # serially, for readable output
./tests/run.sh --durations=10            # find the slow ones
./tests/run.sh --headed --slowmo 400     # watch it happen in a window
./tests/run.sh --base-url http://localhost:4001
```

Tests run across all cores by default (`-n auto`). Distribution is per test, not
per file: grouping by file pinned the largest module to one worker and left the
rest idle, which cost about 50 seconds.

## Layout

| file | |
|---|---|
| `conftest.py` | server startup, browser launch, `desktop` and `phone` fixtures |
| `viewer.py` | driver for the viewer: waits, gestures, state readers |
| `test_photo_viewer.py` | viewer behaviour |
| `test_gallery_links.py` | every photo URL resolves; no browser needed |

`desktop` is a 1440x900 window with a mouse and keyboard. `phone` is an
iPhone 13 with touch input and a coarse pointer, which matters because the
prev/next arrows are hidden behind `@media (hover: none) and (pointer: coarse)`.

Any console error or uncaught exception in the page fails the test that caused
it, via an autouse fixture.

## Notes

Photo counts are read from the page instead of being hardcoded, so adding posts
will not break anything. Tests naming a specific album skip themselves if that
post is gone.

Two kinds of input need raw CDP rather than Playwright's own API:

- **Touch gestures** are a sequence of `Input.dispatchTouchEvent` calls, since a
  swipe is many move events and Playwright only exposes taps.
- **A trackpad pinch** on macOS is not a touch gesture at all. Chrome reports it
  as a `wheel` event with `ctrlKey` set, so it is sent as
  `Input.dispatchMouseEvent` with the Ctrl modifier. Without handling it the
  browser zooms the entire page.

`Viewer.settle()` waits for the photo to decode *and* for both the overlay and
image fades to finish. Asserting or screenshotting before that catches the
viewer mid-transition and looks like a transparency bug.
