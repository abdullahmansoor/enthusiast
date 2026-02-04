import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Plus, Sparkles, Copy, Trash2, Play } from "lucide-react";
import { ApiClient } from "@/lib/api";
import { authenticationProviderInstance } from "@/lib/authentication-provider";
import { AgentBuilderListItem } from "@/lib/types";
import { AgentBuilderCard } from "./agent-builder-card";
import { AgentBuilderFormModal } from "./agent-builder-form-modal";
import { AgentTestModal } from "./agent-test-modal";
import { DeleteConfirmationModal } from "./delete-confirmation-modal";
import { useToast } from "@/hooks/use-toast";
import { Skeleton } from "@/components/ui/skeleton";

const api = new ApiClient(authenticationProviderInstance);

export function AgentBuilderList() {
  const [agents, setAgents] = useState<AgentBuilderListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [formModalOpen, setFormModalOpen] = useState(false);
  const [testModalOpen, setTestModalOpen] = useState(false);
  const [deleteModalOpen, setDeleteModalOpen] = useState(false);
  const [selectedAgent, setSelectedAgent] = useState<AgentBuilderListItem | null>(null);
  const { toast } = useToast();

  const fetchAgents = async () => {
    try {
      setLoading(true);
      const response = await api.agents().listBuilderAgents();
      setAgents(response.results);
    } catch (error) {
      toast({
        variant: "destructive",
        title: "Error",
        description: "Failed to load agents. Please try again.",
      });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAgents();
  }, []);

  const handleCreateNew = () => {
    setSelectedAgent(null);
    setFormModalOpen(true);
  };

  const handleEdit = (agent: AgentBuilderListItem) => {
    setSelectedAgent(agent);
    setFormModalOpen(true);
  };

  const handleTest = (agent: AgentBuilderListItem) => {
    setSelectedAgent(agent);
    setTestModalOpen(true);
  };

  const handleClone = async (agent: AgentBuilderListItem) => {
    try {
      await api.agents().cloneBuilderAgent(agent.id, `${agent.name} (Copy)`);
      toast({
        title: "Agent cloned",
        description: "The agent has been successfully cloned.",
      });
      fetchAgents();
    } catch (error) {
      toast({
        variant: "destructive",
        title: "Error",
        description: "Failed to clone agent. Please try again.",
      });
    }
  };

  const handleDelete = (agent: AgentBuilderListItem) => {
    setSelectedAgent(agent);
    setDeleteModalOpen(true);
  };

  const handlePublish = async (agent: AgentBuilderListItem) => {
    try {
      await api.agents().publishBuilderAgent(agent.id);
      toast({
        title: "Agent published",
        description: "The agent is now available for use.",
      });
      fetchAgents();
    } catch (error) {
      toast({
        variant: "destructive",
        title: "Error",
        description: "Failed to publish agent. Please try again.",
      });
    }
  };

  const handleFormSuccess = () => {
    setFormModalOpen(false);
    setSelectedAgent(null);
    fetchAgents();
  };

  const handleDeleteSuccess = () => {
    setDeleteModalOpen(false);
    setSelectedAgent(null);
    fetchAgents();
  };

  if (loading) {
    return (
      <div className="space-y-4">
        <div className="flex justify-end mb-6">
          <Skeleton className="h-10 w-32" />
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {[1, 2, 3].map((i) => (
            <Skeleton key={i} className="h-64 w-full" />
          ))}
        </div>
      </div>
    );
  }

  return (
    <>
      <div className="flex items-center justify-between mb-6">
        <div className="text-sm text-muted-foreground">
          {agents.length} {agents.length === 1 ? "agent" : "agents"}
        </div>
        <Button onClick={handleCreateNew}>
          <Plus className="h-4 w-4 mr-2" />
          Create New Agent
        </Button>
      </div>

      {agents.length === 0 ? (
        <div className="text-center py-12">
          <Sparkles className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
          <h3 className="text-lg font-medium mb-2">No agents yet</h3>
          <p className="text-muted-foreground mb-6">
            Create your first AI agent with custom configurations
          </p>
          <Button onClick={handleCreateNew}>
            <Plus className="h-4 w-4 mr-2" />
            Create Your First Agent
          </Button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {agents.map((agent) => (
            <AgentBuilderCard
              key={agent.id}
              agent={agent}
              onEdit={() => handleEdit(agent)}
              onTest={() => handleTest(agent)}
              onClone={() => handleClone(agent)}
              onDelete={() => handleDelete(agent)}
              onPublish={() => handlePublish(agent)}
            />
          ))}
        </div>
      )}

      <AgentBuilderFormModal
        open={formModalOpen}
        onOpenChange={setFormModalOpen}
        agent={selectedAgent}
        onSuccess={handleFormSuccess}
      />

      {selectedAgent && (
        <>
          <AgentTestModal
            open={testModalOpen}
            onOpenChange={setTestModalOpen}
            agent={selectedAgent}
          />

          <DeleteConfirmationModal
            open={deleteModalOpen}
            onOpenChange={setDeleteModalOpen}
            agent={selectedAgent}
            onSuccess={handleDeleteSuccess}
          />
        </>
      )}
    </>
  );
}
