"use client"

import { useEffect } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Progress } from "@/components/ui/progress"
import { Badge } from "@/components/ui/badge"
import { useJob } from "@/hooks/use-api"
import type { Job } from "@/lib/api-client"
import { CheckCircle2, XCircle, Loader2, Clock, AlertCircle } from "lucide-react"
import { toast } from "sonner"
import { formatDistanceToNow } from "date-fns"

interface JobProgressTrackerProps {
  jobId: string
  onComplete?: (job: Job) => void
}

export function JobProgressTracker({ jobId, onComplete }: JobProgressTrackerProps) {
  const { job, isLoading, error } = useJob(jobId)

  useEffect(() => {
    if (job?.status === "completed") {
      toast.success(`Job "${job.job_name}" completed successfully!`, {
        description: `Found ${job.scraped_sites} results`,
      })
      onComplete?.(job)
    } else if (job?.status === "failed") {
      toast.error(`Job "${job.job_name}" failed`, {
        description: job.error || "Unknown error",
      })
    }
  }, [job?.status, job, onComplete])

  if (isLoading && !job) {
    return (
      <Card>
        <CardContent className="flex items-center justify-center py-8">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </CardContent>
      </Card>
    )
  }

  if (error || !job) {
    return (
      <Card>
        <CardContent className="flex items-center justify-center py-8">
          <div className="text-center">
            <AlertCircle className="h-8 w-8 text-destructive mx-auto mb-2" />
            <p className="text-sm text-muted-foreground">Failed to load job status</p>
          </div>
        </CardContent>
      </Card>
    )
  }

  const getStatusIcon = () => {
    switch (job.status) {
      case "completed":
        return <CheckCircle2 className="h-5 w-5 text-green-500" />
      case "failed":
        return <XCircle className="h-5 w-5 text-destructive" />
      case "running":
        return <Loader2 className="h-5 w-5 animate-spin text-blue-500" />
      default:
        return <Clock className="h-5 w-5 text-muted-foreground" />
    }
  }

  const getStatusBadge = () => {
    const variants: Record<string, "default" | "secondary" | "destructive" | "outline"> = {
      pending: "secondary",
      running: "default",
      completed: "outline",
      failed: "destructive",
    }

    return <Badge variant={variants[job.status] || "default"}>{job.status.toUpperCase()}</Badge>
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <CardTitle className="flex items-center gap-2">
              {getStatusIcon()}
              {job.job_name}
            </CardTitle>
            <CardDescription>
              Created {formatDistanceToNow(new Date(job.created_at), { addSuffix: true })}
            </CardDescription>
          </div>
          {getStatusBadge()}
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Progress Bar */}
        <div className="space-y-2">
          <div className="flex items-center justify-between text-sm">
            <span className="text-muted-foreground">Progress</span>
            <span className="font-medium">{job.progress}%</span>
          </div>
          <Progress value={job.progress} className="h-2" />
        </div>

        {/* Stats */}
        <div className="grid grid-cols-2 gap-4 pt-2">
          <div>
            <p className="text-sm text-muted-foreground">Sites Scraped</p>
            <p className="text-2xl font-bold">{job.scraped_sites}</p>
          </div>
          <div>
            <p className="text-sm text-muted-foreground">Total Sites</p>
            <p className="text-2xl font-bold">{job.total_sites}</p>
          </div>
        </div>

        {/* Query */}
        <div className="pt-2">
          <p className="text-sm text-muted-foreground">Search Query</p>
          <p className="text-sm font-medium mt-1">{job.query}</p>
        </div>

        {/* Error Message */}
        {job.error && (
          <div className="bg-destructive/10 text-destructive px-3 py-2 rounded-lg text-sm">{job.error}</div>
        )}

        {/* Completion Info */}
        {job.completed_at && (
          <div className="text-sm text-muted-foreground">
            Completed {formatDistanceToNow(new Date(job.completed_at), { addSuffix: true })}
          </div>
        )}
      </CardContent>
    </Card>
  )
}
