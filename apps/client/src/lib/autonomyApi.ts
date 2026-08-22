import { fetch } from 'expo/fetch';
import { Platform } from 'react-native';
import type { EngineeringRunDto } from './api';

export type EngineeringAutonomyStepDto = {
  stage: string;
  outcome: string;
  attempt_id: string | null;
  replayed: boolean;
  tool_id: string | null;
};

export type EngineeringAutonomyResultDto = {
  run: EngineeringRunDto;
  stop_reason: string;
  steps: EngineeringAutonomyStepDto[];
};

const configuredApiBase = process.env.EXPO_PUBLIC_PARALLAX_API_URL ?? 'http://localhost:8010';
const hostedHttpsWeb = Platform.OS === 'web'
  && typeof globalThis.location !== 'undefined'
  && globalThis.location.protocol === 'https:';
const apiBase = hostedHttpsWeb || (Platform.OS === 'web' && configuredApiBase.startsWith('https://'))
  ? '/p2-api'
  : configuredApiBase;

export async function runEngineeringAutonomy(
  run: EngineeringRunDto,
  operationKey: string,
): Promise<EngineeringAutonomyResultDto> {
  const response = await fetch(`${apiBase}/v1/engineering-runs/${run.id}/autonomous`, {
    method: 'POST',
    credentials: hostedHttpsWeb ? 'include' : 'same-origin',
    headers: {
      'Content-Type': 'application/json',
      ...(hostedHttpsWeb ? { 'X-Parallax-Session': '1' } : {}),
    },
    body: JSON.stringify({ operation_key: operationKey, expected_revision: run.revision }),
  });
  if (!response.ok) {
    let detail = `Parallax API ${response.status}`;
    try {
      const payload = await response.json() as { detail?: string };
      if (typeof payload.detail === 'string' && payload.detail.trim()) detail = payload.detail;
    } catch {
      // Keep the status fallback when the API did not return JSON.
    }
    throw new Error(detail);
  }
  return await response.json() as EngineeringAutonomyResultDto;
}
