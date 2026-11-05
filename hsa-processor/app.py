import json
import logging
import os
import re
from datetime import datetime, timezone

import httpx
from anthropic import Anthropic
from fastapi import FastAPI, Request
from google.oauth2 import service_account
from googleapiclient.discovery import build

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("hsa-processor")

PAPERLESS_URL = os.environ["PAPERLESS_URL"].rstrip("/")
PAPERLESS_TOKEN = os.environ["PAPERLESS_TOKEN"]
ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]
GOOGLE_SHEET_ID = os.environ["GOOGLE_SHEET_ID"]
GOOGLE_SHEET_TAB = os.environ.get("GOOGLE_SHEET_TAB", "Sheet1")
SERVICE_ACCOUNT_FILE = os.environ.get("GOOGLE_SERVICE_ACCOUNT_FILE", "/secrets/service-account.json")
PUBLIC_DOC_BASE_URL = os.environ.get("PUBLIC_DOC_BASE_URL", "https://paperless.masterbateshome.com").rstrip("/")

HSA_LOGGED_TAG_ID = int(os.environ["HSA_LOGGED_TAG_ID"])
HSA_REVIEW_TAG_ID = int(os.environ["HSA_REVIEW_TAG_ID"])

anthropic_client = Anthropic(api_key=ANTHROPIC_API_KEY)

_sheets_creds = service_account.Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE,
    scopes=["https://www.googleapis.com/auth/spreadsheets"],
)
_sheets_service = build("sheets", "v4", credentials=_sheets_creds)

app = FastAPI()

EXTRACTION_PROMPT = """You are extracting billing data from a healthcare document's OCR text for HSA (Health Savings Account) expense tracking.

Read the document text below and determine:
1. total_amount: the TOTAL amount owed/billed/paid on this document, as a plain number (no $ or commas). This should be the final balance due or total charge, not a subtotal, not an insurance-adjusted amount unless that's the actual amount the patient owes, and not a payment plan installment unless that's the only amount shown. If multiple totals appear (e.g. "Total Charges" vs "Amount You Owe"), prefer the amount the patient is responsible for paying.
2. provider: the name of the healthcare provider, clinic, hospital, or billing entity that issued this document.
3. bill_date: the date of service or the bill/statement date, in YYYY-MM-DD format. Use the most relevant single date if several appear.
4. confident: true only if you are reasonably confident in total_amount specifically. If the document is ambiguous, has multiple conflicting totals you can't resolve, or doesn't appear to be a bill/invoice/receipt at all, set this to false.
5. notes: a short (<150 char) explanation, especially if confident is false.

Respond with ONLY a JSON object, no other text, matching exactly this shape:
{"total_amount": <number or null>, "provider": <string or null>, "bill_date": <"YYYY-MM-DD" or null>, "confident": <true|false>, "notes": <string>}

DOCUMENT TEXT:
---
{content}
---
"""


def paperless_headers():
    return {"Authorization": f"Token {PAPERLESS_TOKEN}"}


def fetch_document(doc_id: int) -> dict:
    with httpx.Client(timeout=30.0) as c:
        r = c.get(f"{PAPERLESS_URL}/api/documents/{doc_id}/", headers=paperless_headers())
        if r.status_code >= 400:
            log.error("fetch_document(%s) -> %s: %s", doc_id, r.status_code, r.text[:500])
        r.raise_for_status()
        return r.json()


def extract_bill_info(content: str) -> dict:
    # Guard against absurdly long OCR text blowing up token usage/cost
    trimmed = content[:15000]
    prompt = EXTRACTION_PROMPT.replace("{content}", trimmed)
    resp = anthropic_client.messages.create(
        model="claude-sonnet-5",
        max_tokens=800,
        messages=[{"role": "user", "content": prompt}],
    )
    text = "".join(
        block.text for block in resp.content
        if getattr(block, "type", None) == "text" and block.text
    ).strip()
    # Strip markdown code fences if the model added them despite instructions
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise ValueError(f"Could not find JSON in model response: {text!r}")
    return json.loads(match.group(0))


def append_to_sheet(row: list):
    body = {"values": [row]}
    _sheets_service.spreadsheets().values().append(
        spreadsheetId=GOOGLE_SHEET_ID,
        range=f"{GOOGLE_SHEET_TAB}!A:D",
        valueInputOption="USER_ENTERED",
        insertDataOption="INSERT_ROWS",
        body=body,
    ).execute()


def set_document_tags(doc_id: int, current_tags: list[int], add: int, remove: int | None = None):
    new_tags = set(current_tags)
    new_tags.add(add)
    if remove is not None:
        new_tags.discard(remove)
    with httpx.Client(timeout=30.0) as c:
        r = c.patch(
            f"{PAPERLESS_URL}/api/documents/{doc_id}/",
            headers=paperless_headers(),
            json={"tags": list(new_tags)},
        )
        r.raise_for_status()


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/webhook")
async def webhook(request: Request):
    payload = await request.json()
    doc_id = payload.get("document_id")
    if doc_id is None:
        log.error("Webhook called without document_id: %s", payload)
        return {"status": "error", "detail": "missing document_id"}

    doc_id = int(doc_id)
    log.info("Processing document %s", doc_id)

    try:
        doc = fetch_document(doc_id)
        content = doc.get("content") or ""
        current_tags = doc.get("tags", [])

        if not content.strip():
            log.warning("Document %s has no OCR content; marking for review", doc_id)
            set_document_tags(doc_id, current_tags, add=HSA_REVIEW_TAG_ID)
            return {"status": "review", "detail": "no content"}

        info = extract_bill_info(content)
        log.info("Document %s extraction result: %s", doc_id, info)

        amount = info.get("total_amount")
        confident = info.get("confident", False)

        if not confident or amount is None or not isinstance(amount, (int, float)) or amount <= 0:
            log.warning("Document %s not confidently parsed: %s", doc_id, info.get("notes"))
            set_document_tags(doc_id, current_tags, add=HSA_REVIEW_TAG_ID)
            return {"status": "review", "detail": info}

        bill_date = info.get("bill_date") or datetime.now(timezone.utc).strftime("%Y-%m-%d")
        provider = info.get("provider") or "(unknown provider)"
        doc_link = f"{PUBLIC_DOC_BASE_URL}/documents/{doc_id}/details"

        append_to_sheet([bill_date, provider, amount, doc_link])
        set_document_tags(doc_id, current_tags, add=HSA_LOGGED_TAG_ID, remove=HSA_REVIEW_TAG_ID)

        log.info("Document %s logged: %s / %s / %s", doc_id, bill_date, provider, amount)
        return {"status": "logged", "amount": amount, "provider": provider, "bill_date": bill_date}

    except Exception as e:
        log.exception("Failed processing document %s: %s", doc_id, e)
        try:
            doc = fetch_document(doc_id)
            set_document_tags(doc_id, doc.get("tags", []), add=HSA_REVIEW_TAG_ID)
        except Exception:
            log.exception("Also failed to mark document %s for review", doc_id)
        return {"status": "error", "detail": str(e)}
