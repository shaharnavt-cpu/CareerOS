import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

import {
  convertProposalToEnrichment,
  createEnrichment,
  isDuplicateEnrichmentError,
  listEnrichments,
  updateEnrichment,
} from "./enrichment-api.ts";

test("enrichment API uses create, review, and conversion contracts", async () => {
  const originalFetch = globalThis.fetch;
  const calls: Array<{ url: string; init?: RequestInit }> = [];
  globalThis.fetch = async (input, init) => {
    calls.push({ url: String(input), init });
    return new Response(JSON.stringify({}), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    });
  };

  try {
    await listEnrichments();
    await createEnrichment("memory-1", "Methods: Gaussian fitting");
    await updateEnrichment("enrichment-1", { status: "APPROVED" });
    await convertProposalToEnrichment("memory-1", "proposal/1");

    assert.match(calls[0].url, /\/api\/career-memory\/enrichments$/);
    assert.match(
      calls[1].url,
      /\/api\/career-memory\/memory-1\/enrichments$/,
    );
    assert.equal(calls[1].init?.method, "POST");
    assert.match(String(calls[1].init?.body), /Gaussian fitting/);
    assert.match(
      calls[2].url,
      /\/api\/career-memory\/enrichments\/enrichment-1$/,
    );
    assert.equal(calls[2].init?.method, "PATCH");
    assert.match(String(calls[2].init?.body), /APPROVED/);
    assert.match(calls[3].url, /from-proposal\/proposal%2F1$/);
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test("enrichment API preserves actionable duplicate response details", async () => {
  const originalFetch = globalThis.fetch;
  globalThis.fetch = async () =>
    new Response(
      JSON.stringify({
        detail: {
          code: "DUPLICATE_ENRICHMENT",
          message:
            "This evidence already appears to be saved for this project. No duplicate enrichment was created.",
          existing_enrichment_id: "enrichment-existing",
          existing_status: "APPROVED",
        },
      }),
      { status: 409, headers: { "Content-Type": "application/json" } },
    );

  try {
    await assert.rejects(
      () => createEnrichment("memory-1", "Repeated project evidence"),
      (error: unknown) => {
        assert.ok(isDuplicateEnrichmentError(error));
        assert.equal(error.status, 409);
        assert.equal(error.existingEnrichmentId, "enrichment-existing");
        assert.equal(error.existingStatus, "APPROVED");
        assert.equal(
          error.message,
          "This evidence already appears to be saved for this project. No duplicate enrichment was created.",
        );
        return true;
      },
    );
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test("enrichment route renders the complete reviewed project flow", () => {
  const route = readFileSync(
    new URL("../app/enrichments/page.tsx", import.meta.url),
    "utf8",
  );
  const workspace = readFileSync(
    new URL(
      "../components/enrichments/enrichment-workspace.tsx",
      import.meta.url,
    ),
    "utf8",
  );

  assert.match(route, /EnrichmentWorkspace/);
  assert.match(route, /memory_id/);
  assert.match(route, /proposal_id/);
  assert.match(workspace, /Approved project memory/);
  assert.match(workspace, /Project details/);
  assert.match(workspace, /Generate enrichment proposal/);
  assert.match(workspace, /CareerOS thinks this belongs to/);
  assert.match(workspace, /Approve enrichment/);
  assert.match(workspace, /Save enrichment edits/);
  assert.match(workspace, /saved as proposed/);
  assert.match(workspace, /Reject/);
  assert.match(workspace, /Convert duplicate draft into enrichment/);
  assert.match(workspace, /Rejected enrichment will not affect proof artifacts/);
  assert.match(workspace, /limited project-specific text|abstract, methods/);
  assert.match(workspace, /Regenerate proof artifact/);
  assert.match(
    workspace,
    /This evidence already appears to be saved for this project\. No duplicate enrichment was created\./,
  );
  assert.match(
    workspace,
    /function changeEnrichmentText\(value: string\)[\s\S]*?setEnrichmentText\(value\);[\s\S]*?setDuplicateWarning\(null\);/,
  );
  assert.match(
    workspace,
    /changeEnrichmentText\(event\.target\.value\)/,
  );
  const duplicateCatch = workspace.slice(
    workspace.indexOf("} catch (error) {", workspace.indexOf("async function generate")),
    workspace.indexOf("} finally {", workspace.indexOf("async function generate")),
  );
  assert.doesNotMatch(duplicateCatch, /setEnrichmentText\(""\)/);
  assert.match(workspace, /Matching existing enrichment/);
  assert.match(workspace, /Approved enrichment used by proof artifacts\./);
  assert.match(workspace, /Memory quality impact/);
  assert.match(workspace, /Missing or weak sections/);
  assert.match(workspace, /Project boundary/);
});

test("review, dashboard, navigation, and proof link into enrichment", () => {
  const review = readFileSync(
    new URL("../components/review/review-workspace.tsx", import.meta.url),
    "utf8",
  );
  const dashboard = readFileSync(
    new URL("../components/dashboard/dashboard-shell.tsx", import.meta.url),
    "utf8",
  );
  const navigation = readFileSync(
    new URL("../components/common/workspace-nav.tsx", import.meta.url),
    "utf8",
  );
  const proof = readFileSync(
    new URL(
      "../components/proof-artifacts/proof-artifact-workspace.tsx",
      import.meta.url,
    ),
    "utf8",
  );

  assert.match(review, /Possible duplicate:/);
  assert.match(review, /Convert to enrichment/);
  assert.match(review, /CareerOS will not create a new project memory/);
  assert.match(dashboard, /Add deeper project evidence/);
  assert.match(navigation, /href: "\/enrichments", label: "Enrich"/);
  assert.match(proof, /Need richer proof\? Add project evidence/);
});
