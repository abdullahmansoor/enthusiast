import { useState, useEffect } from "react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Separator } from "@/components/ui/separator";
import { AgentBuilderListItem, AgentBuilderConfig } from "@/lib/types";
import { ApiClient } from "@/lib/api";
import { authenticationProviderInstance } from "@/lib/authentication-provider";
import { useToast } from "@/hooks/use-toast";
import { useApplicationContext } from "@/lib/use-application-context";
import { Loader2, Settings2, MessageSquare, Database, Sparkles } from "lucide-react";
import { ScrollArea } from "@/components/ui/scroll-area";

const api = new ApiClient(authenticationProviderInstance);

interface AgentBuilderFormModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  agent: AgentBuilderListItem | null;
  onSuccess: () => void;
}

export function AgentBuilderFormModal({
  open,
  onOpenChange,
  agent,
  onSuccess,
}: AgentBuilderFormModalProps) {
  const { dataSetId } = useApplicationContext() ?? { dataSetId: null };
  const [loading, setLoading] = useState(false);
  const { toast } = useToast();

  // Form state
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [config, setConfig] = useState<AgentBuilderConfig>({
    model: {
      provider: "openai",
      name: "gpt-4o",
      temperature: 0.7,
      max_tokens: 2000,
    },
    system_prompt: "You are a helpful AI assistant.",
    retrieval: {
      enabled: true,
      top_k: 5,
      similarity_threshold: 0.7,
      reranking_enabled: false,
    },
    max_history_messages: 10,
    enable_citations: true,
  });

  // Load full agent data if editing
  useEffect(() => {
    if (agent && open) {
      setLoading(true);
      api
        .agents()
        .getBuilderAgent(agent.id)
        .then((data) => {
          setName(data.name);
          setDescription(data.description);
          setConfig(data.config);
        })
        .catch(() => {
          toast({
            variant: "destructive",
            title: "Error",
            description: "Failed to load agent data.",
          });
        })
        .finally(() => setLoading(false));
    } else if (!agent && open) {
      // Reset form for new agent
      setName("");
      setDescription("");
      setConfig({
        model: {
          provider: "openai",
          name: "gpt-4o",
          temperature: 0.7,
          max_tokens: 2000,
        },
        system_prompt: "You are a helpful AI assistant.",
        retrieval: {
          enabled: true,
          top_k: 5,
          similarity_threshold: 0.7,
          reranking_enabled: false,
        },
        max_history_messages: 10,
        enable_citations: true,
      });
    }
  }, [agent, open]);

  const handleSubmit = async () => {
    if (!name.trim()) {
      toast({
        variant: "destructive",
        title: "Validation Error",
        description: "Agent name is required.",
      });
      return;
    }

    if (dataSetId === null) {
      toast({
        variant: "destructive",
        title: "Error",
        description: "No dataset selected.",
      });
      return;
    }

    try {
      setLoading(true);
      if (agent) {
        // Update existing agent
        await api.agents().updateBuilderAgent(agent.id, {
          name,
          description,
          config,
        });
        toast({
          title: "Agent updated",
          description: "Your agent has been successfully updated.",
        });
      } else {
        // Create new agent
        await api.agents().createBuilderAgent({
          name,
          description,
          dataset: dataSetId,
          config,
        });
        toast({
          title: "Agent created",
          description: "Your agent has been successfully created.",
        });
      }
      onSuccess();
    } catch (error: any) {
      toast({
        variant: "destructive",
        title: "Error",
        description: error.message || "Failed to save agent.",
      });
    } finally {
      setLoading(false);
    }
  };

  const updateModelConfig = (key: string, value: any) => {
    setConfig((prev) => ({
      ...prev,
      model: { ...prev.model, [key]: value },
    }));
  };

  const updateRetrievalConfig = (key: string, value: any) => {
    setConfig((prev) => ({
      ...prev,
      retrieval: { ...prev.retrieval, [key]: value },
    }));
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-4xl max-h-[90vh] overflow-hidden flex flex-col">
        <DialogHeader>
          <DialogTitle>
            {agent ? `Edit Agent: ${agent.name}` : "Create New Agent"}
          </DialogTitle>
          <DialogDescription>
            Configure your AI agent with custom settings and behavior.
          </DialogDescription>
        </DialogHeader>

        <ScrollArea className="flex-1 pr-4">
          <div className="space-y-6 pb-6">
            {/* Basic Information */}
            <div className="space-y-4">
              <div className="flex items-center gap-2">
                <Sparkles className="h-5 w-5" />
                <h3 className="text-lg font-semibold">Basic Information</h3>
              </div>

              <div className="space-y-2">
                <Label htmlFor="name">Name *</Label>
                <Input
                  id="name"
                  placeholder="My Custom Agent"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="description">Description</Label>
                <Textarea
                  id="description"
                  placeholder="A helpful agent that..."
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  rows={3}
                />
              </div>
            </div>

            <Separator />

            {/* Model Configuration */}
            <div className="space-y-4">
              <div className="flex items-center gap-2">
                <Settings2 className="h-5 w-5" />
                <h3 className="text-lg font-semibold">Model Configuration</h3>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="provider">Provider</Label>
                  <Select
                    value={config.model.provider}
                    onValueChange={(value) => updateModelConfig("provider", value)}
                  >
                    <SelectTrigger id="provider">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="openai">OpenAI</SelectItem>
                      <SelectItem value="anthropic">Anthropic</SelectItem>
                      <SelectItem value="google">Google</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="model">Model</Label>
                  <Select
                    value={config.model.name}
                    onValueChange={(value) => updateModelConfig("name", value)}
                  >
                    <SelectTrigger id="model">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {config.model.provider === "openai" && (
                        <>
                          <SelectItem value="gpt-4o">GPT-4o</SelectItem>
                          <SelectItem value="gpt-4o-mini">GPT-4o Mini</SelectItem>
                          <SelectItem value="gpt-4-turbo">GPT-4 Turbo</SelectItem>
                        </>
                      )}
                      {config.model.provider === "anthropic" && (
                        <>
                          <SelectItem value="claude-3-5-sonnet-20241022">Claude 3.5 Sonnet</SelectItem>
                          <SelectItem value="claude-3-opus-20240229">Claude 3 Opus</SelectItem>
                          <SelectItem value="claude-3-haiku-20240307">Claude 3 Haiku</SelectItem>
                        </>
                      )}
                      {config.model.provider === "google" && (
                        <>
                          <SelectItem value="gemini-pro">Gemini Pro</SelectItem>
                          <SelectItem value="gemini-pro-vision">Gemini Pro Vision</SelectItem>
                        </>
                      )}
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="temperature">
                    Temperature: {config.model.temperature}
                  </Label>
                  <input
                    id="temperature"
                    type="range"
                    min="0"
                    max="2"
                    step="0.1"
                    value={config.model.temperature}
                    onChange={(e) => updateModelConfig("temperature", parseFloat(e.target.value))}
                    className="w-full"
                  />
                  <p className="text-xs text-muted-foreground">
                    Controls randomness: 0 = focused, 2 = creative
                  </p>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="max_tokens">Max Tokens</Label>
                  <Input
                    id="max_tokens"
                    type="number"
                    value={config.model.max_tokens}
                    onChange={(e) => updateModelConfig("max_tokens", parseInt(e.target.value))}
                    min={100}
                    max={8000}
                  />
                </div>
              </div>
            </div>

            <Separator />

            {/* System Prompt */}
            <div className="space-y-4">
              <div className="flex items-center gap-2">
                <MessageSquare className="h-5 w-5" />
                <h3 className="text-lg font-semibold">System Prompt</h3>
              </div>

              <div className="space-y-2">
                <Textarea
                  placeholder="You are a helpful AI assistant that..."
                  value={config.system_prompt}
                  onChange={(e) =>
                    setConfig((prev) => ({ ...prev, system_prompt: e.target.value }))
                  }
                  rows={6}
                  className="font-mono text-sm"
                />
                <p className="text-xs text-muted-foreground">
                  Define your agent's personality, role, and behavior guidelines
                </p>
              </div>
            </div>

            <Separator />

            {/* Retrieval Configuration */}
            <div className="space-y-4">
              <div className="flex items-center gap-2">
                <Database className="h-5 w-5" />
                <h3 className="text-lg font-semibold">Retrieval Configuration</h3>
              </div>

              <div className="flex items-center justify-between">
                <div className="space-y-0.5">
                  <Label>Enable Retrieval</Label>
                  <p className="text-xs text-muted-foreground">
                    Use dataset documents to enhance responses
                  </p>
                </div>
                <Switch
                  checked={config.retrieval.enabled}
                  onCheckedChange={(checked) => updateRetrievalConfig("enabled", checked)}
                />
              </div>

              {config.retrieval.enabled && (
                <div className="grid grid-cols-2 gap-4 pl-4 border-l-2">
                  <div className="space-y-2">
                    <Label htmlFor="top_k">Top K Results</Label>
                    <Input
                      id="top_k"
                      type="number"
                      value={config.retrieval.top_k}
                      onChange={(e) => updateRetrievalConfig("top_k", parseInt(e.target.value))}
                      min={1}
                      max={20}
                    />
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="similarity_threshold">
                      Similarity Threshold: {config.retrieval.similarity_threshold}
                    </Label>
                    <input
                      id="similarity_threshold"
                      type="range"
                      min="0"
                      max="1"
                      step="0.05"
                      value={config.retrieval.similarity_threshold}
                      onChange={(e) =>
                        updateRetrievalConfig("similarity_threshold", parseFloat(e.target.value))
                      }
                      className="w-full"
                    />
                  </div>

                  <div className="flex items-center justify-between col-span-2">
                    <div className="space-y-0.5">
                      <Label>Enable Reranking</Label>
                      <p className="text-xs text-muted-foreground">
                        Improve result quality with reranking
                      </p>
                    </div>
                    <Switch
                      checked={config.retrieval.reranking_enabled}
                      onCheckedChange={(checked) =>
                        updateRetrievalConfig("reranking_enabled", checked)
                      }
                    />
                  </div>
                </div>
              )}
            </div>

            <Separator />

            {/* Additional Settings */}
            <div className="space-y-4">
              <h3 className="text-lg font-semibold">Additional Settings</h3>

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="max_history">Max History Messages</Label>
                  <Input
                    id="max_history"
                    type="number"
                    value={config.max_history_messages}
                    onChange={(e) =>
                      setConfig((prev) => ({
                        ...prev,
                        max_history_messages: parseInt(e.target.value),
                      }))
                    }
                    min={1}
                    max={50}
                  />
                  <p className="text-xs text-muted-foreground">
                    Number of previous messages to include
                  </p>
                </div>

                <div className="flex items-center justify-between">
                  <div className="space-y-0.5">
                    <Label>Enable Citations</Label>
                    <p className="text-xs text-muted-foreground">
                      Show source references in responses
                    </p>
                  </div>
                  <Switch
                    checked={config.enable_citations}
                    onCheckedChange={(checked) =>
                      setConfig((prev) => ({ ...prev, enable_citations: checked }))
                    }
                  />
                </div>
              </div>
            </div>
          </div>
        </ScrollArea>

        <div className="flex justify-end gap-2 pt-4 border-t">
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={loading}>
            Cancel
          </Button>
          <Button onClick={handleSubmit} disabled={loading}>
            {loading ? (
              <>
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                Saving...
              </>
            ) : agent ? (
              "Update Agent"
            ) : (
              "Create Agent"
            )}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
