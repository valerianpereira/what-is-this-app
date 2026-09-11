# What is this?

An Android picture-naming game for 2–4 year olds, built from the Claude Design
handoff (`What Is This.dc.html`).

Show a photo, the child says the word out loud, five seconds later the app says
it back. Ten pictures a round, then a summary of the words seen.

17 groups × 15 things = 255 words, 272 photos, **16 MB APK**, no permissions,
no network, no accounts.

The UI is one HTML file running in a Capacitor WebView — there is no framework
and no build step for the app itself, only the Android packaging.

## Build and install

The APK is not in the repository — build it:

    npm install
    npm run apk                # cap sync + gradlew assembleDebug
    npm run install-apk        # adb install -r dist/what-is-this.apk

`npm run apk` writes `android/app/build/outputs/apk/debug/app-debug.apk`; copy
it to `dist/what-is-this.apk` (or straight to a phone and open it, allowing
install from unknown sources).

Needs the Android SDK (API 35+), JDK 17+, and `ANDROID_HOME` set. Use
`./gradlew clean assembleDebug` after changing assets — an incremental build
leaves the replaced files' bytes inside the APK and doubles its size.

## Layout

    app/index.html            whole app — markup, styles, game logic
    app/data/cards.json       every group and word, and where its photo comes from
    app/img/*.webp            272 photos (17 group tiles + 255 things)
    app/img/credits.json      photographer + licence per photo
    app/fonts/                Fredoka variable font, 400–700

    android/                  Capacitor wrapper (generated; `npm run apk` refreshes it)
    dist/what-is-this.apk     built debug APK (gitignored)

    tools/fetch-images.mjs    downloads any photo cards.json is missing
    tools/check.mjs           asserts every card has a photo and a credit
    tools/contact-sheet.py    composes a labelled sheet of the photos, to eyeball them
    tools/candidates.mjs      shows Commons search results when a photo needs replacing
    tools/make-android-icons.py  regenerates launcher icons and the splash

## Changing the words or pictures

`app/data/cards.json` is the only place groups and words are defined — the app
reads it at boot and the fetcher reads it to download photos. Each item names
the Wikipedia article its photo comes from. A `File:Foo.jpg` value pins one
exact Wikimedia Commons file, which is how items whose article lead image is a
painting, a collage or a botanical diagram (Doctor, Coconut, Harp, …) get a
usable photo.

    npm run images        # downloads only what is missing
    npm run check         # fails on a card with no photo, a duplicate word, a stray credit
    python3 tools/contact-sheet.py /tmp/sheet.jpg     # look at all 272 at once

To replace one bad photo: delete its `app/img/<slot>.webp` and its entry in
`app/img/credits.json`, point the item at a better article or `File:`, re-run
`npm run images`.

Photos are fetched at 720px (the round card at 3× on a 1080p phone) and encoded
as WebP q78 — about half the bytes of the equivalent JPEG, which is where most
of the 16 MB APK comes from. Requires `cwebp` (`brew install webp`).

## Development

`npm run preview` serves `app/` at http://localhost:8000 for quick iteration in
a desktop browser — a dev convenience only. The shipped product is the APK;
there is no web build, service worker, or installable PWA.

## Sound

Two controls, one setting: the speaker button in the round's top bar, and
"Say the answer" in Settings. Off means no speech at all. The choice is saved,
so muting once keeps it muted on the next launch. Speech uses the device's
built-in text-to-speech.

## Licence

MIT for the code (`LICENSE`). The 272 photos keep their own Wikimedia licences
and the font is OFL — see `NOTICE.md`.

## Photos and licensing

All photos come from Wikimedia Commons / Wikipedia under CC and public-domain
licences. Attribution is required and is shown in the app: Settings → For
grown-ups → hold 2s → Photo credits. `app/img/credits.json` holds author,
licence and source URL for all 272. Keep that screen if you ship this.

## Android notes

- The APK asks for **no permissions at all**, INTERNET included: every photo,
  the font and the page ship inside it, and nothing phones home.
- Locked to portrait.
- `dist/what-is-this.apk` is a debug build — fine for sideloading, not for the
  Play Store. For that, generate an upload key and run `./gradlew bundleRelease`.

## Deviations from the design

The prototype's `image-slot` placeholders are real `<img>` elements, and the
`ios-frame` device chrome is dropped (the OS provides it). The onboarding
screen's "Ages 2–4 · Offline" line was removed on request, and the round bar
gained the mute button. Settings persist to `localStorage`; the prototype reset
each launch. The round photo is `min(298px, 74vw)` so it fits phones narrower
than the 402px mock. Group sizes are read from the data rather than assumed to
be ten. Everything else — colours, type, spacing, timings, copy — is the design's.
