"""Global stylesheet for the app.

Streamlit gives us the widgets; this turns them into the designed layout —
a horizontal search bar, a filters dropdown, and bordered result cards.

Selectors lean on ``st-key-*`` classes, which Streamlit emits for any element
given a ``key``. That is far more stable than the generated ``st-emotion-*``
hashes, which change between releases.
"""

from __future__ import annotations

ACCENT = "#F76C6C"
ACCENT_DARK = "#E45252"
INK = "#2E3A46"
MUTED = "#8A94A0"
LINE = "#E3E7EB"

STYLES = f"""
<style>
:root {{
  --mz-accent: {ACCENT};
  --mz-accent-dark: {ACCENT_DARK};
  --mz-ink: {INK};
  --mz-muted: {MUTED};
  --mz-line: {LINE};
}}

/* ---- Chrome we do not want -------------------------------------------- */
[data-testid="stSidebar"], [data-testid="stSidebarCollapsedControl"] {{ display: none !important; }}
/* Streamlit's header floats over the top-right of the page and swallows clicks
   meant for the Filters button. The design supplies its own bar, so drop it.
   Delete this rule to get the hamburger/Deploy menu back. */
[data-testid="stHeader"] {{ display: none !important; }}
.block-container {{ padding-top: 1.1rem; max-width: 1400px; }}

/* ---- Top search bar ----------------------------------------------------
   Styled via the container's st-key class rather than a wrapper <div>: a div
   opened in st.markdown is closed by Streamlit before the widgets render, so
   it can never actually contain them. */
[class*="st-key-topbar"] {{
  position: sticky; top: 0; z-index: 60;
  background: #fff; border-bottom: 1px solid var(--mz-line);
  margin: -1.1rem -1rem 1.4rem; padding: .85rem 1.25rem .6rem;
}}
.mz-logo {{
  width: 42px; height: 42px; border-radius: 13px; background: var(--mz-accent);
  display: flex; align-items: center; justify-content: center;
}}
.mz-logo span {{
  width: 15px; height: 15px; border-radius: 50%;
  border: 4px solid #fff; display: block;
}}

/* Inputs in the bar: flat, grey-bordered, no focus glow. */
[class*="st-key-topbar"] [data-baseweb="input"],
[class*="st-key-topbar"] [data-baseweb="select"] > div {{
  border-radius: 6px !important; border: 1px solid var(--mz-line) !important;
  box-shadow: none !important; min-height: 46px; font-size: .95rem;
  background: #fff !important;
}}
[class*="st-key-topbar"] input {{ background: transparent !important; }}
[class*="st-key-topbar"] input::placeholder {{ color: #A9B2BC; }}

/* SEARCH + APPLY FILTERS */
[class*="st-key-search"] button, [class*="st-key-apply_filters"] button {{
  background: var(--mz-accent) !important; border: 1px solid var(--mz-accent) !important;
  color: #fff !important; border-radius: 6px; min-height: 46px;
  letter-spacing: .12em; font-size: .8rem; font-weight: 600; text-transform: uppercase;
}}
[class*="st-key-search"] button:hover, [class*="st-key-apply_filters"] button:hover {{
  background: var(--mz-accent-dark) !important; border-color: var(--mz-accent-dark) !important;
}}
[class*="st-key-apply_filters"] button {{ min-height: 42px; }}

/* Filters trigger + saved-jobs heart */
[class*="st-key-filters"] button, [class*="st-key-saved_toggle"] button {{
  border: 1px solid var(--mz-line) !important; background: #fff !important;
  border-radius: 6px; min-height: 46px; color: var(--mz-ink) !important;
  font-weight: 400; box-shadow: none !important;
}}
[class*="st-key-saved_toggle"] button {{ color: var(--mz-accent) !important; font-size: 1.15rem; }}
[data-testid="stPopoverBody"] {{ width: 26rem; max-width: 92vw; }}

/* ---- Filters panel ----------------------------------------------------- */
.mz-fgroup {{
  font-weight: 700; font-size: .95rem; color: var(--mz-ink);
  margin: .2rem 0 .1rem;
}}
.mz-fgroup::after {{
  content: ""; display: block; width: 34px; height: 2px;
  background: var(--mz-line); margin-top: .45rem;
}}

/* ---- Result cards ------------------------------------------------------ */
.mz-count {{ font-weight: 700; font-size: 1.05rem; color: var(--mz-ink); margin: .2rem 0 .9rem; }}

/* Cards fill their row so a short posting does not leave a ragged grid. */
[data-testid="stHorizontalBlock"] {{ align-items: stretch; }}
[data-testid="stColumn"] {{ display: flex; align-items: stretch; }}
[data-testid="stColumn"] > div {{ width: 100%; height: 100%; }}
/* Streamlit wraps a bordered container in a layout div that does not inherit
   the stretched height; without this the shorter card in a row stops early. */
[data-testid="stColumn"] [data-testid="stLayoutWrapper"] {{ height: 100%; }}

[class*="st-key-card_"] {{
  position: relative;
  border: 1px solid var(--mz-line) !important; border-radius: 10px !important;
  padding: 1.35rem 1.5rem 1.15rem !important; background: #fff;
  height: 100%;
}}
[class*="st-key-card_"]:hover {{ border-color: #CFD6DD !important; }}
/* Push the contact footer to the bottom edge of every card in the row. */
[class*="st-key-card_"] > div {{ height: 100%; }}

.mz-title {{
  font-size: 1.28rem; font-weight: 700; line-height: 1.3;
  margin: 0 0 .85rem; padding-right: 2rem;
}}
.mz-title a {{ color: var(--mz-ink); text-decoration: none; }}
.mz-title a:hover {{ color: var(--mz-accent); }}
.mz-sub {{ font-size: 1rem; color: var(--mz-ink); margin: 0; line-height: 1.6; }}
.mz-sub a {{ color: var(--mz-ink); text-decoration: none; }}
.mz-sub a:hover {{ color: var(--mz-accent); }}
.mz-sub--muted {{ color: #5C6874; }}

.mz-meta {{
  display: flex; justify-content: space-between; gap: 1rem;
  border-top: 1px solid var(--mz-line); border-bottom: 1px solid var(--mz-line);
  margin: 1.1rem 0 1rem; padding: .8rem 0;
  font-size: .78rem; letter-spacing: .09em; text-transform: uppercase; color: #6C7783;
}}
.mz-meta span:last-child {{ text-align: right; white-space: nowrap; }}

.mz-contact-label {{
  font-size: .72rem; letter-spacing: .12em; text-transform: uppercase;
  color: var(--mz-muted); margin: 0 0 .7rem;
}}
.mz-poster {{ font-size: .85rem; color: #5C6874; margin: 0 0 .7rem; }}
.mz-desc {{ font-size: .88rem; line-height: 1.55; color: #5C6874; margin: 0 0 .2rem; }}

.mz-links {{ display: flex; flex-wrap: wrap; gap: .6rem; }}
.mz-card-link {{
  display: inline-block; padding: .6rem 1.15rem; border-radius: 5px;
  border: 1px solid var(--mz-accent); color: var(--mz-accent) !important;
  font-size: .78rem; font-weight: 600; letter-spacing: .1em; text-transform: uppercase;
  text-decoration: none !important; white-space: nowrap;
}}
.mz-card-link:hover {{ background: rgba(247, 108, 108, .07); }}
.mz-none {{ font-size: .8rem; color: var(--mz-muted); margin: 0; }}

/* Per-card save heart: a real button (HTML cannot call back into Python),
   lifted out of the flow into the card's top-right corner. */
[class*="st-key-save_"] {{
  position: absolute; top: 1.1rem; right: 1.2rem; z-index: 2; width: auto !important;
}}
[class*="st-key-save_"] button {{
  border: none !important; background: transparent !important; box-shadow: none !important;
  color: #C4CBD2 !important; font-size: 1.35rem; padding: 0 !important;
  min-height: 0 !important; line-height: 1;
}}
[class*="st-key-save_"] button:hover {{ color: var(--mz-accent) !important; }}
[class*="st-key-save_"] button[kind="primary"] {{ color: var(--mz-accent) !important; }}

@media (max-width: 640px) {{
  .mz-meta {{ flex-direction: column; gap: .35rem; }}
  .mz-meta span:last-child {{ text-align: left; }}
}}
</style>
"""

LOGO = '<div class="mz-logo"><span></span></div>'
