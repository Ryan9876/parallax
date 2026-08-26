export const WORK_SPEC_RATE_LIMIT_MESSAGE = 'Model capacity is temporarily unavailable. Retry Capture Spec later; your objective is preserved.';

export function workSpecificationDraftFailureMessage(status: number | null, detail: string | null | undefined): string {
  if (status === 429) return WORK_SPEC_RATE_LIMIT_MESSAGE;
  const clean = detail?.trim();
  return clean || 'Specification drafting failed. Your objective is preserved; retry Capture Spec.';
}
