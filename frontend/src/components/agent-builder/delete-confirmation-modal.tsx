import { useState } from "react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { AgentBuilderListItem } from "@/lib/types";
import { ApiClient } from "@/lib/api";
import { authenticationProviderInstance } from "@/lib/authentication-provider";
import { useToast } from "@/hooks/use-toast";
import { AlertTriangle } from "lucide-react";

const api = new ApiClient(authenticationProviderInstance);

interface DeleteConfirmationModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  agent: AgentBuilderListItem | null;
  onSuccess: () => void;
}

export function DeleteConfirmationModal({
  open,
  onOpenChange,
  agent,
  onSuccess,
}: DeleteConfirmationModalProps) {
  const [deleting, setDeleting] = useState(false);
  const { toast } = useToast();

  const handleDelete = async () => {
    if (!agent) return;

    try {
      setDeleting(true);
      await api.agents().deleteBuilderAgent(agent.id);
      toast({
        title: "Agent deleted",
        description: "The agent has been successfully deleted.",
      });
      onSuccess();
    } catch (error) {
      toast({
        variant: "destructive",
        title: "Error",
        description: "Failed to delete agent. Please try again.",
      });
    } finally {
      setDeleting(false);
    }
  };

  if (!agent) return null;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <AlertTriangle className="h-5 w-5 text-destructive" />
            Delete Agent
          </DialogTitle>
          <DialogDescription>
            Are you sure you want to delete <strong>{agent.name}</strong>? This action cannot be
            undone.
          </DialogDescription>
        </DialogHeader>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={deleting}>
            Cancel
          </Button>
          <Button variant="destructive" onClick={handleDelete} disabled={deleting}>
            {deleting ? "Deleting..." : "Delete"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
