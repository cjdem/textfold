// Build the shared Windows Python payload in desktop-mygo/resources/payload.
// The Electron payload script owns the CPython download and package install;
// this wrapper only points its output at the MyGo resource folder.
import { execFileSync } from "node:child_process";
import { existsSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const root = path.dirname(here);
const script = path.join(root, "desktop", "scripts", "prepare-payload.mjs");
const payload = path.join(here, "resources", "payload");

if (!existsSync(script)) throw new Error(`missing payload script: ${script}`);
execFileSync(process.env.NODE || "node", [script, "win32", "x64"], {
  cwd: root,
  env: { ...process.env, TEXTFOLD_PAYLOAD: payload },
  stdio: "inherit",
});
console.log(`MyGo payload ready at ${payload}`);
