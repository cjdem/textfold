// The runtime the app ships, in desktop-mygo/resources/payload:
//   python/   a standalone CPython (python-build-standalone, the "install_only_stripped" build for the app's system:
//             64-bit Windows) with TextFold's packages (requirements.txt) installed into it
//   app/      the code: textfold/ (its web/ inside)
// Parts of CPython the server never uses (tkinter and its Tcl/Tk, the test suite, IDLE) are left out: a smaller app.
//
//   node scripts/prepare-payload.mjs                  for this computer
//   PBS_URL=<tar.gz url> node scripts/...             a given build
//   PBS_FILE=<local tar.gz> PBS_SHA256=<digest>       an offline or pre-downloaded build
//   TEXTFOLD_PAYLOAD=<folder>                         write somewhere else
// A Windows payload is made on Windows: the packages are installed by the Python it ships.
import { execFileSync } from 'node:child_process';
import { copyFileSync, cpSync, existsSync, mkdirSync, readFileSync, readdirSync, rmSync, writeFileSync, createWriteStream } from 'node:fs';
import { createHash } from 'node:crypto';
import path from 'node:path';
import { pipeline } from 'node:stream/promises';
import { Readable } from 'node:stream';
import { fileURLToPath } from 'node:url';

const here = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const root = path.dirname(here);
const payload = process.env.TEXTFOLD_PAYLOAD ? path.resolve(process.env.TEXTFOLD_PAYLOAD) : path.join(here, 'resources', 'payload');
const [platform = process.platform, arch = process.arch] = process.argv.slice(2);
const TARGETS = { 'win32-x64': 'x86_64-pc-windows-msvc' };
const TARGET = TARGETS[`${platform}-${arch}`];
if (!TARGET) throw new Error(`no payload for ${platform}-${arch}: ${Object.keys(TARGETS).join(', ')}`);
if ((platform === 'win32') !== (process.platform === 'win32')) throw new Error(`a ${platform} payload is made on ${platform}`);
const WIN = platform === 'win32';

async function cpythonUrl() {
  if (process.env.PBS_URL) return process.env.PBS_URL;
  const r = await fetch('https://api.github.com/repos/astral-sh/python-build-standalone/releases/latest', {
    headers: { 'User-Agent': 'textfold-desktop', ...(process.env.GITHUB_TOKEN ? { Authorization: `Bearer ${process.env.GITHUB_TOKEN}` } : {}) },
  });
  if (!r.ok) throw new Error(`python-build-standalone releases: HTTP ${r.status}`);
  const rel = await r.json();
  const want = new RegExp(`^cpython-3\\.12\\.\\d+\\+\\d+-${TARGET}-install_only_stripped\\.tar\\.gz$`);
  const asset = rel.assets.find((a) => want.test(a.name));
  if (!asset) throw new Error(`no CPython 3.12 ${TARGET} build in ${rel.tag_name}`);
  return asset.browser_download_url;
}

rmSync(payload, { recursive: true, force: true });
mkdirSync(payload, { recursive: true });

const url = process.env.PBS_FILE ? null : await cpythonUrl();
console.log('CPython:', process.env.PBS_FILE || url);
const archive = path.join(payload, 'python.tar.gz');
if (process.env.PBS_FILE) {
  copyFileSync(path.resolve(process.env.PBS_FILE), archive);
} else {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`download: HTTP ${res.status}`);
  await pipeline(Readable.fromWeb(res.body), createWriteStream(archive));
}
if (process.env.PBS_SHA256) {
  const digest = createHash('sha256').update(readFileSync(archive)).digest('hex');
  if (digest.toLowerCase() !== process.env.PBS_SHA256.toLowerCase()) {
    throw new Error(`CPython archive SHA-256 is ${digest}, expected ${process.env.PBS_SHA256}`);
  }
}
// a relative name, run from the folder: Windows' own tar and Git's GNU tar both read it (GNU tar takes C:\… for a host)
execFileSync('tar', ['-xzf', 'python.tar.gz'], { cwd: payload, stdio: 'inherit' });
rmSync(path.join(payload, 'python.tar.gz'));
const py = WIN ? path.join(payload, 'python', 'python.exe') : path.join(payload, 'python', 'bin', 'python3');
const run = (args, opts) => execFileSync(py, args, opts);

console.log('installing TextFold\'s packages…');
run(['-m', 'pip', 'install', '--no-cache-dir', '--disable-pip-version-check', '--no-warn-script-location',
  '-r', path.join(root, 'requirements.txt')], { stdio: 'inherit', env: { ...process.env, PYTHONNOUSERSITE: '1' } });

// what the server never uses
const stdlib = WIN ? path.join(payload, 'python', 'Lib')
  : path.join(payload, 'python', 'lib', readdirSync(path.join(payload, 'python', 'lib')).find((d) => /^python3\.\d+$/.test(d)));
for (const p of ['test', 'idlelib', 'tkinter', 'turtledemo', 'ensurepip', 'lib2to3']) rmSync(path.join(stdlib, p), { recursive: true, force: true });
const dynload = WIN ? path.join(payload, 'python', 'DLLs') : path.join(stdlib, 'lib-dynload');
for (const f of readdirSync(dynload)) if (/^(_tkinter|tcl\d|tk\d)/.test(f)) rmSync(path.join(dynload, f));
const tcl = WIN ? path.join(payload, 'python') : path.join(payload, 'python', 'lib');
for (const d of readdirSync(tcl)) if (/^(tcl|tk|itcl|thread)\d/i.test(d) || /^lib(tcl|tk)/.test(d) || (WIN && d === 'tcl')) rmSync(path.join(tcl, d), { recursive: true, force: true });
(function prune(dir) {
  for (const e of readdirSync(dir, { withFileTypes: true })) {
    if (!e.isDirectory()) continue;
    if (e.name === '__pycache__') rmSync(path.join(dir, e.name), { recursive: true, force: true });
    else prune(path.join(dir, e.name));
  }
})(path.join(payload, 'python'));

// the code
const app = path.join(payload, 'app');
mkdirSync(app, { recursive: true });
for (const d of ['textfold']) {
  cpSync(path.join(root, d), path.join(app, d), { recursive: true, filter: (src) => !src.includes('__pycache__') });
}
writeFileSync(path.join(app, 'requirements.txt'), '# installed into ../python\n');

// a quick check that the runtime imports what the server needs (trafilatura: web pages and HTML files)
run(['-s', '-c', 'import bs4, lxml, PIL, trafilatura, mammoth, openpyxl, pypdfium2, textfold.server; print("payload ok")'], { cwd: app, stdio: 'inherit' });
if (!existsSync(path.join(app, 'textfold', 'web', 'reader.js'))) throw new Error('web/ missing from the payload');
