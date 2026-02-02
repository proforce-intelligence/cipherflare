"use client"

import { useState } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { useMonitoringJobs, useStats } from "@/hooks/use-api"
import { MonitorJobForm } from "@/components/monitor-job-form"
import { MonitorProgressTracker } from "@/components/monitor-progress-tracker"
import { RefreshCw, Loader2, Plus, Play, Pause, Trash2, AlertCircle, CheckCircle2, Clock } from "lucide-react"
import { formatDistanceToNow } from "date-fns"
import { apiClient } from "@/lib/api-client"
import { toast } from "sonner"

export default function MonitoringPage() {
  const { jobs, isLoading, refresh } = useMonitoringJobs()
  const { stats } = useStats()
  const [showForm, setShowForm] = useState(false)
  const [selectedJobId, setSelectedJobId] = useState<string | null>(null)

  const handleJobCreated = (jobId: string) => {
    setSelectedJobId(jobId)
    setShowForm(false)
    refresh()
    toast.success("Monitoring job created successfully!")
  }

  const handleToggleStatus = async (jobId: string, currentStatus: string) => {
    try {
      if (currentStatus === "active") {
        await apiClient.pauseMonitoringJob(jobId)
        toast.success("Monitoring paused")
      } else {
        await apiClient.resumeMonitoringJob(jobId)
        toast.success("Monitoring resumed")
      }
      refresh()
    } catch (error) {
      toast.error("Failed to toggle monitoring status")
    }
  }

  const handleDelete = async (jobId: string) => {
    try {
      await apiClient.deleteMonitoringJob(jobId)
      toast.success("Monitoring job deleted")
      if (selectedJobId === jobId) {
        setSelectedJobId(null)
      }
      refresh()
    } catch (error) {
      toast.error("Failed to delete monitoring job")
    }
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case "active":
        return <Play className="h-4 w-4 text-green-500" />
      case "paused":
        return <Pause className="h-4 w-4 text-yellow-500" />
      case "completed":
        return <CheckCircle2 className="h-4 w-4 text-blue-500" />
      case "failed":
        return <AlertCircle className="h-4 w-4 text-destructive" />
      default:
        return <Clock className="h-4 w-4 text-muted-foreground" />
    }
  }

  const getStatusBadge = (status: string) => {
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
      <Badge variant={variants[status] || "default"} className={colors[status]}>
        {status.toUpperCase()}
      </Badge>
    )
  }

  const activeJobs = jobs?.filter((j) => j.status === "active") || []
  const pausedJobs = jobs?.filter((j) => j.status === "paused") || []
  const completedJobs = jobs?.filter((j) => j.status === "completed") || []
  const failedJobs = jobs?.filter((j) => j.status === "failed") || []

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-orange-400">Continuous Monitoring</h1>
          <p className="text-sm text-neutral-400 mt-1">Track dark web sites continuously with real-time alerts</p>
        </div>
        <Button onClick={() => setShowForm(!showForm)} className="bg-orange-500 hover:bg-orange-600 text-black">
          <Plus className="w-4 h-4 mr-2" />
          {showForm ? "Cancel" : "Setup Monitoring"}
        </Button>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card className="bg-neutral-900 border-orange-900/30">
          <CardHeader className="pb-3">
            <CardTitle className="text-xs text-neutral-500 uppercase tracking-wider">Active Monitors</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-baseline gap-2">
              <p className="text-3xl font-bold text-orange-400 font-mono">{activeJobs.length}</p>
              <p className="text-sm text-green-400">Running</p>
            </div>
          </CardContent>
        </Card>

        <Card className="bg-neutral-900 border-orange-900/30">
          <CardHeader className="pb-3">
            <CardTitle className="text-xs text-neutral-500 uppercase tracking-wider">Total Jobs</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-baseline gap-2">
              <p className="text-3xl font-bold text-orange-400 font-mono">{jobs?.length || 0}</p>
              <p className="text-sm text-neutral-400">All time</p>
            </div>
          </CardContent>
        </Card>

        <Card className="bg-neutral-900 border-orange-900/30">
          <CardHeader className="pb-3">
            <CardTitle className="text-xs text-neutral-500 uppercase tracking-wider">Total Checks</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-baseline gap-2">
              <p className="text-3xl font-bold text-orange-400 font-mono">
                {jobs?.reduce((acc, j) => acc + (j.total_checks || 0), 0) || 0}
              </p>
              <p className="text-sm text-neutral-400">Performed</p>
            </div>
          </CardContent>
        </Card>

        <Card className="bg-neutral-900 border-orange-900/30">
          <CardHeader className="pb-3">
            <CardTitle className="text-xs text-neutral-500 uppercase tracking-wider">Alerts Triggered</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-baseline gap-2">
              <p className="text-3xl font-bold text-orange-400 font-mono">
                {jobs?.reduce((acc, j) => acc + (j.alerts_triggered || 0), 0) || 0}
              </p>
              <p className="text-sm text-yellow-400">Threats</p>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Create Monitoring Form */}
      {showForm && (
        <div className="animate-in fade-in slide-in-from-top-4 duration-300">
          <MonitorJobForm onJobCreated={handleJobCreated} />
        </div>
      )}

      {/* Active Job Progress Tracker */}
      {selectedJobId && (
        <div className="animate-in fade-in slide-in-from-top-4 duration-300">
          <MonitorProgressTracker jobId={selectedJobId} onClose={() => setSelectedJobId(null)} />
        </div>
      )}

      {/* All Monitoring Jobs */}
      <Card className="bg-neutral-900 border-orange-900/30">
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="text-lg text-orange-400">All Monitoring Jobs</CardTitle>
              <CardDescription>Track progress and manage your continuous monitoring operations</CardDescription>
            </div>
            <Button variant="ghost" size="icon" onClick={refresh} className="text-neutral-400 hover:text-orange-500">
              <RefreshCw className={`w-4 h-4 ${isLoading ? "animate-spin" : ""}`} />
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          {isLoading && !jobs ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="h-8 w-8 animate-spin text-orange-500" />
            </div>
          ) : jobs && jobs.length > 0 ? (
            <div className="space-y-3">
              {jobs.map((job) => (
                <div
                  key={job.id}
                  className="flex items-center justify-between p-4 bg-neutral-800/50 border border-neutral-700 rounded-lg hover:border-orange-500/50 transition-all cursor-pointer"
                  onClick={() => setSelectedJobId(job.id)}
                >
                  <div className="flex-1 space-y-2">
                    {/* Job Header */}
                    <div className="flex items-center gap-3">
                      {getStatusIcon(job.status)}
                      <span className="text-sm font-medium text-white font-mono">{job.target_url}</span>
                      {getStatusBadge(job.status)}
                      {job.status === "active" && (
                        <div className="flex items-center gap-2">
                          <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
                          <span className="text-xs text-green-400">Live</span>
                        </div>
                      )}
                    </div>

                    {/* Job Stats */}
                    <div className="flex gap-6 text-xs text-neutral-400">
                      <span>Interval: Every {job.interval_hours}h</span>
                      <span>Checks: {job.total_checks || 0}</span>
                      <span>Findings: {job.findings_count || 0}</span>
                      <span>Alerts: {job.alerts_triggered || 0}</span>
                      {job.last_run_at && (
                        <span>Last: {formatDistanceToNow(new Date(job.last_run_at), { addSuffix: true })}</span>
                      )}
                      {job.next_run_at && (
                        <span className="text-orange-400">
                          Next: {formatDistanceToNow(new Date(job.next_run), { addSuffix: true })}
                        </span>
                      )}
                    </div>

                    {/* Created Date */}
                    <div className="text-xs text-neutral-500">
                      Created {formatDistanceToNow(new Date(job.created_at), { addSuffix: true })}
                    </div>
                  </div>

                  {/* Actions */}
                  <div className="flex gap-2" onClick={(e) => e.stopPropagation()}>
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={() => handleToggleStatus(job.id, job.status)}
                      className="text-neutral-400 hover:text-orange-500"
                      title={job.status === "active" ? "Pause" : "Resume"}
                    >
                      {job.status === "active" ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4" />}
                    </Button>
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={() => handleDelete(job.id)}
                      className="text-neutral-400 hover:text-red-400"
                      title="Delete"
                    >
                      <Trash2 className="w-4 h-4" />
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-12">
              <AlertCircle className="h-12 w-12 mx-auto mb-4 text-neutral-600" />
              <p className="text-neutral-500 mb-2">No monitoring jobs yet</p>
              <p className="text-sm text-neutral-600">
                Click "Setup Monitoring" to create your first continuous monitor
              </p>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Job History Breakdown */}
      {jobs && jobs.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <Card className="bg-neutral-900 border-green-900/30">
            <CardHeader className="pb-3">
              <CardTitle className="text-xs text-neutral-500 uppercase">Active</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-2xl font-bold text-green-400">{activeJobs.length}</p>
            </CardContent>
          </Card>

          <Card className="bg-neutral-900 border-yellow-900/30">
            <CardHeader className="pb-3">
              <CardTitle className="text-xs text-neutral-500 uppercase">Paused</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-2xl font-bold text-yellow-400">{pausedJobs.length}</p>
            </CardContent>
          </Card>

          <Card className="bg-neutral-900 border-blue-900/30">
            <CardHeader className="pb-3">
              <CardTitle className="text-xs text-neutral-500 uppercase">Completed</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-2xl font-bold text-blue-400">{completedJobs.length}</p>
            </CardContent>
          </Card>

          <Card className="bg-neutral-900 border-red-900/30">
            <CardHeader className="pb-3">
              <CardTitle className="text-xs text-neutral-500 uppercase">Failed</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-2xl font-bold text-red-400">{failedJobs.length}</p>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  )
}
