#!/usr/bin/env bash

set -euo pipefail

usage() {
  cat <<'EOF'
Usage: deployment-smoke.sh --api-origin URL --frontend-origin URL

Required environment variables:
  SMOKE_TEST_EMAIL
  SMOKE_TEST_PASSWORD
EOF
}

api_origin="${API_ORIGIN:-}"
frontend_origin="${FRONTEND_ORIGIN:-}"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --api-origin)
      api_origin="${2:-}"
      shift 2
      ;;
    --frontend-origin)
      frontend_origin="${2:-}"
      shift 2
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    *)
      usage >&2
      exit 2
      ;;
  esac
done

for required in api_origin frontend_origin SMOKE_TEST_EMAIL SMOKE_TEST_PASSWORD; do
  if [[ -z "${!required:-}" ]]; then
    echo "Missing required deployment smoke-test configuration: $required" >&2
    exit 2
  fi
done

api_origin="${api_origin%/}"
frontend_origin="${frontend_origin%/}"

if [[ "$api_origin" != https://* || "$frontend_origin" != https://* ]]; then
  echo "Deployment smoke tests require HTTPS API and frontend origins." >&2
  exit 2
fi

cookie_jar="$(mktemp)"
trap 'rm -f "$cookie_jar"' EXIT

curl_request() {
  curl \
    --fail-with-body \
    --silent \
    --show-error \
    --retry 8 \
    --retry-all-errors \
    --retry-delay 5 \
    --connect-timeout 10 \
    --max-time 30 \
    "$@"
}

health_response="$(curl_request "$api_origin/health")"
jq -e '.status == "ok" and (.service | type == "string")' >/dev/null <<<"$health_response"
echo "API health smoke test passed."

sign_in_payload="$(jq -cn --arg email "$SMOKE_TEST_EMAIL" --arg password "$SMOKE_TEST_PASSWORD" '{email: $email, password: $password, callbackURL: "/dashboard"}')"
curl_request \
  --request POST \
  --header 'Content-Type: application/json' \
  --header "Origin: $frontend_origin" \
  --data "$sign_in_payload" \
  --cookie-jar "$cookie_jar" \
  "$frontend_origin/api/auth/sign-in/email" >/dev/null

session_response="$(curl_request \
  --header "Origin: $frontend_origin" \
  --cookie "$cookie_jar" \
  "$frontend_origin/api/auth/get-session")"
jq -e --arg email "$SMOKE_TEST_EMAIL" '.user.email == $email' >/dev/null <<<"$session_response"
echo "Authentication smoke test passed."

dashboard_page="$(curl_request --cookie "$cookie_jar" "$frontend_origin/dashboard")"
grep -Fq 'AI Garmin Coach' <<<"$dashboard_page"

overview_response="$(curl_request \
  --header "Origin: $frontend_origin" \
  --cookie "$cookie_jar" \
  "$api_origin/dashboard/overview")"
jq -e '
  .sync.has_demo_data == true and
  .activity.activity_count_7d > 0 and
  .recovery.metric_date != null and
  .sleep.sleep_date != null and
  .latest_insight != null
' >/dev/null <<<"$overview_response"
echo "Authenticated demo dashboard smoke test passed."
