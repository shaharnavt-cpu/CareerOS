import assert from "node:assert/strict";
import test from "node:test";

import {
  evidenceCategoryLabel,
  mergeById,
  nextListeningStep,
  replacePendingById,
} from "./listening-utils.ts";

test("mergeById keeps prior proposals and replaces matching ids", () => {
  const result = mergeById(
    [
      { id: "one", value: "old" },
      { id: "two", value: "kept" },
    ],
    [{ id: "one", value: "new" }],
  );

  assert.deepEqual(result, [
    { id: "one", value: "new" },
    { id: "two", value: "kept" },
  ]);
});

test("listening progress stops at its final user-facing stage", () => {
  assert.equal(nextListeningStep(0, 5), 1);
  assert.equal(nextListeningStep(4, 5), 4);
});

test("evidence labels prefer extracted category and format source fallback", () => {
  assert.equal(
    evidenceCategoryLabel({ category: "EDUCATION", source_type: "RESUME" }),
    "EDUCATION",
  );
  assert.equal(
    evidenceCategoryLabel({ source_type: "GENERIC_DOCUMENT" }),
    "GENERIC DOCUMENT",
  );
});

test("a fresh multi-source pass replaces stale pending proposals", () => {
  const proposal = (id: string, approval_state: string) => ({ id, approval_state });
  const result = replacePendingById(
    [proposal("old", "NEEDS_REVIEW"), proposal("kept", "CANONICAL")],
    [proposal("fused", "NEEDS_REVIEW")],
  );

  assert.deepEqual(
    result.map((item) => item.id),
    ["kept", "fused"],
  );
});
