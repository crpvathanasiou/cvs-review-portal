Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

poetry run uvicorn cvs_review_portal.main:app --host 127.0.0.1 --port 18080 --reload
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
