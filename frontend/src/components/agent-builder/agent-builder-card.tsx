import { AgentBuilderListItem } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Edit, MoreVertical, Copy, Trash2, Play, CheckCircle2, FileText } from "lucide-react";
import { formatDistanceToNow } from "@/lib/date-utils";

interface AgentBuilderCardProps {
  agent: AgentBuilderListItem;
  onEdit: () => void;
  onTest: () => void;
  onClone: () => void;
  onDelete: () => void;
  onPublish: () => void;
}

export function AgentBuilderCard({
  agent,
  onEdit,
  onTest,
  onClone,
  onDelete,
  onPublish,
}: AgentBuilderCardProps) {
  const getStatusBadge = () => {
    switch (agent.status) {
      case "published":
        return (
          <Badge variant="default" className="bg-green-500">
            <CheckCircle2 className="h-3 w-3 mr-1" />
            Published
          </Badge>
        );
      case "draft":
        return (
          <Badge variant="secondary">
            <FileText className="h-3 w-3 mr-1" />
            Draft
          </Badge>
        );
      case "archived":
        return <Badge variant="outline">Archived</Badge>;
      default:
        return null;
    }
  };

  return (
    <Card className="hover:shadow-lg transition-shadow">
      <CardHeader>
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <CardTitle className="text-xl mb-2">{agent.name}</CardTitle>
            <div className="flex items-center gap-2">
              {getStatusBadge()}
              <span className="text-xs text-muted-foreground">
                v{agent.version}
              </span>
            </div>
          </div>
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" size="sm">
                <MoreVertical className="h-4 w-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem onClick={onEdit}>
                <Edit className="h-4 w-4 mr-2" />
                Edit
              </DropdownMenuItem>
              <DropdownMenuItem onClick={onTest}>
                <Play className="h-4 w-4 mr-2" />
                Test
              </DropdownMenuItem>
              <DropdownMenuItem onClick={onClone}>
                <Copy className="h-4 w-4 mr-2" />
                Clone
              </DropdownMenuItem>
              {agent.status === "draft" && (
                <>
                  <DropdownMenuSeparator />
                  <DropdownMenuItem onClick={onPublish}>
                    <CheckCircle2 className="h-4 w-4 mr-2" />
                    Publish
                  </DropdownMenuItem>
                </>
              )}
              <DropdownMenuSeparator />
              <DropdownMenuItem onClick={onDelete} className="text-destructive">
                <Trash2 className="h-4 w-4 mr-2" />
                Delete
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </CardHeader>
      <CardContent>
        <CardDescription className="line-clamp-2 min-h-[40px]">
          {agent.description || "No description provided"}
        </CardDescription>
      </CardContent>
      <CardFooter className="text-xs text-muted-foreground">
        <div className="flex items-center justify-between w-full">
          <span>
            Updated {formatDistanceToNow(new Date(agent.updated_at), { addSuffix: true })}
          </span>
          {agent.published_at && (
            <span>
              Published {formatDistanceToNow(new Date(agent.published_at), { addSuffix: true })}
            </span>
          )}
        </div>
      </CardFooter>
    </Card>
  );
}
