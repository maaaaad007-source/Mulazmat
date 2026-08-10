"""Global stylesheet for the app.

Streamlit gives us the widgets; this turns them into the designed layout —
a horizontal search bar, a filters dropdown, and bordered result cards.

Selectors lean on ``st-key-*`` classes, which Streamlit emits for any element
given a ``key``. That is far more stable than the generated ``st-emotion-*``
hashes, which change between releases.
"""

from __future__ import annotations

ACCENT = "#E8746E"
ACCENT_DARK = "#D65E58"
INK = "#2E3A46"
MUTED = "#8A94A0"
LINE = "#E3E7EB"

#: Streamlit's ``.block-container`` geometry. The sticky bar is full-bleed, so
#: it needs these to line its contents back up with the cards below it.
CONTENT_WIDTH = "1400px"
CONTENT_PAD = "5rem"

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
.block-container {{ padding-top: 0 !important; max-width: 1400px; }}

/* ---- Top search bar ----------------------------------------------------
   Styled via the container's st-key class rather than a wrapper <div>: a div
   opened in st.markdown is closed by Streamlit before the widgets render, so
   it can never actually contain them.

   Full-bleed so the rule under the bar spans the window, with padding that
   lines the controls back up with the page container. z-index stays low
   enough that the Filters popover opens over the bar, not under it. */
[class*="st-key-topbar"] {{
  position: sticky; top: 0; z-index: 5;
  padding-block: .75rem; margin-bottom: 1.6rem;
}}
/* Streamlit forces the container's width, so the bar cannot be stretched to
   the window itself. This backdrop paints the white band and its rule edge to
   edge behind the controls, which stay aligned with the cards below. */
[class*="st-key-topbar"]::before {{
  content: ""; position: absolute; top: 0; bottom: 0; left: 50%;
  transform: translateX(-50%); width: 100vw; z-index: -1;
  background: #fff; border-bottom: 1px solid var(--mz-line);
}}
[class*="st-key-topbar"] [data-testid="stHorizontalBlock"] {{ align-items: center; }}
[class*="st-key-topbar"] [data-testid="stElementContainer"] {{ margin: 0; }}

/* Streamlit sizes a markdown block to one line of text (28px), so the logo
   overflowed it and hung below the other controls. Pin the wrapper to the
   control height and centre the mark inside it. */
[class*="st-key-topbar"] [data-testid="stMarkdown"],
[class*="st-key-topbar"] [data-testid="stMarkdown"] > div,
[class*="st-key-topbar"] [data-testid="stMarkdownContainer"] {{
  height: 46px !important; display: flex; align-items: center;
  /* Streamlit hangs a -16px bottom margin on this, which drags the centred
     logo 8px below the rest of the row. */
  margin-bottom: 0 !important;
}}
.mz-logo {{
  width: 46px; height: 46px; border-radius: 14px; background: var(--mz-accent);
  display: flex; align-items: center; justify-content: center; flex: none;
}}
.mz-logo span {{
  width: 14px; height: 14px; border-radius: 50%;
  border: 4px solid #fff; display: block;
}}

/* Every control in the bar is 46px tall on a shared baseline.

   The height/background must land on the widgets' own inner elements —
   stTextInputRootElement for a text input, the select's control div — because
   the outer wrappers are transparent and size to their contents. Note the
   button rule is scoped to our three buttons: a bare `button` selector also
   catches the selectbox's chevron and stretches it. */
