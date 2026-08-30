#!/usr/bin/env bash
set -euo pipefail

: "${API_BASE:?API_BASE is required}"
: "${OIDC_TOKEN:?OIDC_TOKEN is required}"
: "${GITHUB_RUN_ID:?GITHUB_RUN_ID is required}"
: "${GITHUB_RUN_ATTEMPT:?GITHUB_RUN_ATTEMPT is required}"

COOKIE_JAR="$(mktemp)"
BODY_FILE="$(mktemp)"
EVIDENCE_FILE="${RUNNER_TEMP:-/tmp}/parallax-safe-deletion-evidence.json"
project_id=""
conversation_id=""
run_id=""
replacement_project_id=""
cleanup_started="0"

request_status() {
  local method="$1"
  local url="$2"
  local data_file="${3:-}"
  local args=(
    --silent --show-error
    --cookie "${COOKIE_JAR}"
    -H "X-Parallax-Session: 1"
    -X "${method}"
    -o "${BODY_FILE}"
    -w '%{http_code}'
  )
  if [[ -n "${data_file}" ]]; then
    args+=( -H "Content-Type: application/json" --data-binary "@${data_file}" )
  fi
  curl "${args[@]}" "${url}"
}

best_effort_cancel_run() {
  [[ -z "${run_id}" ]] && return 0
  local status state revision payload
  status="$(request_status GET "${API_BASE}/v1/engineering-runs/${run_id}" || true)"
  [[ "${status}" != "200" ]] && return 0
  state="$(jq -r '.state // empty' "${BODY_FILE}" 2>/dev/null || true)"
  case "${state}" in
    COMPLETE|CANCELLED|SPEC_AMENDMENT) return 0 ;;
  esac
  revision="$(jq -r '.revision // empty' "${BODY_FILE}" 2>/dev/null || true)"
  [[ -z "${revision}" ]] && return 0
  payload="$(mktemp)"
  jq -n \
    --arg operation_key "qa-safe-delete-cleanup-${GITHUB_RUN_ID}-${GITHUB_RUN_ATTEMPT}" \
    --argjson expected_revision "${revision}" \
    '{operation_key:$operation_key,expected_revision:$expected_revision}' >"${payload}"
  request_status POST "${API_BASE}/v1/engineering-runs/${run_id}/cancel" "${payload}" >/dev/null || true
  rm -f "${payload}"
}

cleanup() {
  local exit_code=$?
  [[ "${cleanup_started}" == "1" ]] && exit "${exit_code}"
  cleanup_started="1"
  set +e
  if [[ -n "${replacement_project_id}" ]]; then
    request_status DELETE "${API_BASE}/v1/projects/${replacement_project_id}" >/dev/null
  fi
  if [[ -n "${project_id}" ]]; then
    best_effort_cancel_run
    request_status DELETE "${API_BASE}/v1/projects/${project_id}" >/dev/null
  fi
  rm -f "${COOKIE_JAR}" "${BODY_FILE}"
  exit "${exit_code}"
}
trap cleanup EXIT

assert_status() {
  local actual="$1"
  local expected="$2"
  local context="$3"
  if [[ "${actual}" != "${expected}" ]]; then
    echo "${context}: expected HTTP ${expected}, got ${actual}" >&2
    cat "${BODY_FILE}" >&2 || true
    exit 1
  fi
}

run_suffix="${GITHUB_RUN_ID}-${GITHUB_RUN_ATTEMPT}"
slug="qa-safe-delete-${GITHUB_RUN_ID}-${GITHUB_RUN_ATTEMPT}"
repository_ref="github:Ryan9876/qa-safe-delete-${GITHUB_RUN_ID}-${GITHUB_RUN_ATTEMPT}"
project_name="QA Safe Deletion ${run_suffix}"

# Establish the existing bounded QA application identity. The bearer token is
# used only for this session exchange and is never written to durable output.
curl --fail-with-body --silent --show-error \
  --cookie-jar "${COOKIE_JAR}" \
  -H "Authorization: Bearer ${OIDC_TOKEN}" \
  -X POST "${API_BASE}/v1/session/qa-automation" >"${BODY_FILE}"
