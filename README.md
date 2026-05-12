# ON24 URL Converter

A Streamlit tool for converting between ON24 event URLs and Customer Verified registration URLs. Direction is detected automatically from the input, and any mix of both URL types can be processed in a single batch.

## URL Formats

ON24 event URLs follow the pattern `https://event.on24.com/wcc/r/{eventId}/{accessToken}`, where the access token is a hash unique to each event. Customer Verified registration URLs follow the pattern `https://webinar.customer.swi.siemens.com/webinar/register?eid={eventId}`. Bare numeric event IDs are also accepted as input.

## Conversion Directions

**ON24 → Customer Verified:** Extracts the event ID from the ON24 URL and constructs the corresponding Customer Verified link. No API credentials are required for this direction.

**Customer Verified → ON24:** Extracts the event ID from the Customer Verified URL, then queries the ON24 API to retrieve the full event record. The `audienceurl` field in the event record contains the complete ON24 audience URL including the access token hash, which cannot be reconstructed from the event ID alone.

Multiple URLs of either type can be pasted together — the tool detects direction per line and processes them in a single run. The results table shows the input, extracted event ID, direction, converted output URL, and a status for each row. Converted URLs are also displayed in a copy-ready block with a plain text download option.

## Setup

Clone the repository, create a virtual environment, and install dependencies.

```
pip install -r requirements.txt
```

Copy `.env.example` to `.env` and fill in your ON24 credentials. These are only required for Customer Verified → ON24 conversions; the tool will work without them for the ON24 → Customer Verified direction.

```
streamlit run app.py
```

## Credentials

`ON24_CLIENT_ID`, `ON24_TOKEN_KEY`, and `ON24_TOKEN_SECRET` must be set in `.env` to enable Customer Verified → ON24 lookups. Credentials can be copied from any other ON24 project in this workspace. If credentials are absent, affected rows show a warning and unaffected rows convert normally.