[class*="st-key-topbar"] [data-testid="stTextInputRootElement"],
[class*="st-key-topbar"] [data-testid="stSelectbox"] > div > div,
[class*="st-key-topbar"] [data-baseweb="base-input"],
[class*="st-key-topbar"] [data-baseweb="select"] > div,
[class*="st-key-topbar"] [data-testid="stPopoverButton"],
[class*="st-key-search"] button,
[class*="st-key-saved_toggle"] button {{
  height: 46px !important; min-height: 46px !important;
  border-radius: 7px !important; box-shadow: none !important;
}}
[class*="st-key-topbar"] [data-testid="stTextInputRootElement"],
[class*="st-key-topbar"] [data-testid="stSelectbox"] > div > div,
[class*="st-key-topbar"] [data-baseweb="base-input"],
[class*="st-key-topbar"] [data-baseweb="select"] > div {{
  border: 1px solid var(--mz-line) !important; background: #fff !important;
  font-size: .95rem;
}}
[class*="st-key-topbar"] input {{
  height: 44px !important; background: transparent !important; font-size: .95rem;
}}
[class*="st-key-topbar"] input::placeholder {{ color: #A9B2BC; }}
/* The select's own dropdown arrow must keep its natural size. */
[class*="st-key-topbar"] [data-testid="stSelectbox"] button {{
  height: auto !important; min-height: 0 !important;
}}
/* Job title is a combobox so it can suggest titles, but it should still read
   as the plain search box the design calls for — no dropdown arrow. */
[class*="st-key-title"] [data-testid="stSelectbox"] button {{ display: none; }}

/* SEARCH + APPLY FILTERS */
[class*="st-key-search"] button, [class*="st-key-apply_filters"] button {{
  background: var(--mz-accent) !important; border: 1px solid var(--mz-accent) !important;
  color: #fff !important; letter-spacing: .14em; font-size: .78rem;
  font-weight: 600; text-transform: uppercase;
}}
[class*="st-key-search"] button:hover, [class*="st-key-apply_filters"] button:hover {{
  background: var(--mz-accent-dark) !important; border-color: var(--mz-accent-dark) !important;
}}

/* Filters trigger + saved-jobs toggle */
[class*="st-key-filters"] button, [class*="st-key-saved_toggle"] button {{
  border: 1px solid var(--mz-line) !important; background: #fff !important;
  color: var(--mz-ink) !important; font-weight: 400;
}}
[class*="st-key-saved_toggle"] button {{
  color: var(--mz-accent) !important; padding: 0 !important;
  justify-content: center;
}}
[class*="st-key-saved_toggle"] button[kind="primary"] {{
  background: var(--mz-accent) !important; color: #fff !important;
  border-color: var(--mz-accent) !important;
}}

/* ---- Filters panel ----------------------------------------------------- */
[data-testid="stPopoverBody"] {{
  width: 24rem; max-width: 92vw; padding: 1.1rem 1.25rem .9rem !important;
}}
/* Streamlit's default 1rem gap between every widget makes the panel far taller
   than it needs to be; tighten it and let the group headings do the spacing. */
[data-testid="stPopoverBody"] [data-testid="stVerticalBlock"] {{ gap: .3rem; }}
[data-testid="stPopoverBody"] [data-testid="stCheckbox"],
[data-testid="stPopoverBody"] [data-testid="stRadio"] {{ margin: 0; }}
[data-testid="stPopoverBody"] [data-testid="stRadio"] label {{ padding: .1rem 0; }}
[data-testid="stPopoverBody"] [data-testid="stCheckbox"] label {{ padding: .12rem 0; }}
[data-testid="stPopoverBody"] [data-testid="stSlider"] {{ padding: 0 .3rem; }}

/* Note `p.mz-fgroup`, not `.mz-fgroup`: Streamlit resets paragraph margins
   through `[data-testid="stMarkdownContainer"] p`, which outranks a bare class
   and left every group heading with the same 5px gap as the options under it.

   The underline is a background stripe rather than an ::after block, because a
   pseudo-element here escaped the paragraph's box and overlapped the option
   beneath it. */
[data-testid="stPopoverBody"] p.mz-fgroup {{
  font-weight: 700; font-size: .95rem; color: var(--mz-ink);
  margin: 1.5rem 0 .6rem !important;
  padding-bottom: .45rem;
  background-image: linear-gradient(#D8DEE4, #D8DEE4);
  background-size: 34px 2px;
  background-position: left bottom;
  background-repeat: no-repeat;
}}
/* Only the panel's very first heading needs no space above it. */
[data-testid="stPopoverBody"] [data-testid="stElementContainer"]:first-child p.mz-fgroup {{
  margin-top: 0 !important;
}}
[class*="st-key-apply_filters"] {{ padding-top: 1rem; }}
[class*="st-key-apply_filters"] button {{ height: 42px; }}

/* ---- Result cards ------------------------------------------------------ */
.mz-count {{ font-weight: 700; font-size: 1.05rem; color: var(--mz-ink); margin: 0 0 .2rem; }}

[data-testid="stHorizontalBlock"] {{ align-items: stretch; }}
[data-testid="stColumn"] {{ display: flex; align-items: stretch; }}
[data-testid="stColumn"] > div {{ width: 100%; height: 100%; }}
/* Streamlit wraps a bordered container in a layout div that does not inherit
   the stretched height; without this the shorter card in a row stops early. */
[data-testid="stColumn"] [data-testid="stLayoutWrapper"] {{ height: 100%; }}

[class*="st-key-card_"] {{
  position: relative;
  border: 1px solid var(--mz-line) !important; border-radius: 10px !important;
  padding: 1.3rem 1.4rem 1.5rem !important; background: #fff; height: 100%;
}}
[class*="st-key-card_"]:hover {{ border-color: #CFD6DD !important; }}
[class*="st-key-card_"] > div {{ height: 100%; }}
[class*="st-key-card_"] [data-testid="stElementContainer"] {{ margin: 0; }}

.mz-title {{
  font-size: 1.15rem; font-weight: 700; line-height: 1.35;
  margin: 0 0 .55rem; padding-right: 2rem;
}}
.mz-title a {{ color: var(--mz-ink); text-decoration: none; }}
.mz-title a:hover {{ color: var(--mz-accent); }}
.mz-sub {{ font-size: .95rem; color: var(--mz-ink); margin: 0; line-height: 1.5; }}
.mz-sub a {{ color: var(--mz-ink); text-decoration: none; }}
.mz-sub a:hover {{ color: var(--mz-accent); }}
.mz-sub--muted {{ color: #667180; }}

.mz-meta {{
  display: flex; justify-content: space-between; gap: 1rem;
  border-top: 1px solid var(--mz-line); border-bottom: 1px solid var(--mz-line);
  margin: .95rem 0 .9rem; padding: .6rem 0;
  font-size: .73rem; letter-spacing: .1em; text-transform: uppercase; color: #78838F;
}}
.mz-meta span:last-child {{ text-align: right; white-space: nowrap; }}
.mz-meta--single {{ justify-content: flex-start; }}

.mz-contact-label {{
  font-size: .7rem; letter-spacing: .13em; text-transform: uppercase;
  color: var(--mz-muted); margin: 0 0 .6rem;
}}
.mz-poster {{ font-size: .84rem; color: #667180; margin: 0 0 .55rem; }}
.mz-desc {{ font-size: .86rem; line-height: 1.55; color: #667180; margin: 0 0 1rem; }}

/* The gap under the buttons matches the one above "Contact & apply". */
.mz-links {{ display: flex; flex-wrap: wrap; gap: .5rem; margin-bottom: .35rem; }}
.mz-card-link {{
  display: inline-block; padding: .5rem 1rem; border-radius: 5px;
  border: 1px solid var(--mz-accent); color: var(--mz-accent) !important;
  font-size: .72rem; font-weight: 600; letter-spacing: .11em; text-transform: uppercase;
  text-decoration: none !important; white-space: nowrap; line-height: 1.35;
}}
.mz-card-link:hover {{ background: rgba(232, 116, 110, .08); }}
.mz-none {{ font-size: .8rem; color: var(--mz-muted); margin: 0; }}

/* Per-card save button: a real widget (HTML cannot call back into Python),
   lifted out of the flow into the card's top-right corner. */
[class*="st-key-save_"] {{
  position: absolute; top: 1rem; right: 1.1rem; z-index: 2; width: auto !important;
}}
[class*="st-key-save_"] button {{
  border: none !important; background: transparent !important; box-shadow: none !important;
  color: #C4CBD2 !important; padding: 0 !important; min-height: 0 !important;
  height: auto !important; line-height: 1;
}}
[class*="st-key-save_"] button:hover {{ color: var(--mz-accent) !important; }}
[class*="st-key-save_"] button[kind="primary"] {{
  background: transparent !important; color: var(--mz-accent) !important;
}}

@media (max-width: 640px) {{
  [class*="st-key-topbar"] {{ padding-inline: 1rem; }}
  .mz-meta {{ flex-direction: column; gap: .3rem; }}
  .mz-meta span:last-child {{ text-align: left; }}
}}
</style>
"""

LOGO = '<div class="mz-logo"><span></span></div>'
