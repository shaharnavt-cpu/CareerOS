import assert from "node:assert/strict";
import test from "node:test";

import {
  createProofArtifact,
  listEligibleProofMemories,
  regenerateProofArtifact,
  updateProofArtifact,
  updateProofArtifactVersion,
} from "./proof-artifact-api.ts";

test("proof artifact API uses eligible-memory and generation contracts", async () => {
  const originalFetch = globalThis.fetch;
  const calls: Array<{ url: string; init?: RequestInit }> = [];
  globalThis.fetch = async (input, init) => {
    calls.push({ url: String(input), init });
    return new Response(JSON.stringify([]), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    });
  };

  try {
    await listEligibleProofMemories();
    await createProofArtifact({
      source_memory_id: "memory-1",
      source_diagnosis_result_id: "diagnosis-result-1",
      target_role: "Data Analytics / AI internship",
      target_audience: "APPLICATION_UPLOAD",
      artifact_type: "CASE_STUDY",
    });
    await regenerateProofArtifact("artifact-1", {});
    await updateProofArtifact("artifact-1", { status: "READY" });
    await updateProofArtifactVersion("artifact-1", "version-1", {
      content: "Edited proof",
    });

    assert.match(calls[0].url, /\/api\/proof-artifacts\/eligible-memories$/);
    assert.match(calls[1].url, /\/api\/proof-artifacts$/);
    assert.equal(calls[1].init?.method, "POST");
    assert.match(String(calls[1].init?.body), /diagnosis-result-1/);
    assert.match(calls[2].url, /\/api\/proof-artifacts\/artifact-1\/regenerate$/);
    assert.equal(calls[2].init?.body, "{}");
    assert.match(calls[3].url, /\/api\/proof-artifacts\/artifact-1$/);
    assert.equal(calls[3].init?.method, "PATCH");
    assert.match(String(calls[3].init?.body), /READY/);
    assert.match(
      calls[4].url,
      /\/api\/proof-artifacts\/artifact-1\/versions\/version-1$/,
    );
    assert.equal(calls[4].init?.method, "PATCH");
    assert.match(String(calls[4].init?.body), /Edited proof/);
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test("proof artifact API surfaces backend validation detail", async () => {
  const originalFetch = globalThis.fetch;
  globalThis.fetch = async () =>
    new Response(
      JSON.stringify({
        detail: "Approve career memories before building a proof artifact.",
      }),
      { status: 422, headers: { "Content-Type": "application/json" } },
    );

  try {
    await assert.rejects(
      () => listEligibleProofMemories(),
      /Approve career memories before building a proof artifact/,
    );
  } finally {
    globalThis.fetch = originalFetch;
  }
});
