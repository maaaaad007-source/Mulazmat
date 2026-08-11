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

#: Card logo edge length; kept in step with ``cards.LOGO_PX``.
LOGO_PX = 56

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
/* Streamlit Community Cloud's floating "Manage app" badge, bottom right. Its
   real class names carry a build hash, so match on the stable prefix rather
   than the whole thing. */
[data-testid="manage-app-button"],
[class*="_manageAppButton"],
[class*="_profileContainer"],
[class*="_viewerBadge"],
[class*="viewerBadge_container"],
[class*="_terminalButton"],
#MainMenu,
footer {{ display: none !important; }}
/* The badge-hiding component is a zero-height iframe; keep it out of the flow. */
[data-testid="stIFrame"][height="0"],
iframe[height="0"] {{ display: none !important; }}
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
   The padding stays after dropping the underline so the spacing is unchanged. */
[data-testid="stPopoverBody"] p.mz-fgroup {{
  font-weight: 700; font-size: .95rem; color: var(--mz-ink);
  margin: 1.5rem 0 .6rem !important;
  padding-bottom: .45rem;
}}
/* Only the panel's very first heading needs no space above it. */
[data-testid="stPopoverBody"] [data-testid="stElementContainer"]:first-child p.mz-fgroup {{
  margin-top: 0 !important;
}}
[class*="st-key-apply_filters"] {{ padding-top: 1rem; }}
[class*="st-key-apply_filters"] button {{ height: 42px; }}

/* ---- Idle state --------------------------------------------------------- */
.mz-idle {{
  display: flex; justify-content: center; align-items: center;
  padding: 3rem 1rem 4rem;
}}
.mz-idle img {{
  max-width: min(420px, 80vw); width: 100%; height: auto; border-radius: 12px;
}}

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

/* Logo left, the title/company/location block to its right. */
.mz-head {{ display: flex; gap: .85rem; align-items: flex-start; }}
.mz-head-text {{ min-width: 0; flex: 1; }}
.mz-logo-box {{
  width: {LOGO_PX}px; height: {LOGO_PX}px; min-width: {LOGO_PX}px; flex: none;
  border-radius: 9px; border: 1px solid var(--mz-line); background: #fff;
  overflow: hidden; display: flex; align-items: center; justify-content: center;
}}
.mz-logo-img {{
  width: {LOGO_PX}px !important; height: {LOGO_PX}px !important;
  max-width: {LOGO_PX}px; object-fit: contain;
}}
.mz-logo-fallback {{
  font-weight: 700; font-size: 1.3rem; color: var(--mz-muted);
}}

/* The description toggle: a plain text link, not a button. */
[class*="st-key-desc_"] button {{
  border: none !important; background: transparent !important; box-shadow: none !important;
  padding: 0 !important; min-height: 0 !important; height: auto !important;
  color: var(--mz-accent) !important; font-size: .76rem; font-weight: 600;
  letter-spacing: .09em; text-transform: uppercase;
}}
[class*="st-key-desc_"] button:hover {{ color: var(--mz-accent-dark) !important; }}
[class*="st-key-desc_"] {{ margin: -.35rem 0 .9rem; }}

/* Expanded in place — the snippet is replaced, never repeated. */
.mz-desc--full {{ max-height: 26rem; overflow-y: auto; padding-right: .5rem; }}

