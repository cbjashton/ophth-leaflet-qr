# EyeLeaflets

A phone app for eye clinic staff. Tap a condition or procedure and it shows a QR code; the patient scans it with their phone camera to open the patient information leaflet. 

- 183 leaflets from Moorfields Eye Hospital (public pages, as of 9 October 2026)
- Works offline once installed. The patient's phone still needs signal or Wi-Fi to open the leaflet.
- Favourites and most-used leaflets are saved on each phone. Only the developer can add or change leaflets.
- No accounts, no patient data.

## Put it online with GitHub Pages (about 10 minutes, free)

1. Create a free account at github.com.
2. Click **+** (top right) → **New repository**. Name it `leaflet-qr`, choose **Public**, tick **Add a README file**, then **Create repository**.
3. Click **Add file** → **Upload files**. Drag in everything from this folder, including the `source` folder. Click **Commit changes**.
4. Go to **Settings** → **Pages**. Under **Branch**, choose **main** and **/ (root)**, then **Save**.
5. After a minute or two the page shows your address, for example `https://yourname.github.io/leaflet-qr/`.

## Weekly link check

A GitHub job checks every leaflet link each Monday morning, and whenever `leaflets.json` changes. It's already set up in this repository at `.github/workflows/link-check.yml` (a copy is in `source/thumbnails.yml`). To run it straight away: **Actions** tab → **Weekly leaflet link check** → **Run workflow**.

Each run updates `link-report.md` with any leaflets that no longer open.

**Broken-link alerts.** If any link fails, the job opens an issue called *Leaflet links need checking* in the repository, and GitHub emails you about it (make sure email notifications are on in your GitHub settings). Each week it adds the latest report to that issue until the links are fixed, then closes it automatically.

The check only tests links. It doesn't keep copies of the Moorfields PDFs or pictures of their front pages, so **View leaflet** opens the leaflet from Moorfields, and press-and-hold previews show no picture. If Moorfields' patient information team later agree to copies being hosted (the repository is public, so anyone could find them), set `SAVE_PDF_COPIES` and `SAVE_FRONT_PAGES` to `True` in `source/make_thumbs.py`. The QR codes always send patients to the official Moorfields address either way.

A leaflet viewed once is saved on the phone and can be viewed again offline. The PDF viewer is PDF.js 5.7.284 (Mozilla, Apache 2.0 licence, in the `pdfjs` folder). Check for security updates to PDF.js a couple of times a year.

## Feedback and help

A small **Feedback** button at the top of the home screen opens a menu:

- **Request a leaflet**
- **Report a leaflet problem**
- **Something isn't working**
- **General feedback or ideas**
- **Help installing the app** (opens the install steps inside the app)

The first four open the Google Form stored in `leaflets.json` as `"reportForm"`. Google emails you each new response (Responses tab → ⋮ → Get email notifications for new responses). Set `"reportForm"` to `""` to hide the button.

To see which option someone chose, add a question to the form such as *What is this about?*, get a pre-filled link for it (⋮ → Get pre-filled link), and put its field name in `leaflets.json` as `"feedbackEntry": "entry.123456789"`. Each option then fills in its own label. To change the options, or send one to a different form, add a `"feedbackMenu"` list to `leaflets.json`, with `label`, `hint` and optionally `url` for each.

## Usage counts (optional, off by default)

For a quality improvement project, the app can send anonymous counts to GoatCounter, a free, cookie-free statistics service:

- once per phone: the app was installed (counted the first time it opens from the home screen)
- once a day per phone: the app was opened (how many people use it)
- each time a code is shown, and for which leaflet
- each time the app is shared

Nothing else is sent: no names, no patient details, no device identifiers. Counts made offline are sent when the phone next has signal. It counts codes **shown**, not codes **scanned**; a short patient survey gives the proportion actually opened.

To switch it on: create a site at goatcounter.com, then put its code (the `xxx` in `xxx.goatcounter.com`) into `leaflets.json` as `"statsCode": "xxx"`. Agree this with governance first and tell staff it's on; it's still worth noting in the DPIA screening even though no personal data is collected.

**Paper saved:** with `SAVE_FRONT_PAGES` on, the weekly job writes `thumbs/pages.json` with the page count of each PDF. Multiply each leaflet's "code shown" count by its pages for pages not printed.

## Install on a phone

Open the address once with signal, then:

- **iPhone:** in Safari, tap **Share** → **Add to Home Screen**.
- **Android:** in Chrome, tap **⋮** → **Install app** (or **Add to Home screen**).

From then on it opens from the home screen and works with no signal.

## Updating the leaflet list for everyone

Edit `leaflets.json` on GitHub (click the file, then the pencil icon). Each leaflet looks like this:

```json
{"id":"m-keratoconus","title":"Keratoconus","url":"https://moorfields.nhs.uk/mediaLocal/hlvpqvm1/keratoconus.pdf","source":"Moorfields","tag":"Cornea","kind":"condition"}
```

- `id`: any unique short code. Don't change an existing one, or staff lose their favourite for it.
- `kind`: `condition`, `surgery`, `medicines` or `visit` (sets the tab).
- `tag`: one of the subspecialties listed at the top of the app's filter.
- Change `"updated"` at the top of the file to the current date and time, e.g. `"2026-11-02T09:00"`.

### Related leaflets

When a leaflet is opened, its related leaflets appear under **Also consider** as a reminder, one tap each. They're set in `"related"` at the bottom of `leaflets.json`, from a leaflet's `id` to the ones to suggest with it:

```json
"related": {
  "m-keratoconus": ["m-corneal-cross-linking", "m-collagen-cross-linking-after-care-instructions"]
}
```

Links work one way, so add a line for each leaflet that should show suggestions.

## Changing the app itself

Edit `source/index.src.html`, then run `python3 source/build.py path/to/qrcode.js` to rebuild `index.html` in the main folder. The QR library is `qrcode-generator` 1.4.4 from npm. Upload the new `index.html` and bump `VERSION` in `sw.js`. Staff then see *A new version of the app is ready. Tap to update.* the next time they open it.

## Before rolling out to all staff

- Check with your patient information team that these are the leaflets they want used, and with IT or information governance about hosting. The app holds no patient data.
- Trusts move and update leaflets. The weekly link check emails you when one stops working; tap **Open** on any card to check one quickly.
