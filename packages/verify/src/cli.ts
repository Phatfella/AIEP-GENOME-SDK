/**
 * @aiep/verify — CLI entry point
 *
 * Usage:
 *   tsx src/cli.ts --vectors <path-to-vectors-dir>
 *   tsx src/cli.ts --self-test
 *   tsx src/cli.ts --vectors <dir> --suite <suite-name>
 */

import { argv, exit } from "node:process";
import { runManifest, runSelfTests } from "./runner.js";

// ── ANSI helpers (no dependencies) ───────────────────────────────────────────
const GREEN = "\x1b[32m";
const RED = "\x1b[31m";
const YELLOW = "\x1b[33m";
const BOLD = "\x1b[1m";
const RESET = "\x1b[0m";

function pass(s: string) { return `${GREEN}PASS${RESET} ${s}`; }
function fail(s: string) { return `${RED}FAIL${RESET} ${s}`; }

// ── Argument parsing ──────────────────────────────────────────────────────────

const args = argv.slice(2);

function getFlag(name: string): string | undefined {
    const idx = args.indexOf(name);
    return idx !== -1 ? args[idx + 1] : undefined;
}

function hasFlag(name: string): boolean {
    return args.includes(name);
}

// ── Main ──────────────────────────────────────────────────────────────────────

if (hasFlag("--self-test") || args.length === 0) {
    console.log(`\n${BOLD}AIEP GENOME Kernel Self-Test (R1–R7)${RESET}\n`);

    const results = runSelfTests();
    let failures = 0;
    for (const r of results) {
        const line = `  [${r.rule}] ${r.id.padEnd(40)} ${r.detail}`;
        if (r.pass) {
            console.log(pass(line));
        } else {
            console.log(fail(line));
            failures++;
        }
    }

    const total = results.length;
    const passed = total - failures;
    console.log(`\n${BOLD}${passed}/${total} self-tests passed${RESET}`);
    if (failures === 0) {
        console.log(`${GREEN}${BOLD}TS KERNEL SELF-TEST PASS${RESET}`);
    } else {
        console.log(`${RED}${BOLD}SELF-TEST FAILED — ${failures} error(s)${RESET}`);
        exit(1);
    }
}

const vectorsDir = getFlag("--vectors");
const suiteFilter = getFlag("--suite");

if (vectorsDir) {
    console.log(`\n${BOLD}AIEP GENOME — Vector Conformance${RESET}`);
    console.log(`  directory : ${vectorsDir}`);
    if (suiteFilter) console.log(`  suite     : ${suiteFilter}`);
    console.log();

    let results;
    try {
        results = runManifest(vectorsDir);
    } catch (e) {
        console.error(`${RED}ERROR: ${String(e)}${RESET}`);
        exit(1);
    }

    if (suiteFilter) {
        results = results.filter((r) => r.suite === suiteFilter);
    }

    let failures = 0;
    for (const r of results) {
        const label = `${r.vectorId.padEnd(12)} [${r.suite}]`;
        if (r.pass) {
            console.log(pass(`${label.padEnd(40)} ${r.detail}`));
        } else {
            console.log(fail(`${label.padEnd(40)} ${r.detail}`));
            failures++;
        }
    }

    const total = results.length;
    const passed = total - failures;

    console.log(`\n${BOLD}${passed}/${total} vectors passed${RESET}`);

    if (failures === 0) {
        // Determine pack version from manifest
        const { readFileSync, existsSync } = await import("node:fs");
        const { join } = await import("node:path");
        const manifestPath = join(vectorsDir, "MANIFEST.json");
        let packVersion = "?";
        if (existsSync(manifestPath)) {
            try {
                const m = JSON.parse(readFileSync(manifestPath, "utf8")) as { vector_pack_version?: string };
                packVersion = m.vector_pack_version ?? "?";
            } catch { /* ignore */ }
        }
        console.log(`\n${GREEN}${BOLD}AIEP-COMPLIANT v${packVersion}${RESET}`);
    } else {
        console.log(`\n${RED}${BOLD}NOT CONFORMANT — ${failures} failure(s)${RESET}`);
        exit(1);
    }
}

if (!hasFlag("--self-test") && !vectorsDir) {
    console.error(`Usage:
  tsx src/cli.ts --self-test
  tsx src/cli.ts --vectors <path-to-AIEP-VECTORS/vX.Y.Z/>
  tsx src/cli.ts --vectors <dir> --suite <suite-name>
`);
    exit(1);
}
