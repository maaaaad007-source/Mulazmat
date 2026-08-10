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
press **Search**. Tick **Demo mode** in the sidebar to click through the whole
UI with sample data, without touching LinkedIn.

## What you can search on

| Field | Notes |
| --- | --- |
| **Job title** | Required. This is what LinkedIn actually searches on. |
| **Company** | Optional. Applied to results *after* they arrive, so editing it re-filters instantly without a new search. |
| **Country** | All 195 countries, alphabetical; the selectbox filters as you type. "Anywhere" skips the location filter. |
| City / region | Optional, narrows within the country. |
| Date posted | Any time / 24 hours / week / month. |
| Workplace | On-site, Remote, Hybrid. |
| Job type | Full-time, Part-time, Contract, Temporary, Internship, Volunteer, Other. |
| Experience | Internship through Executive. |
| Sort | Most relevant or most recent. |
| Max results | 25–500. |

Results render as a sortable table with clickable links, plus a **Download CSV**
button.

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
which LinkedIn resolves itself. The sidebar's **Advanced** expander always shows
the `geoId` in use and lets you override it if results for your country look
wrong.

## Project layout

```
app.py                      Streamlit UI
src/mulazmat/
  countries.py              Country list, geoId hints, location strings
  filters.py                Date/experience/job-type/workplace vocabularies
  linkedin.py               Guest-endpoint client, pagination, HTML parsing
  models.py                 Job and SearchQuery
  sample_data.py            Offline demo results
tests/                      Parser, filter and end-to-end UI tests
```

## Tests

```bash
pip install pytest
pytest
```

21 tests: HTML-parsing against a pinned real-world card fragment, query-parameter
construction, the country list, and end-to-end runs that drive the actual
Streamlit app through `AppTest` in demo mode.

Note that the test suite deliberately makes **no network calls** — the live
endpoint is exercised by running the app, not by CI.
