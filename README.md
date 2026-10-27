# Leaflet QR

A phone app for eye clinic staff. Tap a condition or procedure and it shows a QR code; the patient scans it with their phone camera to open the patient information leaflet. 

- 183 leaflets from Moorfields Eye Hospital (public pages, as of 9 October 2026)
- Works offline once installed. The patient's phone still needs signal or Wi-Fi to open the leaflet.
- Favourites, most-used and staff's own extra leaflets are saved on each phone. Nothing is sent anywhere.
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

## Feedback

A small **Feedback** link at the top of the home screen opens a Google Form where staff can report a problem or suggest an improvement. Google emails you each new response (Responses tab → ⋮ → Get email notifications for new responses).

The form's link is stored in `leaflets.json` as `"reportForm"`. To use a different form, replace that link; to hide the link, set it to `""`.

## Pilot data (off until the pilot starts)

Everything that collects data is in `pilot.js`. Nothing is sent, and staff aren't asked anything, until a GoatCounter code is added.

**Switching it on.** Create a free site at goatcounter.com (cookie-free, no personal data). Put its code (the `xxx` in `xxx.goatcounter.com`) into `leaflets.json` as `"statsCode": "xxx"`. Phones pick this up the next time they open the app with signal. Agree it with information governance first and tell staff it's on.

**What staff see.** The first time the app opens with the pilot on, it asks for their role and the area they mainly work in. They can change this later from the link at the bottom of the home screen, which also says what is recorded. The lists are in `leaflets.json` under `"pilot"`:

- `"roles"` and `"areas"`: edit freely. Changing a label starts a new group in the report.
- `"sites"`: leave empty for the single-site pilot. Add sites (e.g. `["City Road", "St George's", "Croydon"]`) when it spreads and staff are asked for their site too.
- `"surveyForm"`: link to a form where staff can leave their NHS email for pilot surveys. Emails go to that form only, never into the app's counts.

**What is counted** (each with role, area, local date and time, whether the phone had signal, and a random code for the phone):
installed to home screen; app opened (or returned to after 15 minutes); role and area chosen; QR code shown (which leaflet); code shown from "Also consider"; leaflet viewed on the staff phone; search that found nothing (the words typed are never sent); favourite added; app shared; feedback form opened. GoatCounter adds browser, phone system, screen size and country.

**Never recorded:** names, email addresses, search words, or anything about patients. The random phone code lets the report count active phones and returning users without knowing whose phone it is; mention it in the DPIA screening.

**Counts made with no signal** wait on the phone and are sent later with the time they happened.

**Reports.** In GoatCounter: Settings → Export → Start export; GoatCounter emails a CSV. Then run `python3 source/pilot_report.py export.csv` for `pilot-report.html` (summary, by week with returning phones, by role, by area, by hour and weekday, most-used and never-used leaflets, phone systems) and `pilot-events.csv` (one row per count, for Excel). Keep exports off GitHub: the repository is public. Both report files are ignored by git.

**Not collected by the app** (needs separate steps in the pilot): whether patients actually scanned the code, patient views, paper use before the pilot, and staff time. It counts codes **shown**, not codes **scanned**.

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

Edit `source/index.src.html`, then run `python3 source/build.py path/to/qrcode.js` to rebuild `index.html`. The QR library is `qrcode-generator` 1.4.4 from npm. Upload the new `index.html` and bump `VERSION` in `sw.js`. Staff then see *A new version of the app is ready. Tap to update.* the next time they open it.

## Before rolling out to all staff

- Check with your patient information team that these are the leaflets they want used, and with IT or information governance about hosting. The app holds no patient data.
- Trusts move and update leaflets. The weekly link check emails you when one stops working; tap **Open** on any card to check one quickly.
