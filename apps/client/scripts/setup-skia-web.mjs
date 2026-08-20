import { copyFileSync, mkdirSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { createRequire } from 'node:module';

const require = createRequire(import.meta.url);
const source = require.resolve('canvaskit-wasm/bin/full/canvaskit.wasm');
const target = join(process.cwd(), 'public', 'canvaskit.wasm');
mkdirSync(dirname(target), { recursive: true });
copyFileSync(source, target);
console.log(`Copied CanvasKit WASM to ${target}`);
