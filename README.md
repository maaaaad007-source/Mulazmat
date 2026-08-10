# 💼 Mulazmat

A Streamlit app for searching LinkedIn job postings by **job title**, **company**
(optional) and **country** (full alphabetical list, type-to-search).

## Quick start

```bash
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

The app opens at <http://localhost:8501>. Enter a job title, pick a country,
press **Search**. Tick **Demo mode** under **Filters** to click through the whole
UI with sample data, without touching LinkedIn.

## Layout

A single horizontal bar across the top — logo, job title, company, country,
**Search**, **Filters**, and a bookmark that switches to your saved jobs. There is
no sidebar. Everything secondary lives in the **Filters** dropdown: sort, date
posted, workplace, experience level, max results, card/table view, detail
fetching, demo mode and the geoId override.

Results are a two-up grid of cards: company logo, title, company, location, a
workplace / job-type / age strip, and the **Contact & apply** footer. Logos come
off the search results themselves, so they cost no extra requests; companies
without one get a monogram. Postings with more description than a card shows get
a **Read full description** expander, so you can read the whole posting without
opening LinkedIn. Each card has a bookmark to save it; saved jobs live in the session, so they clear when
the browser tab is closed. **Apply filters** closes the panel.

Streamlit's own header is hidden so it cannot sit on top of the **Filters**
button — delete the `[data-testid="stHeader"]` rule in `src/mulazmat/theme.py`
to bring the hamburger menu back.

## What you can search on

| Field | Notes |
| --- | --- |
| **Job title** | Required. This is what LinkedIn actually searches on. Suggests common titles as you type, and remembers your last 8 searches at the top of the list — but accepts any text, so unusual titles are typed as normal. |
| **Company** | Optional. Applied to results *after* they arrive, so editing it re-filters instantly without a new search. |
| **Country** | All 195 countries, alphabetical; the selectbox filters as you type. Leave it blank to search everywhere. |
| Date posted | Any time / 24 hours / week / month. |
| Workplace | Select all, On-site, Remote or Hybrid. |
| Experience | Internship through Executive, multi-select. |
| Sort | Most relevant or most recent. |
| Max results | 25–500. |
| View | **Cards** (default) or **Table**. Both live under **Filters**. |
| Fetch full details | Off by default. Opens each posting for its description, employment type, applicant count and apply link — one extra request per job, capped at the first N. With it on, cards gain a description snippet. |
| Detect workplace type | Off by default. Labels every result Remote or Hybrid, at the cost of two extra searches. See below. |

Results render as cards — title, company, location, the workplace / job-type /
age strip, a description once details are fetched, and a **Contact & apply**
footer — or as a sortable table. Either way there is a **Download CSV** button,
and the CSV carries every field, including ones the cards leave out such as
salary and the full posted date.

## About "contact details"

**LinkedIn job postings contain no recruiter emails and no phone numbers.** They
are not in the search results, and they are not on the guest job page. Any tool
promising them is either guessing addresses from a name-and-domain pattern or
buying them from a data broker; this app does neither.

What the **Contact & apply** footer on each card gives you is the real,
published routes to a human:

- **Apply** — the employer's own application URL when the posting has one
  (LinkedIn hides it in the page source), otherwise the LinkedIn posting.
- **Company page** — the company's LinkedIn page.
- **Profile** — when a posting names the person who posted it, a link to their
  public profile. Name and headline only; nothing is scraped beyond what
  LinkedIn shows publicly.
- **On LinkedIn** — the original posting, kept alongside an external apply link.

Cards say "No public contact links on this posting" when a posting genuinely has
none, rather than inventing something.

Most of that footer beyond the company page only appears with **Fetch full
details** switched on, since it comes from the individual job page.

## How it gets the jobs — and the honest caveats

LinkedIn has **no public jobs API**. This app reads the same endpoint LinkedIn's
own logged-out jobs page uses for infinite scroll
(`/jobs-guest/jobs/api/seeMoreJobPostings/search`) and parses the HTML cards it
returns. That is the only way to do this without a paid data provider, and it
comes with real limits you should know about before relying on it:

- **You cannot get *all* jobs.** LinkedIn stops serving results at roughly 1000
  per query no matter how you page, so the app caps at 500 by default. Narrow by
  country, date and title to get closer to full coverage of what you care about.
- **It is rate limited.** Requests are paced ~1.5s apart and retried with
  backoff, but heavy use earns an HTTP 429 ("slow down") or a temporary 403.
  Both are surfaced as plain messages in the UI rather than a stack trace.
- **The markup is not a contract.** LinkedIn can change their HTML whenever they
  like, which would break parsing. The parser is defensive and the test suite
  pins the current card structure, so a break is easy to spot and fix.
- **Terms of service.** Automated access is contrary to LinkedIn's ToS. This is
  built for personal, low-volume job hunting. For reliable or commercial bulk
  access, use a licensed job-board API instead.

### Country accuracy

LinkedIn resolves locations internally by a numeric `geoId`. Those ids are not
published, so `src/mulazmat/countries.py` carries a **partial, best-effort map**
for 20 common countries; everything else sends the country name as free text,
which LinkedIn resolves itself. **Filters → Advanced** always shows the `geoId`
in use and lets you override it if results for your country look wrong.

## Project layout

```
app.py                      Streamlit UI
src/mulazmat/
  cards.py                  Card markup (escaped) + the results grid
  job_titles.py             Autocomplete suggestions for the search box
  theme.py                  The stylesheet: top bar, filters panel, cards
  countries.py              Country list, geoId hints, location strings
  filters.py                Date/experience/job-type/workplace vocabularies
  linkedin.py               Guest-endpoint client, pagination, HTML parsing
  models.py                 Job and SearchQuery
  sample_data.py            Offline demo results