.mz-title {{
  font-size: 1.15rem; font-weight: 700; line-height: 1.35;
  margin: 0 0 .35rem; padding-right: 1.6rem;
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

/* ---- Write email ------------------------------------------------------- */
/* The card's own action, so it is filled rather than outlined like the links
   above it. `st-key-email_` cannot collide with the `me_email` details field —
   the underscore is on the other side of the word. */
[class*="st-key-email_"] {{ margin: .75rem 0 .1rem !important; }}
[class*="st-key-email_"] button {{
  border: 1px solid var(--mz-accent) !important; background: var(--mz-accent) !important;
  color: #fff !important; border-radius: 5px !important;
  padding: .5rem 1rem !important; min-height: 0 !important; height: auto !important;
  font-size: .72rem; font-weight: 600; letter-spacing: .11em; text-transform: uppercase;
}}
[class*="st-key-email_"] button:hover {{
  background: var(--mz-accent-dark) !important; border-color: var(--mz-accent-dark) !important;
}}
/* Open: the same button, held back so "Open in email app" leads. */
[class*="st-key-emailopen_"] button {{
  background: #fff !important; color: var(--mz-muted) !important;
  border-color: var(--mz-line) !important;
}}
[class*="st-key-emailopen_"] button:hover {{
  background: #fff !important; color: var(--mz-accent) !important;
  border-color: var(--mz-accent) !important;
}}

/* The panel is its own container so this gap does not reach the rest of the
   card — Streamlit's default 1rem between eight widgets is an ocean. */
[class*="st-key-draftbox_"] {{ gap: .45rem !important; margin-top: .9rem; }}
/* Cards are stretched to the height of their row, and a flex column with
   spare height to hand out squashes the message box and inflates whatever
   follows it. Every part of the draft keeps the size it asked for. */
[class*="st-key-draftbox_"] > * {{ flex: none !important; }}
/* The rule that stretches a card to its row also catches the copy expander,
   which is a layout wrapper in the same column. It should be its own height. */
[class*="st-key-draftbox_"] [data-testid="stLayoutWrapper"] {{ height: auto !important; }}
.mz-draft-label {{
  font-size: .7rem; letter-spacing: .13em; text-transform: uppercase;
  color: var(--mz-muted); margin: 0 0 .1rem !important;
}}
[class*="st-key-tone_"] label {{ font-size: .82rem; }}
[class*="st-key-body_"] textarea {{
  font-size: .82rem !important; line-height: 1.55; font-family: inherit;
}}
[class*="st-key-subj_"] input {{ font-weight: 600; }}
/* Both draft links read as card actions rather than Streamlit defaults.
   Keyed rather than matched on the link's `kind`, which stays "secondary"
   whatever `type=` says. */
[class*="st-key-mailto_"] a, [class*="st-key-liprofile_"] a {{
  border-radius: 5px !important; min-height: 0 !important; height: auto !important;
  padding: .55rem 1rem !important; font-size: .72rem; font-weight: 600;
  letter-spacing: .11em; text-transform: uppercase;
}}
[class*="st-key-mailto_"] a {{
  background: var(--mz-accent) !important; border: 1px solid var(--mz-accent) !important;
  color: #fff !important;
}}
[class*="st-key-mailto_"] a:hover {{
  background: var(--mz-accent-dark) !important; border-color: var(--mz-accent-dark) !important;
}}
[class*="st-key-liprofile_"] a {{
  background: #fff !important; border: 1px solid var(--mz-accent) !important;
  color: var(--mz-accent) !important;
}}
/* "Start over" is a quiet escape hatch, not a third call to action. */
[class*="st-key-regen_"] button {{
  border: none !important; background: transparent !important; box-shadow: none !important;
  padding: 0 !important; min-height: 0 !important; height: auto !important;
  color: var(--mz-muted) !important; font-size: .72rem; font-weight: 600;
  letter-spacing: .09em; text-transform: uppercase;
}}
[class*="st-key-regen_"] button:hover {{ color: var(--mz-accent) !important; }}
[class*="st-key-draftbox_"] [data-testid="stExpander"] summary {{ font-size: .78rem; }}

@media (max-width: 640px) {{
  [class*="st-key-topbar"] {{ padding-inline: 1rem; }}
  .mz-meta {{ flex-direction: column; gap: .3rem; }}
  .mz-meta span:last-child {{ text-align: left; }}
}}
</style>
"""

LOGO = '<div class="mz-logo"><span></span></div>'

def hide_cloud_badge() -> None:
    """Remove Streamlit Community Cloud's floating "Manage app" control.

    CSS alone is not enough: the badge's class names carry a build hash that
    changes between deploys, so any selector written against them rots. This
    finds it by its visible text instead, from a zero-height component iframe
    reaching into the parent document (same origin on *.streamlit.app), and
    keeps watching because the cloud re-inserts it after navigation.

    Note the badge is only shown to the app's owner while signed in — other
    visitors never see it in the first place.
    """
    import streamlit.components.v1 as components

    components.html(
        """
        <script>
        const LABELS = ["manage app", "manage this app"];

        function hideBadge() {
          const doc = window.parent && window.parent.document;
          if (!doc) return;

          doc.querySelectorAll(
            '[data-testid="manage-app-button"], [class*="_profileContainer"],' +
            '[class*="_viewerBadge"], [class*="viewerBadge_container"],' +
            '[class*="_terminalButton"], [class*="_manageAppButton"]'
          ).forEach((el) => { el.style.display = "none"; });

          // Whatever the classes are called this week, the text is the same.
          doc.querySelectorAll("a, button, span, div").forEach((el) => {
            if (el.children.length) return;
            const text = (el.textContent || "").trim().toLowerCase();
            if (!LABELS.includes(text)) return;
            const box = el.closest("div, a, button");
            if (box) box.style.display = "none";
          });
        }

        hideBadge();
        // The cloud re-inserts the badge, so keep an eye on it.
        try {
          new MutationObserver(hideBadge).observe(
            window.parent.document.body, { childList: true, subtree: true }
          );
        } catch (err) { /* different origin: the CSS rules still apply */ }
        setInterval(hideBadge, 1000);
        </script>
        """,
        height=0,
    )


#: Shown before the first search, in place of a wall of explanatory text.
IDLE_GIF_URL = (
    "https://media1.giphy.com/media/v1.Y2lkPTc5MGI3NjExZjBqdWJoYTNvajU1dGlzOXZ2"
    "ajVzMHloeDhveW43a2JwNDRmd3JsNiZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/"
    "uBRLi3E3XCFgOwRYrH/giphy.gif"
)

IDLE_GIF = f'''
<div class="mz-idle">
  <img src="{IDLE_GIF_URL}" alt="" loading="lazy">
</div>
'''

