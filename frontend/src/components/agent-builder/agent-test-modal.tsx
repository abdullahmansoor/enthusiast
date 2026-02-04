import { useState } from "react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { AgentBuilderListItem, AgentTestResponse } from "@/lib/types";
import { ApiClient } from "@/lib/api";
import { authenticationProviderInstance } from "@/lib/authentication-provider";
import { useToast } from "@/hooks/use-toast";
import { Send, Loader2 } from "lucide-react";
import { Alert, AlertDescription } from "@/components/ui/alert";

const api = new ApiClient(authenticationProviderInstance);

interface AgentTestModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  agent: AgentBuilderListItem;
}

export function AgentTestModal({ open, onOpenChange, agent }: AgentTestModalProps) {
  const [message, setMessage] = useState("");
  const [response, setResponse] = useState<AgentTestResponse | null>(null);
  const [testing, setTesting] = useState(false);
  const { toast } = useToast();

  const handleTest = async () => {
    if (!message.trim()) {
      toast({
        variant: "destructive",
        title: "Error",
        description: "Please enter a message to test.",
      });
      return;
    }

    try {
      setTesting(true);
      setResponse(null);
      const result = await api.agents().testBuilderAgent(agent.id, message);
      setResponse(result);
    } catch (error: any) {
      toast({
        variant: "destructive",
        title: "Test failed",
        description: error.message || "Failed to test agent. Please try again.",
      });
    } finally {
      setTesting(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) {
      e.preventDefault();
      handleTest();
    }
  };

  const handleClose = () => {
    setMessage("");
    setResponse(null);
    onOpenChange(false);
  };

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Test Agent: {agent.name}</DialogTitle>
          <DialogDescription>
            Send a test message to see how your agent responds.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          <div className="space-y-2">
            <label className="text-sm font-medium">Your Message</label>
            <Textarea
              placeholder="Type your test message here..."
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              onKeyDown={handleKeyDown}
              rows={4}
              className="resize-none"
            />
            <p className="text-xs text-muted-foreground">
              Press Ctrl+Enter (Cmd+Enter on Mac) to send
            </p>
          </div>

          <Button onClick={handleTest} disabled={testing || !message.trim()} className="w-full">
            {testing ? (
              <>
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                Testing...
              </>
            ) : (
              <>
                <Send className="h-4 w-4 mr-2" />
                Send Test Message
              </>
            )}
          </Button>

          {response && (
            <div className="space-y-3">
              <div className="space-y-2">
                <label className="text-sm font-medium">Agent Response</label>
                <Alert>
                  <AlertDescription className="whitespace-pre-wrap">
                    {response.response}
                  </AlertDescription>
                </Alert>
              </div>

              {response.metadata && (
                <div className="space-y-2">
                  <label className="text-sm font-medium">Metadata</label>
                  <div className="text-xs space-y-1 p-3 bg-muted rounded-md">
                    {response.metadata.model_used && (
                      <div>
                        <span className="font-medium">Model:</span> {response.metadata.model_used}
                      </div>
                    )}
                    {response.metadata.processing_time && (
                      <div>
                        <span className="font-medium">Processing Time:</span>{" "}
                        {response.metadata.processing_time.toFixed(2)}s
                      </div>
                    )}
                    {response.metadata.retrieved_context && response.metadata.retrieved_context.length > 0 && (
                      <div>
                        <span className="font-medium">Retrieved Contexts:</span>{" "}
                        {response.metadata.retrieved_context.length} document(s)
                      </div>
                    )}
                    <div>
                      <span className="font-medium">Conversation ID:</span> {response.conversation_id}
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}
