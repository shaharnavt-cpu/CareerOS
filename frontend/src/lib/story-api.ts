export type StoryStatus = "PROPOSED" | "APPROVED" | "REJECTED" | "ARCHIVED";

export type StoryChapter = {
  id: string;
  title: string;
  summary: string | null;
  position: number;
  start_date: string | null;
  end_date: string | null;
};

export type StoryMembership = {
  id: string;
  entity_type:
    | "PROGRAM"
    | "EDUCATION"
    | "EXPERIENCE"
    | "PROJECT"
    | "ACHIEVEMENT"
    | "SKILL";
  entity_id: string;
  chapter_id: string | null;
  label: string;
  organization: string | null;
  role: string | null;
  rationale: string;
  confidence: number;
};

export type StoryEvidence = {
  id: string;
  evidence_item_id: string;
  title: string;
  evidence_type: string;
  verification_status: string;
  source_url: string | null;
  excerpt: string | null;
  relationship_type: string;
};

export type CareerStory = {
  id: string;
  title: string;
  summary: string;
  primary_goal: string | null;
  transformation: string | null;
  confidence: number;
  status: StoryStatus;
  chapters: StoryChapter[];
  memberships: StoryMembership[];
  evidence: StoryEvidence[];
  created_at: string;
  updated_at: string;
  approved_at: string | null;
};

export type StoryDiscoveryResult = {
  stories: CareerStory[];
  experiences_considered: number;
  signals_used: string[];
  explanation: string;
};

const apiBase =
  process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, "") ??
  "http://localhost:8000";

export async function listStories(): Promise<CareerStory[]> {
  return request(`${apiBase}/api/stories`);
}

export async function discoverStories(): Promise<StoryDiscoveryResult> {
  return request(`${apiBase}/api/stories/discover`, { method: "POST" });
}

export async function updateStory(
  storyId: string,
  changes: {
    summary?: string;
    primary_goal?: string | null;
    transformation?: string | null;
  },
): Promise<CareerStory> {
  return request(`${apiBase}/api/stories/${storyId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(changes),
  });
}

export async function renameStory(
  storyId: string,
  title: string,
): Promise<CareerStory> {
  return request(`${apiBase}/api/stories/${storyId}/rename`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ title }),
  });
}

export async function transitionStory(
  storyId: string,
  action: "approve" | "reject" | "archive",
): Promise<CareerStory> {
  return request(`${apiBase}/api/stories/${storyId}/${action}`, {
    method: "POST",
  });
}

export async function mergeStories(
  storyIds: string[],
  title?: string,
): Promise<CareerStory> {
  return request(`${apiBase}/api/stories/merge`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ story_ids: storyIds, title }),
  });
}

export async function splitStory(
  storyId: string,
  membershipIds: string[],
  title: string,
): Promise<CareerStory> {
  return request(`${apiBase}/api/stories/${storyId}/split`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ membership_ids: membershipIds, title }),
  });
}

async function request<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, init);
  if (response.ok) return (await response.json()) as T;
  const body = (await response.json().catch(() => null)) as {
    detail?: string;
  } | null;
  throw new Error(body?.detail ?? `CareerOS API returned ${response.status}.`);
}
