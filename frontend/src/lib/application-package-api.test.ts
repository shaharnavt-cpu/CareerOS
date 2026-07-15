import assert from "node:assert/strict";
import test from "node:test";

import {
  createApplicationPackage,
  generateApplicationPackage,
  getApplicationPackage,
  listApplicationPackages,
  listEligibleApplicationPackageMemories,
  regenerateApplicationPackage,
  updateApplicationPackage,
  updateApplicationPackageOutputs,
} from "./application-package-api.ts";

test("application package API follows the complete package and version contract", async () => {
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
    await listEligibleApplicationPackageMemories("Data Science Intern");
    await listApplicationPackages();
    await listApplicationPackages(true);
    await getApplicationPackage("package-1");
    await createApplicationPackage({
      opportunity_id: "opportunity-1",
      role_title: "Data Science Intern",
      company: "Test Company",
      location: "Chicago, IL",
      job_type: "Internship",
      target_description: "Analyze data and communicate uncertainty.",
      required_skills: ["Python", "modeling"],
      preferred_skills: ["technical communication"],
      responsibilities: ["Analyze messy data"],
      selected_memory_ids: ["gas-memory", "unicorn-memory"],
    });
    await generateApplicationPackage("package-1", {
      selected_memory_ids: ["gas-memory", "unicorn-memory"],
    });
    await regenerateApplicationPackage("package-1", {
      selected_memory_ids: ["unicorn-memory", "gas-memory"],
    });
    await updateApplicationPackage("package-1", { status: "ARCHIVED" });
    await updateApplicationPackageOutputs("package-1", {
      edit_summary: "Reviewed wording",
      reviewer_questions: ["Can I support this metric?"],
    });

    assert.match(
      calls[0].url,
      /\/api\/application-packages\/eligible-memories\?target_role=Data\+Science\+Intern$/,
    );
    assert.equal(calls[0].init?.cache, "no-store");
    assert.match(calls[1].url, /\/api\/application-packages$/);
    assert.equal(calls[1].init?.cache, "no-store");
    assert.match(
      calls[2].url,
      /\/api\/application-packages\?include_archived=true$/,
    );
    assert.match(calls[3].url, /\/api\/application-packages\/package-1$/);
    assert.equal(calls[3].init?.cache, "no-store");
    assert.equal(calls[4].init?.method, "POST");
    assert.deepEqual(JSON.parse(String(calls[4].init?.body)), {
      opportunity_id: "opportunity-1",
      role_title: "Data Science Intern",
      company: "Test Company",
      location: "Chicago, IL",
      job_type: "Internship",
      target_description: "Analyze data and communicate uncertainty.",
      required_skills: ["Python", "modeling"],
      preferred_skills: ["technical communication"],
      responsibilities: ["Analyze messy data"],
      selected_memory_ids: ["gas-memory", "unicorn-memory"],
    });
    assert.match(calls[5].url, /\/package-1\/generate$/);
    assert.deepEqual(JSON.parse(String(calls[5].init?.body)), {
      selected_memory_ids: ["gas-memory", "unicorn-memory"],
    });
    assert.match(calls[6].url, /\/package-1\/regenerate$/);
    assert.deepEqual(JSON.parse(String(calls[6].init?.body)), {
      selected_memory_ids: ["unicorn-memory", "gas-memory"],
    });
    assert.match(calls[7].url, /\/api\/application-packages\/package-1$/);
    assert.equal(calls[7].init?.method, "PATCH");
    assert.match(String(calls[7].init?.body), /ARCHIVED/);
    assert.match(calls[8].url, /\/package-1\/outputs$/);
    assert.equal(calls[8].init?.method, "PATCH");
    assert.match(String(calls[8].init?.body), /Reviewed wording/);
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test("application package API surfaces FastAPI validation details", async () => {
  const originalFetch = globalThis.fetch;
  globalThis.fetch = async () =>
    new Response(
      JSON.stringify({
        detail: [
          { msg: "Select at least one approved Career Memory before generating." },
          { msg: "Role title is required." },
        ],
      }),
      { status: 422, headers: { "Content-Type": "application/json" } },
    );

  try {
    await assert.rejects(
      () => generateApplicationPackage("package-1"),
      /Select at least one approved Career Memory.*Role title is required/,
    );
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test("application package API preserves structured backend error messages", async () => {
  const originalFetch = globalThis.fetch;
  globalThis.fetch = async () =>
    new Response(
      JSON.stringify({ error: { message: "Approved memory is no longer eligible." } }),
      { status: 409, headers: { "Content-Type": "application/json" } },
    );

  try {
    await assert.rejects(
      () => listEligibleApplicationPackageMemories(),
      /Approved memory is no longer eligible/,
    );
  } finally {
    globalThis.fetch = originalFetch;
  }
});
