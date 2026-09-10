# SeaTable API Reading

Use this reference for a private SeaTable deployment. The external-app URL identifies the app, not necessarily the base or table. Derive the deployment origin from `WEEKLY_REPORT_URL`, then discover the base and table at runtime instead of guessing names.

## Credentials

Prefer a Fish universal variable, or use a local ignored file:

```fish
set -Ux SEATABLE_API_TOKEN (string trim < token.txt)
set -Ux WEEKLY_REPORT_URL "https://inner-table.example.com/external-apps/<uuid>/?page_id=<page-id>"
```

Load the token without printing it:

```bash
TOKEN=$(tr -d '\r\n' < "$SEATABLE_API_TOKEN_FILE")
test -n "$TOKEN"
```

`SEATABLE_API_TOKEN` may be used instead. Never commit either value or include it in command output.

## Resolve the External App

The verified deployment exchanges the API token at the SeaTable web API root, without `/api-gateway`. Derive the origin without printing the token:

```bash
ORIGIN=$(python3 -c 'import os, urllib.parse; u=urllib.parse.urlsplit(os.environ["WEEKLY_REPORT_URL"]); print(f"{u.scheme}://{u.netloc}")')
curl --fail-with-body -sS \
  -H "Authorization: Bearer $TOKEN" \
  "$ORIGIN/api/v2.1/dtable/app-access-token/" \
  > /tmp/weekly-report-base-token.json
```

The verified base is named `周报`. Read `access_token`, `dtable_uuid`, and `dtable_server` from the response at runtime. Do not print or persist `access_token` beyond a temporary file.

## Discover and Read

Call the verified dtable-server v1 endpoints with the resolved base UUID:

```bash
BASE_TOKEN='...resolved at runtime...'
BASE_UUID='...resolved at runtime...'
BASE_API="$ORIGIN/dtable-server"

curl --fail-with-body -sS \
  -H "Authorization: Bearer $BASE_TOKEN" \
  "$BASE_API/api/v1/dtables/$BASE_UUID/metadata/"
```

Find the table containing fields such as `日期`, `本周进展`, `下周计划`, `风险`, and `填写人`. Then list rows with the table name URL-encoded, applying a date/person filter client-side if the deployment does not support SQL queries:

```bash
curl --fail-with-body -sS \
  -H "Authorization: Bearer $BASE_TOKEN" \
  --get --data-urlencode "table_name=周报" \
  "$BASE_API/api/v1/dtables/$BASE_UUID/rows/"
```

The `周报` table includes `名称`, `日期`, `本周进展`, `下周计划`, `风险`, `填写人名`, and `填写人`. For a monthly summary, filter by `填写人名` and the `YYYY-MM` date prefix, then sort by `日期`. Older rows may have `填写人名` empty; match the person from `名称` only when the row title follows `YYYY-MM-DD-姓名`.

Read all matching weekly rows before generating content. Preserve Slate JSON values as structured data; only convert them to plain text for deduplication and summaries. API reads do not replace post-write browser verification.

## Safety

- Do not commit `token.txt`; repository `.gitignore` includes it.
- Do not place tokens in `WEEKLY_REPORT_URL`, skill documentation, screenshots, or report fields.
- Redact `Authorization` headers and token-shaped values from diagnostics.
- If API discovery returns `401`, stop and request a valid token; do not fall back to guessing endpoints or tables.
