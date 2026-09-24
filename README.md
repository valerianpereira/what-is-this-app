# What is this?

An Android picture-naming game for 2–4 year olds, built from the Claude Design
handoff (`What Is This.dc.html`).

Show a photo, the child says the word out loud, five seconds later the app says
it back. Ten pictures a round, then a summary of the words seen.

22 groups, 545 words, 567 card pictures, **4 MB APK**.

The photos are not bundled. They are served from a CDN and cached on the device
as the child plays — each picture is downloaded the first time it comes up and
is local from then on, so the game keeps working with no network. A grown-up can
also pull the whole set down in one go (Parent zone → "Download all pictures")
before a flight.

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

## Publishing to Google Play

    npm run aab                # signed release bundle → dist/what-is-this.aab

The release build is signed with the Play upload key in
`android/upload-keystore.jks`, whose passwords live in
`android/keystore.properties`. Both are gitignored: back them up somewhere
safe — without the key, updates cannot be uploaded to the same listing. Without
the files the release build is unsigned and only `npm run apk` works.

Everything the Play Console asks for is in `store/`: `listing.md` has the
copy and the answers to the App content questionnaire, `icon-512.png` and
`feature-1024x500.png` are the listing art, `screenshots/01..05.png` the phone
screenshots. The privacy policy is published from the `gh-pages` branch at
https://valerianpereira.github.io/what-is-this-app/.

Bump `versionCode` in `android/app/build.gradle` before every upload.

