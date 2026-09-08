import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const here = dirname(fileURLToPath(import.meta.url));
const component = readFileSync(join(here, '..', 'src', 'components', 'WorkSpecificationStatus.tsx'), 'utf8');
const api = readFileSync(join(here, '..', 'src', 'lib', 'api.ts'), 'utf8');

const requiredComponentContracts = [
  'HOW PARALLAX WILL VERIFY IT',
  'Create verification plan',
  'Approve verification plan',
  'Verification plan approved',
  'Automated browser check',
  'Human review',
  'does not mean the app has passed verification',
  'Nothing was marked verified',
];

for (const contract of requiredComponentContracts) {
  if (!component.includes(contract)) {
    throw new Error(`behavioral verification plan UI contract missing: ${contract}`);
  }
}

const requiredApiContracts = [
  '/behavioral-verification-plan',
  '/behavioral-verification-plan/draft',
  '/behavioral-verification-plans/',
  '/approve',
];

for (const contract of requiredApiContracts) {
  if (!api.includes(contract)) {
    throw new Error(`behavioral verification plan API contract missing: ${contract}`);
  }
}

if (component.includes('executeBehavioralVerification') || api.includes('/behavioral-verification-plans/' + '${planId}' + '/execute')) {
  throw new Error('P2-V0.23.47 must not expose browser execution authority');
}

console.log('PASS: behavioral verification plan review/approval UI stays distinct from app verification');