jq -e '.authenticated == true' "${BODY_FILE}" >/dev/null
session_role="$(jq -r '.role // "unknown"' "${BODY_FILE}")"
echo "Safe deletion smoke: authenticated bounded QA session (role=${session_role})"

project_payload="$(mktemp)"
jq -n \
  --arg name "${project_name}" \
  --arg slug "${slug}" \
  --arg description "Disposable production-only logical-deletion smoke. No external repository exists for this synthetic identity and no provider mutation is authorized." \
  --arg repository_ref "${repository_ref}" \
  '{name:$name,slug:$slug,description:$description,repository_ref:$repository_ref,delivery_mode:"source-only"}' >"${project_payload}"
status="$(request_status POST "${API_BASE}/v1/projects" "${project_payload}")"
assert_status "${status}" "201" "create disposable Project"
project_id="$(jq -r '.id' "${BODY_FILE}")"
test -n "${project_id}"
echo "Safe deletion smoke: created Project ${project_id}"

conversation_payload="$(mktemp)"
jq -n --arg project_id "${project_id}" '{mode:"code",project_id:$project_id}' >"${conversation_payload}"
status="$(request_status POST "${API_BASE}/v1/conversations" "${conversation_payload}")"
assert_status "${status}" "200" "create disposable Code conversation"
conversation_id="$(jq -r '.id' "${BODY_FILE}")"
test -n "${conversation_id}"

message_payload="$(mktemp)"
objective="This is the authorized Parallax safe-deletion production smoke for ${repository_ref}. Do not modify, create, publish to, or deploy any external repository or provider resource. The only engineering lifecycle action is to create an approved work specification, activate a protected run, prove active work blocks Project deletion, cancel that run, and then validate Parallax logical deletion and active identity reuse."
jq -n --arg content "${objective}" '{role:"user",content:$content}' >"${message_payload}"
status="$(request_status POST "${API_BASE}/v1/conversations/${conversation_id}/messages" "${message_payload}")"
assert_status "${status}" "200" "record disposable smoke objective"

status="$(request_status POST "${API_BASE}/v1/conversations/${conversation_id}/work-specifications/draft")"
assert_status "${status}" "200" "draft disposable work specification"
work_specification_id="$(jq -r '.id' "${BODY_FILE}")"
test -n "${work_specification_id}"

status="$(request_status POST "${API_BASE}/v1/work-specifications/${work_specification_id}/approve")"
assert_status "${status}" "200" "approve disposable work specification"
jq -e '.status == "APPROVED"' "${BODY_FILE}" >/dev/null

activate_payload="$(mktemp)"
jq -n \
  --arg conversation_id "${conversation_id}" \
  --arg work_specification_id "${work_specification_id}" \
  '{conversation_id:$conversation_id,work_specification_id:$work_specification_id}' >"${activate_payload}"
status="$(request_status POST "${API_BASE}/v1/engineering-runs/activate" "${activate_payload}")"
assert_status "${status}" "200" "activate protected disposable run"
run_id="$(jq -r '.id' "${BODY_FILE}")"
revision="$(jq -r '.revision' "${BODY_FILE}")"
state="$(jq -r '.state' "${BODY_FILE}")"
test "${state}" = "PLAN"
echo "Safe deletion smoke: protected run ${run_id} activated at PLAN revision ${revision}"

# A non-terminal protected run must block Project deletion and leave the Project active.
status="$(request_status DELETE "${API_BASE}/v1/projects/${project_id}")"
assert_status "${status}" "409" "active engineering run deletion guard"
jq -e '.detail | strings | contains("active engineering work")' "${BODY_FILE}" >/dev/null
status="$(request_status GET "${API_BASE}/v1/projects/${project_id}")"
assert_status "${status}" "200" "Project remains active after blocked delete"
echo "Safe deletion smoke: active-run guard returned 409 without mutation"

cancel_payload="$(mktemp)"
jq -n \
  --arg operation_key "qa-safe-delete-cancel-${run_suffix}" \
  --argjson expected_revision "${revision}" \
  '{operation_key:$operation_key,expected_revision:$expected_revision}' >"${cancel_payload}"
