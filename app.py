"""
ON24 ↔ Customer Verified URL Converter

Bidirectional:
  - ON24 event URLs / bare IDs  →  Customer Verified URLs  (no API needed)
  - Customer Verified URLs       →  ON24 audience URLs      (ON24 API fetch)

Usage:
  streamlit run app.py
"""

import os
import re
import requests
import streamlit as st
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

CLIENT_ID    = os.getenv("ON24_CLIENT_ID")
TOKEN_KEY    = os.getenv("ON24_TOKEN_KEY")
TOKEN_SECRET = os.getenv("ON24_TOKEN_SECRET")

ON24_API_BASE          = "https://api.on24.com"
CUSTOMER_VERIFIED_BASE = "https://webinar.customer.swi.siemens.com/webinar/register"


# ── Helpers ────────────────────────────────────────────────────────────────────

def extract_event_id(raw: str) -> str | None:
    raw = raw.strip()
    if not raw:
        return None
    m = re.search(r"/r/(\d+)", raw)          # ON24 URL: /r/{id}/...
    if m:
        return m.group(1)
    m = re.search(r"[?&]eid=(\d+)", raw)     # Customer Verified: ?eid={id}
    if m:
        return m.group(1)
    if re.match(r"^\d+$", raw):              # bare numeric ID
        return raw
    return None


def is_customer_verified(raw: str) -> bool:
    return "webinar.customer.swi.siemens.com" in raw


def to_customer_verified_url(event_id: str) -> str:
    return f"{CUSTOMER_VERIFIED_BASE}?eid={event_id}"


def fetch_on24_audience_url(event_id: str) -> str:
    """Fetch the full ON24 audience URL (with hash) from the API."""
    r = requests.get(
        f"{ON24_API_BASE}/v2/client/{CLIENT_ID}/event/{event_id}",
        headers={
            "accessTokenKey": TOKEN_KEY,
            "accessTokenSecret": TOKEN_SECRET,
            "accept": "application/json",
        },
        timeout=15,
    )
    r.raise_for_status()
    data = r.json()
    event = data.get("event", data)
    return event.get("audienceurl", "")


# ── Conversion logic ───────────────────────────────────────────────────────────

def convert_inputs(lines: list[str]) -> list[dict]:
    rows = []
    for line in lines:
        eid = extract_event_id(line)
        direction = "CV → ON24" if is_customer_verified(line) else "ON24 → CV"
        rows.append({
            "input":     line,
            "eid":       eid,
            "direction": direction,
            "needs_api": is_customer_verified(line) and eid is not None,
        })
    return rows


def resolve_rows(rows: list[dict]) -> list[dict]:
    """Add 'output' and 'status' to each row, making API calls where needed."""
    results = []
    api_available = all([CLIENT_ID, TOKEN_KEY, TOKEN_SECRET])

    for r in rows:
        eid       = r["eid"]
        needs_api = r["needs_api"]

        if eid is None:
            results.append({**r, "output": "", "status": "⚠️ Could not parse ID"})
            continue

        if needs_api:
            if not api_available:
                results.append({
                    **r,
                    "output": "",
                    "status": "⚠️ ON24 credentials missing — cannot fetch audience URL",
                })
                continue
            try:
                audience_url = fetch_on24_audience_url(eid)
                if audience_url:
                    results.append({**r, "output": audience_url, "status": "✅"})
                else:
                    results.append({**r, "output": "", "status": "⚠️ audienceurl empty in API response"})
            except requests.HTTPError as e:
                results.append({
                    **r,
                    "output": "",
                    "status": f"❌ API {e.response.status_code}: {e.response.text[:120]}",
                })
            except Exception as e:
                results.append({**r, "output": "", "status": f"❌ {e}"})
        else:
            results.append({**r, "output": to_customer_verified_url(eid), "status": "✅"})

    return results


# ── Page config ────────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="ON24 ↔ Customer Verified URL Converter",
    page_icon="🔗",
    layout="centered",
)

st.title("🔗 ON24 ↔ Customer Verified URL Converter")
st.markdown(
    "Paste URLs one per line. Direction is detected automatically:\n\n"
    "- **ON24 event URLs** or bare event IDs → Customer Verified registration URLs\n"
    "- **Customer Verified URLs** → ON24 audience URLs (requires ON24 API credentials)"
)

if not all([CLIENT_ID, TOKEN_KEY, TOKEN_SECRET]):
    st.info(
        "ON24 credentials not configured — Customer Verified → ON24 conversions will be unavailable. "
        "Add `ON24_CLIENT_ID`, `ON24_TOKEN_KEY`, and `ON24_TOKEN_SECRET` to a `.env` file to enable them.",
        icon="ℹ️",
    )

# ── Input ──────────────────────────────────────────────────────────────────────

input_text = st.text_area(
    "Event URLs or IDs (one per line)",
    height=200,
    placeholder=(
        "https://event.on24.com/wcc/r/5341619/B80B44DB4BE841647539A6B3B748B1B2\n"
        "https://webinar.customer.swi.siemens.com/webinar/register?eid=5324468\n"
        "5123456"
    ),
)

if st.button("Convert", type="primary", use_container_width=True):
    lines = [l.strip() for l in input_text.splitlines() if l.strip()]
    if not lines:
        st.warning("Paste at least one URL or event ID.")
        st.stop()

    parsed = convert_inputs(lines)
    n_api  = sum(1 for r in parsed if r["needs_api"])

    with st.spinner(f"Converting{f' (fetching {n_api} event(s) from ON24 API)' if n_api else ''}…"):
        results = resolve_rows(parsed)

    n_ok  = sum(1 for r in results if r["status"] == "✅")
    n_err = len(results) - n_ok

    summary = f"{n_ok} converted"
    if n_err:
        summary += f", {n_err} failed"
    st.subheader(f"Results — {summary}")

    display_df = pd.DataFrame([
        {
            "Input":     r["input"],
            "Event ID":  r["eid"] or "⚠️ Not found",
            "Direction": r["direction"],
            "Output URL": r["output"],
            "Status":    r["status"],
        }
        for r in results
    ])
    st.dataframe(display_df, use_container_width=True, hide_index=True)

    ok_urls = [r["output"] for r in results if r["status"] == "✅"]
    if ok_urls:
        st.subheader("Converted URLs")
        st.code("\n".join(ok_urls), language=None)
        st.download_button(
            "⬇️ Download as TXT",
            data="\n".join(ok_urls),
            file_name="converted_urls.txt",
            mime="text/plain",
        )
