export type KnowledgeCategory =
  | "Education"
  | "Programs"
  | "Experience"
  | "Projects"
  | "Achievements"
  | "Skills";

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

export const initialMessages: ChatMessage[] = [
  {
    id: "assistant-welcome",
    author: "assistant",
    body: "Tell me about your education, work, projects, or achievements. I’ll organize what you share into proposals and explain anything that needs clarification.",
    timestamp: "Now",
  },
];

export const sampleCareerSource = `
Education
The University of Texas at Austin | BS in Astronomy

Programs
Galaxy Evolution Vertically Integrated Program (GEVIP)

Experience
Research Assistant at UT Austin Astronomy Department

Projects
Gas Kinematics Capstone

Achievements
Presented Gas Kinematics research at AAS

Skills
Python, Scientific communication
`;

export const quickReplies = [
  "GEVIP was a selective research program",
  "I wrote the Python analysis for my capstone",
  "I presented the results at AAS",
];
