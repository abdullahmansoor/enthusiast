import { PageMain } from "@/components/util/page-main";
import { PageHeading } from "@/components/util/page-heading";
import { AgentBuilderList } from "@/components/agent-builder/agent-builder-list";

export function AgentBuilderPage() {
  return (
    <PageMain>
      <PageHeading
        title="Agent Builder"
        description="Create and manage your custom AI agents with personalized configurations."
      />
      <AgentBuilderList />
    </PageMain>
  );
}
