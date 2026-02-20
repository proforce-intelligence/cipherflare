"use client"

import { useEffect } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Progress } from "@/components/ui/progress"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { CheckCircle2, XCircle, Loader2, Clock, AlertCircle, X, Pause } from "lucide-react"
import { toast } from "sonner"
import { formatDistanceToNow } from "date-fns"
import { useMonitoringJobs, useMonitoringResults } from "@/hooks/use-api"

interface MonitorProgressTrackerProps {
  jobId: string
  onClose?: () => void
}

export function MonitorProgressTracker({ jobId, onClose }: MonitorProgressTrackerProps) {
  const { jobs, isLoading, error } = useMonitoringJobs()
  const { results, isLoading: isLoadingResults } = useMonitoringResults(jobId)
  const job = jobs?.find((j) => j.id === jobId)

  useEffect(() => {
    if (job?.status === "completed") {
      toast.success(`Monitoring job completed`, {
        description: `Total checks: ${job.total_checks}`,
      })
    } else if (job?.status === "failed") {
      toast.error(`Monitoring job failed`, {
        description: "Check logs for details",
      })
    }
  }, [job?.status, job])

  if (isLoading && !job) {
    return (
      <Card className="bg-neutral-900 border-orange-900/30">
        <CardContent className="flex items-center justify-center py-8">
          <Loader2 className="h-8 w-8 animate-spin text-orange-500" />
        </CardContent>
      </Card>
    )
  }

  if (error || !job) {
    return (
      <Card className="bg-neutral-900 border-red-900/30">
        <CardContent className="flex items-center justify-center py-8">
          <div className="text-center">
            <AlertCircle className="h-8 w-8 text-destructive mx-auto mb-2" />
            <p className="text-sm text-neutral-400">Failed to load monitoring job status</p>
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
      case "active":
        return <Loader2 className="h-5 w-5 animate-spin text-orange-500" />
      case "paused":
        return <Pause className="h-5 w-5 text-yellow-500" />
      default:
        return <Clock className="h-5 w-5 text-neutral-500" />
    }
  }

  const getStatusBadge = () => {
    const variants: Record<string, "default" | "secondary" | "destructive" | "outline"> = {
      active: "default",
      paused: "secondary",
      completed: "outline",
      failed: "destructive",
    }

    const colors: Record<string, string> = {
      active: "bg-green-500/10 text-green-500 border-green-500/20",
      paused: "bg-yellow-500/10 text-yellow-500 border-yellow-500/20",
      completed: "bg-blue-500/10 text-blue-500 border-blue-500/20",
      failed: "bg-red-500/10 text-red-500 border-red-500/20",
    }

    return (
      <Badge variant={variants[job.status] || "default"} className={colors[job.status]}>
        {job.status.toUpperCase()}
      </Badge>
    )
  }

  // Calculate progress based on time until next run
  const getProgress = () => {
    if (job.status === "completed") return 100
    if (job.status === "failed") return 0
    if (job.status === "paused") return 50

    // For active jobs, calculate progress based on time since last run
    if (job.last_run_at && job.next_run_at) {
      const lastRun = new Date(job.last_run_at).getTime()
      const nextRun = new Date(job.next_run_at).getTime()
      const now = Date.now()
      const elapsed = now - lastRun
      const total = nextRun - lastRun
      return Math.min(95, Math.max(5, (elapsed / total) * 100))
    }

    return 10
  }

  return (
    <Card className="bg-neutral-900 border-orange-900/30">
      <CardHeader>
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <CardTitle className="flex items-center gap-2 text-orange-400">
              {getStatusIcon()}
              Monitoring: {job.target_url}
            </CardTitle>
            <CardDescription>
              Created {formatDistanceToNow(new Date(job.created_at), { addSuffix: true })}
            </CardDescription>
          </div>
          <div className="flex items-center gap-2">
            {getStatusBadge()}
            {onClose && (
              <Button variant="ghost" size="icon" onClick={onClose} className="text-neutral-400 hover:text-orange-500">
                <X className="h-4 w-4" />
              </Button>
            )}
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Progress Bar */}
        <div className="space-y-2">
          <div className="flex items-center justify-between text-sm">
            <span className="text-neutral-400">Progress to Next Check</span>
            <span className="font-medium text-orange-400">{Math.round(getProgress())}%</span>
          </div>
          <Progress value={getProgress()} className="h-2 bg-neutral-800" />
        </div>

        {/* Stats */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 pt-2">
          <div className="space-y-1">
            <p className="text-xs text-neutral-500">Total Checks</p>
            <p className="text-2xl font-bold text-orange-400">{job.total_checks || 0}</p>
          </div>
          <div className="space-y-1">
            <p className="text-xs text-neutral-500">Findings</p>
            <p className="text-2xl font-bold text-orange-400">{job.findings_count || 0}</p>
          </div>
          <div className="space-y-1">
            <p className="text-xs text-neutral-500">Alerts</p>
            <p className="text-2xl font-bold text-yellow-400">{job.alerts_triggered || 0}</p>
          </div>
          <div className="space-y-1">
            <p className="text-xs text-neutral-500">Interval</p>
            <p className="text-2xl font-bold text-orange-400">{job.interval_hours}h</p>
          </div>
        </div>

        {/* Timing Info */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 pt-2">
          {job.last_run_at && (
            <div className="p-3 bg-neutral-800 rounded-lg border border-neutral-700">
              <p className="text-xs text-neutral-500 mb-1">Last Check</p>
              <p className="text-sm font-medium text-white">
                {formatDistanceToNow(new Date(job.last_run_at), { addSuffix: true })}
              </p>
            </div>
          )}
          {job.next_run_at && job.status === "active" && (
            <div className="p-3 bg-neutral-800 rounded-lg border border-orange-900/30">
              <p className="text-xs text-neutral-500 mb-1">Next Check</p>
              <p className="text-sm font-medium text-orange-400">
                {formatDistanceToNow(new Date(job.next_run_at), { addSuffix: true })}
              </p>
            </div>
          )}
        </div>

        {/* Status Message */}
        {job.status === "active" && (
          <div className="flex items-center gap-2 p-3 bg-green-500/10 border border-green-500/20 rounded-lg">
            <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
            <p className="text-sm text-green-400">Monitoring active - checking every {job.interval_hours} hours</p>
          </div>
        )}

        {job.status === "paused" && (
          <div className="flex items-center gap-2 p-3 bg-yellow-500/10 border border-yellow-500/20 rounded-lg">
            <Pause className="w-4 h-4 text-yellow-500" />
            <p className="text-sm text-yellow-400">Monitoring paused - resume to continue checks</p>
          </div>
        )}

        {/* Results Section */}
        <div className="pt-4 border-t border-neutral-800">
          <h4 className="text-sm font-semibold text-neutral-300 mb-3 flex items-center justify-between">
            Recent Findings
            <Badge variant="outline" className="text-[10px] uppercase font-mono">
              {results?.length || 0} Total
            </Badge>
          </h4>
          
          {isLoadingResults ? (
            <div className="flex justify-center py-4">
              <Loader2 className="h-4 w-4 animate-spin text-orange-500" />
            </div>
          ) : results && results.length > 0 ? (
            <div className="space-y-2 max-h-[300px] overflow-y-auto pr-2 custom-scrollbar">
              {results.map((res: any) => (
                <div key={res.id} className="p-3 bg-neutral-800/30 border border-neutral-700/50 rounded-lg hover:border-orange-500/30 transition-colors">
                  <div className="flex items-start justify-between gap-2 mb-1">
                    <span className="text-xs font-medium text-white line-clamp-1">{res.title || "Untitled Finding"}</span>
                    <Badge className={`text-[10px] h-4 px-1 ${
                      res.risk_level === 'critical' ? 'bg-red-500/20 text-red-400' :
                      res.risk_level === 'high' ? 'bg-orange-500/20 text-orange-400' :
                      res.risk_level === 'medium' ? 'bg-yellow-500/20 text-yellow-400' :
                      'bg-green-500/20 text-green-400'
                    }`}>
                      {res.risk_level?.toUpperCase()}
                    </Badge>
                  </div>
                  <p className="text-[10px] text-neutral-500 font-mono mb-2 truncate">{res.target_url}</p>
                  <p className="text-[11px] text-neutral-400 line-clamp-2 mb-2 italic">
                    "{res.text_excerpt?.substring(0, 150)}..."
                  </p>
                  <div className="flex items-center justify-between">
                    <span className="text-[10px] text-neutral-600">
                      {res.detected_at ? formatDistanceToNow(new Date(res.detected_at), { addSuffix: true }) : 'Just now'}
                    </span>
                    {res.alerts_triggered?.length > 0 && (
                      <span className="text-[10px] text-yellow-500 flex items-center gap-1">
                        <AlertCircle className="w-2 h-2" />
                        {res.alerts_triggered.length} Alerts
                      </span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-6 border border-dashed border-neutral-800 rounded-lg">
              <Clock className="h-6 w-6 text-neutral-700 mx-auto mb-2" />
              <p className="text-[11px] text-neutral-500">No findings yet from this monitor.</p>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  )
}
