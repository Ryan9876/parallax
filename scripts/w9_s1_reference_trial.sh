#!/usr/bin/env bash
set -euo pipefail

API_BASE="${API_BASE:-https://parallax-api-tan.vercel.app}"
FIXTURE="benchmarks/parallax-engineering/real-world/decision-ledger-v1.json"
TARGET_REPO="github:ryan9876/sickbeard"
TARGET_GIT="https://github.com/Ryan9876/sickbeard.git"
COOKIE_JAR="/tmp/parallax.cookies"

api() {
  curl --fail-with-body --silent --show-error \
    --cookie "${COOKIE_JAR}" \
    -H "X-Parallax-Session: 1" \
    -H "Content-Type: application/json" \
    "$@"
}

record_boundary() {
  local disposition="$1"
  local project_id="${2:-}"
  local conversation_id="${3:-}"
  local spec_id="${4:-}"
  jq -n \
    --arg disposition "${disposition}" \
    --arg project_id "${project_id}" \
    --arg conversation_id "${conversation_id}" \
    --arg spec_id "${spec_id}" \
    '{w9_s1_reference_observation:{disposition:$disposition,project_id:(if $project_id=="" then null else $project_id end),conversation_id:(if $conversation_id=="" then null else $conversation_id end),work_specification_id:(if $spec_id=="" then null else $spec_id end)}}'
}

refs="$(git ls-remote "${TARGET_GIT}")"
if [ -n "${refs}" ]; then
  echo "Decision Ledger target is no longer greenfield; refusing to start trial." >&2
  exit 1
fi
echo "Greenfield target verified: ${TARGET_REPO}"

if [ -z "${OIDC_TOKEN:-}" ]; then
  echo "Missing bounded GitHub Actions OIDC token" >&2
  exit 1
fi

authenticated=0
for attempt in $(seq 1 36); do
  status="$(curl --silent --show-error \
    --output /tmp/session.json \
    --write-out '%{http_code}' \
    --cookie-jar "${COOKIE_JAR}" \
    -H "Authorization: Bearer ${OIDC_TOKEN}" \
    -X POST "${API_BASE}/v1/session/qa-automation" || true)"
  if [ "${status}" = "200" ] && jq -e '.authenticated == true' /tmp/session.json >/dev/null 2>&1; then
    authenticated=1
    break
  fi
  sleep 10
done
if [ "${authenticated}" != "1" ]; then
  echo "QA automation endpoint did not become ready" >&2
  exit 1
fi

fixture_digest="$(jq -r '.fixture_digest' "${FIXTURE}")"
started_at="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

api "${API_BASE}/v1/projects" >/tmp/projects.json
project_id="$(jq -r '.[] | select((.repository_ref // "" | ascii_downcase) == "github:ryan9876/sickbeard") | .id' /tmp/projects.json | head -n1)"
if [ -z "${project_id}" ]; then
  jq -n '{name:"Decision Ledger W9-S1 Reference",repository_ref:"github:ryan9876/sickbeard"}' >/tmp/project-create.json
  api --data-binary @/tmp/project-create.json -X POST "${API_BASE}/v1/projects" >/tmp/project.json
  project_id="$(jq -r '.id' /tmp/project.json)"
fi
echo "Canonical Project: ${project_id}"

jq -n --arg project_id "${project_id}" '{mode:"code",project_id:$project_id}' >/tmp/conversation-create.json
api --data-binary @/tmp/conversation-create.json -X POST "${API_BASE}/v1/conversations" >/tmp/conversation.json
conversation_id="$(jq -r '.id' /tmp/conversation.json)"
echo "Conversation: ${conversation_id}"

objective="$(jq -r '.objective' "${FIXTURE}")"
requirements="$(jq -r '.requirements[] | "\(.requirement_id) — \(.title): \(.outcome)"' "${FIXTURE}")"
prompt="${objective}

Acceptance requirements (preserve each requirement token exactly once in the Build plan acceptance criteria):
${requirements}

Build this as a greenfield web application in the Project repository. Choose the simplest maintainable architecture that satisfies the outcomes. Do not require an external account or third-party backend."
jq -n --arg content "${prompt}" '{content:$content,material_scope_change:false}' >/tmp/response-request.json