## Layout

    app/index.html            whole app — markup, styles, game logic
    app/data/cards.json       every group and word, and where its photo comes from
    app/sw.js                 serves cached photos so the game works offline
    app/data/credits.json     photographer + licence per photo (bundled, tiny)
    app/fonts/                Fredoka variable font, 400–700

    photos/*.webp             the 567 card pictures, 720px squares — NOT shipped in
                              the APK; uploaded to the CDN and fetched on demand
    photos-src/*.jpg          the full frames those squares are cut from (gitignored)

    android/                  Capacitor wrapper (generated; `npm run apk` refreshes it)
    dist/what-is-this.apk     built debug APK (gitignored)

    tools/fetch-images.mjs    downloads the full frame of any photo cards.json is missing
    tools/square.py           cuts the square card out of each frame, around its subject
    tools/salient.swift       asks macOS Vision where the subject is (used by square.py)
    tools/find-square.py      finds Commons photos whose subject fits a square whole
    tools/upload-cloudinary.mjs  uploads photos/ to Cloudinary, prints imageBase
    tools/draw-cards.py       renders the shape and colour cards, which have no photo
    tools/check.mjs           asserts every card has a photo and a credit
    tools/contact-sheet.py    composes a labelled sheet of the photos, to eyeball them
    tools/candidates.mjs      shows Commons search results when a photo needs replacing
    tools/repin.mjs           points a card at a different photo and forgets the old one
    tools/make-android-icons.py  draws the logo: launcher icons, splash, store icon + feature graphic
    tools/store-shots.py      frames store/screenshots/raw-*.png into Play Store screenshots

    store/                    Play Store listing copy, art and screenshots

## Changing the words or pictures

`app/data/cards.json` is the only place groups and words are defined — the app
reads it at boot and the fetcher reads it to download photos. Its `imageBase`
field is where the app fetches photos from at runtime. Each item names
the Wikipedia article its photo comes from. A `File:Foo.jpg` value pins one
exact Wikimedia Commons file, which is how items whose article lead image is a
painting, a collage or a botanical diagram (Doctor, Coconut, Harp, …) get a
usable photo.

    npm run images        # downloads the full frame of whatever is missing
    npm run square        # cuts every frame into its 720px square card
    npm run check         # fails on a missing/non-square photo, a duplicate word, a stray credit
    python3 tools/contact-sheet.py /tmp/sheet.jpg     # look at all 567 at once

To replace one bad photo:

    node tools/repin.mjs 'vehicles:Truck=File:Tata Truck India.jpg'
    npm run images

`repin.mjs` rewrites the item's `wiki` and forgets the old credit, so the
fetcher downloads the replacement frame; `npm run square` then cuts the card.
Then bump
`imageVersion` in `cards.json` — the photo URLs carry it as `?v=`, which is what
makes a replaced photo actually reach a device (or a CDN) holding the old one
under the same name.

### Why the photos are square

The card is square and shows its photo edge to edge, and three Commons photos
in four are not square. A centre crop was cutting wheels and heads off;
letterboxing left white bands. So the square is cut at build time instead:
`fetch-images.mjs` keeps the full frame in `photos-src/`, and `square.py` asks
macOS Vision (`salient.swift`) where the subject is and cuts the largest square
the frame allows around it. `check.mjs` refuses any card that is not 720×720.

A subject wider or taller than that square cannot be shown whole from that
photo — `square.py` lists those at the end. For each, `find-square.py` searches
Commons and shows only candidates whose subject *does* fit a square (already
cut, so the sheet shows the card as it would be):

    python3 tools/find-square.py /tmp/cands 'vehicles:Motorcycle=motorcycle parked'
    node tools/repin.mjs 'vehicles:Motorcycle=File:<name from the sheet>'

Flags are the exception: no photo of a flag is square, so the `countries` group
is `"crop": "center"` — a plain centre crop, which keeps the emblem.

Photos are fetched at 720px (the round card at 3× on a 1080p phone) and encoded
as WebP q78 — about half the bytes of the equivalent JPEG. Requires `cwebp`
(`brew install webp`).

### Hosting the photos

    export CLOUDINARY_URL='cloudinary://<api_key>:<api_secret>@<cloud_name>'
    node tools/upload-cloudinary.mjs        # skips what is already uploaded

It prints the `imageBase` value to paste into `app/data/cards.json`.
Credentials are read from the environment only — never commit them.

Any static host works; nothing Cloudinary-specific is relied on. The host must
send `Access-Control-Allow-Origin`, which Cloudinary and jsDelivr both do.

## Development

`npm run preview` serves `app/` at http://localhost:8000 for quick iteration in
a desktop browser — a dev convenience only. The shipped product is the APK;
there is no web build, service worker, or installable PWA.

## Playing a round

Ten pictures. The ring counts down, then the answer appears, is read out, and
the app moves on. Tapping the picture shows the answer early. Tapping the left
half of the screen goes back a picture, the right half goes on — at any time,
in either mode.

"Manual mode" in Settings removes the timer altogether: nothing moves until it
is tapped — the picture for the answer, the sides to move. On the summary,
tapping a word says it and shows its picture again.

## Sound

Two controls, one setting: the speaker button in the round's top bar, and
"Say the answer" in Settings. Off means no speech at all. The choice is saved,
so muting once keeps it muted on the next launch.

On a device the speech goes through the native `TextToSpeech` plugin, called
straight over Capacitor's bridge (`Capacitor.nativePromise`) — no import, so the
app stays a single HTML file with no build step. **Android's WebView has no
working Web Speech API**: `speechSynthesis` exists there and `speak()` is
silently ignored, which is why the first Play build had no voice. The browser
preview still uses `speechSynthesis`, which is why the bug did not show up
during development.

The engine reports no languages until it has finished starting up, so the app
asks it which of `en-GB`/`en-IN`/`en-US` it actually has, and asks again and
re-speaks once if the very first word is rejected.

## Licence

MIT for the code (`LICENSE`). The 520 photos keep their own Wikimedia licences
and the font is OFL — see `NOTICE.md`.

## Photos and licensing

All photos come from Wikimedia Commons / Wikipedia under CC and public-domain
licences. Attribution is required and is shown in the app: Settings → For
grown-ups → hold 2s → Photo credits. `app/data/credits.json` holds author,
licence and source URL for all 520. Keep that screen if you ship this.

The 45 Shapes and Colours cards are the exception: Wikipedia leads those
articles with annotated geometry diagrams and with an object of that colour
(Red → strawberries), which teaches the wrong word, so `tools/draw-cards.py`
draws them instead. They are CC0 and marked `"drawn": true` in `cards.json`,
which is what tells the fetcher to skip them.

## Android notes

- The APK asks for one permission, `INTERNET`, used only to fetch card photos.
  No analytics, no accounts, no other network traffic.
- The photo cache lives in the WebView's Cache Storage, served by `app/sw.js`.
  If Android evicts it under storage pressure, photos re-download as they come
  up again.
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
