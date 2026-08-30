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

export class EngineeringAutonomyError extends Error {
  readonly code: string | null;

  constructor(message: string, code: string | null = null) {
    super(message);
    this.name = 'EngineeringAutonomyError';
    this.code = code;
  }
}

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
    let code: string | null = null;
    try {
      const payload = await response.json() as { detail?: unknown };
      if (typeof payload.detail === 'string' && payload.detail.trim()) {
        detail = payload.detail;
      } else if (payload.detail && typeof payload.detail === 'object') {
        const structured = payload.detail as { message?: unknown; code?: unknown };
        if (typeof structured.message === 'string' && structured.message.trim()) detail = structured.message;
        if (typeof structured.code === 'string' && /^[A-Z0-9_]{1,96}$/.test(structured.code)) code = structured.code;
      }
    } catch {
      // Keep the bounded status fallback when the API did not return JSON.
    }
    throw new EngineeringAutonomyError(detail, code);
  }
  return await response.json() as EngineeringAutonomyResultDto;
}
