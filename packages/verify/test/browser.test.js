import test from "node:test";
import assert from "node:assert/strict";
import { canonicalJson, commitCanonical, concatHash, sha256hex } from "../browser.js";

test("browser commitment adapter retains Genome canonical ordering and NFC", async () => {
  assert.equal(canonicalJson({ z: 1, a: "A\u030a" }), '{"a":"Å","z":1}');
  assert.equal(await sha256hex(""), "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855");
  assert.equal(await commitCanonical({ b: 2, a: 1 }), await commitCanonical({ a: 1, b: 2 }));
  assert.notEqual(await concatHash("ab", "c"), await concatHash("a", "bc"));
});

test("browser commitment adapter fails closed on invalid Genome numbers", () => {
  assert.throws(() => canonicalJson({ value: -0 }), /minus-zero/);
  assert.throws(() => canonicalJson({ value: Number.NaN }), /non-finite/);
});
