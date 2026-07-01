export type KnowledgeCategory =
  | "Education"
  | "Programs"
  | "Experience"
  | "Projects"
  | "Achievements"
  | "Skills";

export type KnowledgeStatus =
  | "confirmed"
  | "needs-review"
  | "recently-added";

export type KnowledgeItem = {
  id: string;
  category: KnowledgeCategory;
  title: string;
  detail: string;
  status: KnowledgeStatus;
  stage: number;
  evidence?: string;
};

export type ChatMessage = {
  id: string;
  author: "assistant" | "user";
  body: string;
  timestamp: string;
};

export const categoryOrder: KnowledgeCategory[] = [
  "Education",
  "Programs",
  "Experience",
  "Projects",
  "Achievements",
  "Skills",
];

export const knowledgeItems: KnowledgeItem[] = [
  {
    id: "education-ut-austin",
    category: "Education",
    title: "The University of Texas at Austin",
    detail: "B.S. Astronomy · 2020–2024",
    status: "confirmed",
    stage: 1,
    evidence: "Resume",
  },
  {
    id: "program-gevip",
    category: "Programs",
    title: "Galaxy Evolution VIP (GEVIP)",
    detail: "Selective research program · dates need confirmation",
    status: "needs-review",
    stage: 1,
    evidence: "Conversation",
  },
  {
    id: "experience-galaxy-research",
    category: "Experience",
    title: "Galaxy evolution research",
    detail: "Analyzed gas kinematics with an astronomy research team",
    status: "recently-added",
    stage: 2,
    evidence: "Guided Story",
  },
  {
    id: "project-capstone",
    category: "Projects",
    title: "Gas Kinematics Capstone",
    detail: "Python analysis, data visualization, and scientific writing",
    status: "confirmed",
    stage: 2,
    evidence: "Resume + conversation",
  },
  {
    id: "achievement-aas",
    category: "Achievements",
    title: "AAS poster presentation",
    detail: "Presentation title and conference date need review",
    status: "needs-review",
    stage: 3,
    evidence: "Conversation",
  },
  {
    id: "skill-python",
    category: "Skills",
    title: "Python",
    detail: "Supported by capstone analysis and research workflows",
    status: "confirmed",
    stage: 2,
    evidence: "Capstone + GEVIP",
  },
  {
    id: "skill-scientific-communication",
    category: "Skills",
    title: "Scientific communication",
    detail: "Recently connected to the AAS poster presentation",
    status: "recently-added",
    stage: 3,
    evidence: "Guided Story",
  },
];

export const initialMessages: ChatMessage[] = [
  {
    id: "assistant-welcome",
    author: "assistant",
    body: "Let’s start with the story behind your education. What did you study, and which experiences shaped you most?",
    timestamp: "9:41 AM",
  },
  {
    id: "user-college-story",
    author: "user",
    body: "I studied astronomy at UT Austin. I joined GEVIP, worked on galaxy evolution research, and built my capstone around gas kinematics.",
    timestamp: "9:42 AM",
  },
  {
    id: "assistant-program-question",
    author: "assistant",
    body: "I found your degree, the GEVIP program, and a connected capstone project. Was GEVIP primarily a course, a research group, or a selective program?",
    timestamp: "9:43 AM",
  },
];

export const assistantFollowUps = [
  "That helps. I’ve connected GEVIP to your research experience and capstone without duplicating either one. What did you personally own in the project?",
  "Great detail. I added the AAS presentation as a proposed achievement and connected scientific communication as a skill. You’ll be able to review both before anything is approved.",
  "Your story is taking shape. I’ve marked the high-confidence facts as confirmed and kept the uncertain details visible for review.",
];

export const dashboardSummary = [
  { label: "Education", count: 1, strength: "Strong" },
  { label: "Programs", count: 1, strength: "Review" },
  { label: "Experience", count: 1, strength: "Good" },
  { label: "Projects", count: 1, strength: "Strong" },
  { label: "Achievements", count: 1, strength: "Review" },
  { label: "Skills", count: 2, strength: "Good" },
];