status="$(request_status POST "${API_BASE}/v1/engineering-runs/${run_id}/cancel" "${cancel_payload}")"
assert_status "${status}" "200" "cancel disposable protected run"
jq -e '.run.state == "CANCELLED"' "${BODY_FILE}" >/dev/null
cancelled_revision="$(jq -r '.run.revision' "${BODY_FILE}")"
echo "Safe deletion smoke: run cancelled at revision ${cancelled_revision}"

# Terminal protected work now permits logical Project deletion.
status="$(request_status DELETE "${API_BASE}/v1/projects/${project_id}")"
assert_status "${status}" "204" "delete terminal disposable Project"

status="$(request_status GET "${API_BASE}/v1/projects/${project_id}")"
assert_status "${status}" "404" "deleted Project hidden from direct active read"
status="$(request_status GET "${API_BASE}/v1/projects")"
assert_status "${status}" "200" "list active Projects after deletion"
if jq -e --arg id "${project_id}" '.[] | select(.id == $id)' "${BODY_FILE}" >/dev/null; then
  echo "Deleted Project remained in active Project list" >&2
  exit 1
fi

status="$(request_status GET "${API_BASE}/v1/conversations/${conversation_id}")"
assert_status "${status}" "404" "bound conversation hidden after Project deletion"
status="$(request_status GET "${API_BASE}/v1/conversations")"
assert_status "${status}" "200" "list active conversations after Project deletion"
if jq -e --arg id "${conversation_id}" '.[] | select(.id == $id)' "${BODY_FILE}" >/dev/null; then
  echo "Deleted Project conversation remained in active conversation list" >&2
  exit 1
fi
echo "Safe deletion smoke: deleted Project and bound conversation are absent from active reads"

# Recreate the exact active uniqueness identities. This is production evidence
# that deletion is logical and active-row scoped rather than an immutable tombstone
# that permanently consumes user-visible Project identity.
status="$(request_status POST "${API_BASE}/v1/projects" "${project_payload}")"
assert_status "${status}" "201" "reuse deleted Project slug/repository identity"
replacement_project_id="$(jq -r '.id' "${BODY_FILE}")"
test -n "${replacement_project_id}"
if [[ "${replacement_project_id}" == "${project_id}" ]]; then
  echo "Replacement Project unexpectedly reused the deleted Project row identity" >&2
  exit 1
fi
echo "Safe deletion smoke: active slug/repository identity reuse accepted as new Project ${replacement_project_id}"

status="$(request_status DELETE "${API_BASE}/v1/projects/${replacement_project_id}")"
assert_status "${status}" "204" "delete replacement disposable Project"
status="$(request_status GET "${API_BASE}/v1/projects/${replacement_project_id}")"
assert_status "${status}" "404" "replacement Project cleanup"

jq -n \
  --arg project_id "${project_id}" \
  --arg conversation_id "${conversation_id}" \
  --arg run_id "${run_id}" \
  --arg work_specification_id "${work_specification_id}" \
  --arg replacement_project_id "${replacement_project_id}" \
  --arg repository_ref "${repository_ref}" \
  --arg slug "${slug}" \
  --argjson cancelled_revision "${cancelled_revision}" \
  '{
    outcome:"PASS",
    project_id:$project_id,
    conversation_id:$conversation_id,
    engineering_run_id:$run_id,
    work_specification_id:$work_specification_id,
    cancelled_revision:$cancelled_revision,
    replacement_project_id:$replacement_project_id,
    repository_ref:$repository_ref,
    slug:$slug,
    active_run_delete_status:409,
    terminal_project_delete_status:204,
    deleted_project_read_status:404,
    deleted_conversation_read_status:404,
    active_identity_reuse_status:201,
    replacement_cleanup_status:204,
    external_provider_mutation_authorized:false,
    external_provider_resource_created:false,
    external_provider_resource_deleted:false
  }' | tee "${EVIDENCE_FILE}"

echo "Safe deletion production smoke PASSED"

rm -f \
  "${project_payload}" \
  "${conversation_payload}" \
  "${message_payload}" \
  "${activate_payload}" \
  "${cancel_payload}"

# Successful path has already deleted every active fixture. Prevent the EXIT trap
# from issuing redundant cleanup operations, while still removing temporary files.
project_id=""
replacement_project_id=""
run_id=""
