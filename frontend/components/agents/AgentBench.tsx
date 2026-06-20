"use client";

import AgentCard from "./AgentCard";

interface AgentStatus {
  name: string;
  role: string;
  status: string;
  isActive: boolean;
}

interface AgentBenchProps {
  agents: AgentStatus[];
}

export default function AgentBench({ agents }: AgentBenchProps) {
  return (
    <div className="flex justify-center items-end gap-2 flex-nowrap overflow-x-auto py-1">
      {agents.map((agent) => (
        <AgentCard
          key={agent.name}
          name={agent.name}
          role={agent.role}
          status={agent.status}
          isActive={agent.isActive}
          isCenter={agent.name === "ARBITER"}
        />
      ))}
    </div>
  );
}