tests/                      Parser, card, filter and end-to-end UI tests
```

## Tests

```bash
pip install pytest
pytest
```

85 tests: HTML parsing against pinned real-world search and job-detail
fragments, query-parameter construction, the country list, card markup
(including escaping of untrusted job titles), and end-to-end runs that drive the
actual Streamlit app through `AppTest` — the top bar, the filters panel, title
suggestions, saving and unsaving jobs, and the saved-only view.

Note that the test suite deliberately makes **no network calls** — the live
endpoint is exercised by running the app, not by CI.

### A note on the filter counts

The design this UI follows showed counts beside each date and experience option
(`Past 24 hours (3,458)`). LinkedIn's guest endpoint returns no facet counts, and
there is no way to derive them without running a separate search per option, so
the options are unnumbered rather than numbered with invented figures.

### Job-title suggestions

The suggestion list in `src/mulazmat/job_titles.py` is local, not fetched.
LinkedIn's typeahead is not a public API, and a lookup per keystroke would be
slow and another way to earn a rate limit. Add or remove entries there freely —
the box accepts anything you type either way.

### Where the workplace label comes from

This one is harder than it looks. LinkedIn puts no workplace type on a search
card, and the job page's criteria list has no workplace row either — so for most
postings there is simply nothing to read, which is why the slot sat empty.

**Detect workplace type** (under Filters) solves it properly: it re-runs your
search through LinkedIn's own `f_WT` filters, once for Remote and once for
Hybrid, and labels every id that comes back. LinkedIn's filter is the
authority on this, so the answer is exact rather than inferred. The cost is two
extra paginated searches, which is why it is opt-in — on a 500-result search
that is real request volume, and a good way to meet a rate limit.

Without it, a card still says Remote or Hybrid when something else is
authoritative:

1. **Your workplace filter** — filtering to Remote means every result is remote
   by definition.
2. **The posting's schema.org block**, when **Fetch full details** is on:
   `jobLocationType: "TELECOMMUTE"` is the one place a posting states it is
   remote. Note schema.org has no on-site or hybrid value, only the remote flag.
3. **The title or location text**, when it literally says Remote or Hybrid —
   common enough that it is worth reading, e.g. "Product Designer (Remote)".

Anything else is left blank rather than guessed at.