response_status="$(curl --silent --show-error --max-time 300 \
  --output /tmp/response.sse --write-out '%{http_code}' \
  --cookie "${COOKIE_JAR}" \
  -H "X-Parallax-Session: 1" \
  -H "Content-Type: application/json" \
  -H "Accept: text/event-stream" \
  --data-binary @/tmp/response-request.json \
  -X POST "${API_BASE}/v1/conversations/${conversation_id}/responses" || true)"
if [ "${response_status}" != "200" ]; then
  record_boundary "PRODUCT_RESPONSE_FAILED_HTTP_${response_status}" "${project_id}" "${conversation_id}"
  exit 0
fi

draft_status="$(curl --silent --show-error \
  --output /tmp/spec.json --write-out '%{http_code}' \
  --cookie "${COOKIE_JAR}" \
  -H "X-Parallax-Session: 1" \
  -H "Content-Type: application/json" \
  -X POST "${API_BASE}/v1/conversations/${conversation_id}/work-specifications/draft" || true)"
if [ "${draft_status}" != "200" ]; then
  record_boundary "SPEC_DRAFT_FAILED_HTTP_${draft_status}" "${project_id}" "${conversation_id}"
  exit 0
fi

spec_id="$(jq -r '.id' /tmp/spec.json)"
token_error=0
for token in $(seq -w 1 12 | sed 's/^/DL-/'); do
  count="$(jq --arg token "${token}" '[.acceptance_criteria[] | select(contains($token))] | length' /tmp/spec.json)"
  if [ "${count}" != "1" ]; then
    echo "Specification fidelity failure: ${token} observed ${count} times"
    token_error=1
  fi
done
if [ "${token_error}" = "1" ]; then
  record_boundary "SPEC_FIDELITY_FAILED" "${project_id}" "${conversation_id}" "${spec_id}"
  exit 0
fi

api -X POST "${API_BASE}/v1/work-specifications/${spec_id}/approve" >/tmp/approved-spec.json
revision="$(jq -r '.revision' /tmp/approved-spec.json)"
echo "Approved Work Specification: ${spec_id} revision ${revision}"

jq -n --arg conversation_id "${conversation_id}" --arg work_specification_id "${spec_id}" \
  '{conversation_id:$conversation_id,work_specification_id:$work_specification_id}' >/tmp/activate.json
api --data-binary @/tmp/activate.json -X POST "${API_BASE}/v1/engineering-runs/activate" >/tmp/run.json
run_id="$(jq -r '.id' /tmp/run.json)"
run_revision="$(jq -r '.revision' /tmp/run.json)"
spec_digest="$(jq -r '.work_specification_digest' /tmp/run.json)"
echo "Engineering Run: ${run_id}"

jq -n --arg operation_key "w9-s1-reference-${GITHUB_RUN_ID}-${GITHUB_RUN_ATTEMPT}" --argjson expected_revision "${run_revision}" \
  '{operation_key:$operation_key,expected_revision:$expected_revision}' >/tmp/autonomous.json
autonomous_status="$(curl --silent --show-error --max-time 900 \
  --output /tmp/autonomous-result.json --write-out '%{http_code}' \
  --cookie "${COOKIE_JAR}" \
  -H "X-Parallax-Session: 1" \
  -H "Content-Type: application/json" \
  --data-binary @/tmp/autonomous.json \
  -X POST "${API_BASE}/v1/engineering-runs/${run_id}/autonomous" || true)"
if [ "${autonomous_status}" = "200" ]; then
  jq '.run' /tmp/autonomous-result.json >/tmp/run-final.json
else
  api "${API_BASE}/v1/engineering-runs/${run_id}" >/tmp/run-final.json || cp /tmp/run.json /tmp/run-final.json
fi

final_state="$(jq -r '.state' /tmp/run-final.json)"
final_revision="$(jq -r '.revision' /tmp/run-final.json)"
failure="$(jq -r '.last_failure_code // ""' /tmp/run-final.json)"
completed_at="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
disposition="OBSERVED_${final_state}"
if [ "${autonomous_status}" != "200" ]; then disposition="AUTONOMOUS_REQUEST_FAILED_HTTP_${autonomous_status}"; fi

