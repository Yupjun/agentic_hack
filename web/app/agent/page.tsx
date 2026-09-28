// Question: give the agent a goal and watch what it does.
import { get } from "@/lib/api";
import type { Session } from "@/lib/types";
import { AgentConsole } from "@/components/AgentConsole";

export const dynamic = "force-dynamic";

export default async function Page() {
  const s = await get<Session[]>("/api/sessions");
  return (
    <div className="space-y-4">
      <div>
        <div className="kicker">NeMo Agent Toolkit · tool_calling_agent · Nemotron 3 Super through the NeMo Guardrails gateway</div>
        <h1 className="text-h1 font-semibold">목표를 주면 에이전트가 계획한다<span className="text-cobalt">.</span></h1>
      </div>
      <AgentConsole initial={s} />
    </div>
  );
}
