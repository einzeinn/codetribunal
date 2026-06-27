/**
 * Courtroom theme constants — agent accent colors and shared values.
 * Used by CourtroomCharacter, CourtroomStage, and dialogue boxes.
 */

export type AgentId = "aegis" | "axiom" | "metric" | "arbiter" | "ledger";
export type Pose = "neutral" | "active";

export interface AgentTheme {
  id: AgentId;
  name: string;
  role: string;
  accent: string;
  /** RGB values for bg-opacity calculations */
  accentRgb: string;
}

export const AGENTS: Record<AgentId, AgentTheme> = {
  aegis: {
    id: "aegis",
    name: "AEGIS",
    role: "Prosecutor",
    accent: "#D85A30",
    accentRgb: "216, 90, 48",
  },
  axiom: {
    id: "axiom",
    name: "AXIOM",
    role: "Defense",
    accent: "#185FA5",
    accentRgb: "24, 95, 165",
  },
  metric: {
    id: "metric",
    name: "METRIC",
    role: "Expert Witness",
    accent: "#5F5E5A",
    accentRgb: "95, 94, 90",
  },
  arbiter: {
    id: "arbiter",
    name: "ARBITER",
    role: "Judge",
    accent: "#BA7517",
    accentRgb: "186, 117, 23",
  },
  ledger: {
    id: "ledger",
    name: "LEDGER",
    role: "Clerk",
    accent: "#8B7355",
    accentRgb: "139, 115, 85",
  },
};

/** Map backend agent name (uppercase) to our AgentId */
export function toAgentId(name: string): AgentId {
  return (name.toLowerCase() as AgentId) in AGENTS
    ? (name.toLowerCase() as AgentId)
    : "ledger";
}

/** Sprite path helper */
export function spritePath(agentId: AgentId, pose: Pose): string {
  // ARBITER uses "ruling" instead of "active"
  const file = agentId === "arbiter" && pose === "active" ? "ruling" : pose;
  return `/characters/${agentId}/${file}.png`;
}