python -m pip install --quiet -e services/api
cp /tmp/approved-spec.json /tmp/spec-read.json
cp /tmp/run-final.json /tmp/run-read.json
PYTHONPATH=services/api python - <<'PY'
import json
from pathlib import Path
from parallax_api.evaluation.real_world_bench import (
    CanonicalAcceptanceCriterion,
    CanonicalWorkSpecificationEvidence,
    bind_real_world_template,
    load_real_world_template,
)

template = load_real_world_template(Path('benchmarks/parallax-engineering/real-world/decision-ledger-v1.json'))
spec = json.load(open('/tmp/spec-read.json', encoding='utf-8'))
run = json.load(open('/tmp/run-read.json', encoding='utf-8'))
evidence = CanonicalWorkSpecificationEvidence(
    project_id=run['project_id'],
    work_specification_id=spec['id'],
    work_specification_revision=spec['revision'],
    work_specification_digest=run['work_specification_digest'],
    work_specification_status=spec['status'],
    acceptance_criteria=tuple(
        CanonicalAcceptanceCriterion(acceptance_id=item['id'], text=item['text'])
        for item in run['acceptance_criteria']
    ),
    repository_shape='client-web',
)
case = bind_real_world_template(template, evidence)
with open('/tmp/benchmark-admission.json', 'w', encoding='utf-8') as handle:
    json.dump({
        'benchmark_case_digest': case.digest,
        'acceptance_ids': list(case.acceptance_ids),
        'fixture_digest': case.fixture_digest,
        'expected_ceiling': case.expected_ceiling.value,
    }, handle, sort_keys=True)
PY

benchmark_case_digest="$(jq -r '.benchmark_case_digest' /tmp/benchmark-admission.json)"
acceptance_ids="$(jq -c '.acceptance_ids' /tmp/benchmark-admission.json)"

jq -n \
  --arg template_id "decision-ledger" \
  --arg template_version "1.0.0" \
  --arg fixture_digest "${fixture_digest}" \
  --arg benchmark_case_digest "${benchmark_case_digest}" \
  --argjson acceptance_ids "${acceptance_ids}" \
  --arg project_id "${project_id}" \
  --arg conversation_id "${conversation_id}" \
  --arg work_specification_id "${spec_id}" \
  --argjson work_specification_revision "${revision}" \
  --arg work_specification_digest "${spec_digest}" \
  --arg engineering_run_id "${run_id}" \
  --arg final_state "${final_state}" \
  --argjson final_revision "${final_revision}" \
  --arg last_failure_code "${failure}" \
  --arg started_at "${started_at}" \
  --arg completed_at "${completed_at}" \
  --arg disposition "${disposition}" \
  '{w9_s1_reference_observation:{schema_version:1,template_id:$template_id,template_version:$template_version,fixture_digest:$fixture_digest,benchmark_case_digest:$benchmark_case_digest,acceptance_ids:$acceptance_ids,project_id:$project_id,conversation_id:$conversation_id,work_specification_id:$work_specification_id,work_specification_revision:$work_specification_revision,work_specification_digest:$work_specification_digest,engineering_run_id:$run_id,final_state:$final_state,final_revision:$final_revision,last_failure_code:(if $last_failure_code=="" then null else $last_failure_code end),started_at:$started_at,completed_at:$completed_at,pre_approval_clarifications:0,post_approval_corrections:0,out_of_band_source_edits:0,disposition:$disposition}}'

# QA replay marker: exercise production PREPARE failure projection after deployment 9f9414f5.

# W8-S2 bounded attempt diagnostic
# Diagnostic-only: authenticated QA identity reads one known failed QA-owned run and projects bounded attempt evidence.
w8_diag_run_id="4af0668c-c9c9-48aa-8051-8d6e21597db8"
if api "${API_BASE}/v1/engineering-runs/${w8_diag_run_id}" >/tmp/w8-diag-run.json 2>/dev/null; then
  jq '{id,state,revision,last_failure_code,attempts:[.attempts[] | {stage,status,failure_code,evidence}]}' /tmp/w8-diag-run.json
fi
