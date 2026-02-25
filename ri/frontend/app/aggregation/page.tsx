"use client"

import { useState } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Play, Pause, Plus, Trash2, RefreshCw, Loader2, Lock, Eye } from "lucide-react"
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts"
import { useMonitoringJobs, useStats } from "@/hooks/use-api"
import { apiClient, type MonitoringJobConfig } from "@/lib/api-client"
import { toast } from "sonner"
import { formatDistanceToNow } from "date-fns"
import { Checkbox } from "@/components/ui/checkbox"
import { LiveMirrorViewer } from "@/components/live-mirror-viewer"

export default function AggregationPage() {
  const [showForm, setShowForm] = useState(false)
  const { monitoringJobs, isLoading, refresh } = useMonitoringJobs()
  const { stats } = useStats()

  const [monitorConfig, setMonitorConfig] = useState<Partial<MonitoringJobConfig>>({
    url: "",
    interval_hours: 6,
    username: "",
    password: "",
    login_path: "",
  })
  const [requiresAuth, setRequiresAuth] = useState(false)

  const [liveMirrorSession, setLiveMirrorSession] = useState<{
    sessionId: string
    targetUrl: string
  } | null>(null)
  const [isStartingLiveMirror, setIsStartingLiveMirror] = useState(false)

  const handleCreateMonitoring = async () => {
    if (!monitorConfig.url) {
      toast.error("Please provide a .onion URL")
      return
    }

    if (!monitorConfig.url.match(/^http:\/\/.*\.onion/)) {
      toast.error("Invalid .onion URL format")
      return
    }

    if (requiresAuth && (!monitorConfig.username || !monitorConfig.password)) {
      toast.error("Please provide authentication credentials")
      return
    }

    try {
      const config: MonitoringJobConfig = {
        url: monitorConfig.url,
        interval_hours: monitorConfig.interval_hours || 6,
      }

      if (requiresAuth) {
        config.username = monitorConfig.username
        config.password = monitorConfig.password
        config.login_path = monitorConfig.login_path || ""
      }

      await apiClient.setupMonitoring(config)
      toast.success("Monitoring job created successfully")
      setShowForm(false)
      setMonitorConfig({
        url: "",
        interval_hours: 6,
        username: "",
        password: "",
        login_path: "",
      })
      setRequiresAuth(false)
      refresh()
    } catch (error) {
      toast.error("Failed to create monitoring job")
    }
  }

  const handleStartLiveMirror = async (url: string) => {
    setIsStartingLiveMirror(true)
    try {
      const session = await apiClient.startLiveMirror(url, false)
      setLiveMirrorSession({
        sessionId: session.session_id,
        targetUrl: url,
      })
      toast.success("Live mirror started")
    } catch (error) {
      toast.error("Failed to start live mirror session")
    } finally {
      setIsStartingLiveMirror(false)
    }
  }

  const toggleJobStatus = async (jobId: string, currentStatus: string) => {
    try {
      if (currentStatus === "active") {
        await apiClient.pauseMonitoringJob(jobId)
        toast.success("Job paused")
      } else {
        await apiClient.resumeMonitoringJob(jobId)
        toast.success("Job resumed")
      }
      refresh()
    } catch (error) {
      toast.error("Failed to toggle job status")
    }
  }

  const deleteJob = async (jobId: string) => {
    try {
      await apiClient.deleteMonitoringJob(jobId)
      toast.success("Job deleted")
      refresh()
    } catch (error) {
      toast.error("Failed to delete job")
    }
  }

  const collectionTrendData = [
    { time: "00:00", rate: 200 },
    { time: "04:00", rate: 350 },
    { time: "08:00", rate: 520 },
    { time: "12:00", rate: 680 },
    { time: "16:00", rate: 750 },
    { time: "20:00", rate: 847 },
  ]

  if (liveMirrorSession) {
    return (
      <div className="p-6 h-[calc(100vh-4rem)]">
        <LiveMirrorViewer
          sessionId={liveMirrorSession.sessionId}
          targetUrl={liveMirrorSession.targetUrl}
          onClose={() => setLiveMirrorSession(null)}
        />
      </div>
    )
  }

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-orange-400">CONTINUOUS MONITORING</h2>
          <p className="text-sm text-neutral-500 mt-1">
            Monitor dark web sites continuously with optional authentication
          </p>
        </div>
        <Button onClick={() => setShowForm(!showForm)} className="bg-orange-500 hover:bg-orange-600 text-black">
          <Plus className="w-4 h-4 mr-2" />
          {showForm ? "Cancel" : "Setup Monitoring"}
        </Button>
      </div>

      {showForm && (
        <Card className="bg-neutral-900 border-orange-900/30 animate-in fade-in slide-in-from-top-4 duration-300">
          <CardHeader>
            <CardTitle className="text-sm font-medium text-orange-400">SETUP MONITORING</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-4">
              <div className="space-y-2">
                <Label>Target .onion URL</Label>
                <Input
                  placeholder="http://example.onion"
                  value={monitorConfig.url}
                  onChange={(e) => setMonitorConfig({ ...monitorConfig, url: e.target.value })}
                />
              </div>

              <div className="space-y-2">
                <Label>Check Interval (hours)</Label>
                <Select
                  value={monitorConfig.interval_hours?.toString()}
                  onValueChange={(value) =>
                    setMonitorConfig({ ...monitorConfig, interval_hours: Number.parseInt(value) })
                  }
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="1">Every hour</SelectItem>
                    <SelectItem value="6">Every 6 hours</SelectItem>
                    <SelectItem value="12">Every 12 hours</SelectItem>
                    <SelectItem value="24">Every 24 hours</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="flex items-center space-x-2 pt-2">
                <Checkbox
                  id="requires-auth"
                  checked={requiresAuth}
                  onCheckedChange={(checked) => setRequiresAuth(checked as boolean)}
                />
                <Label htmlFor="requires-auth" className="flex items-center gap-2 cursor-pointer">
                  <Lock className="w-4 h-4" />
                  Site requires authentication
                </Label>
              </div>

              {requiresAuth && (
                <div className="space-y-4 p-4 bg-neutral-800 rounded-lg border border-orange-900/30">
                  <p className="text-xs text-neutral-400 mb-3">
                    Provide credentials to access authenticated dark web sites. Credentials are encrypted before
                    storage.
                  </p>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label>Username</Label>
                      <Input
                        placeholder="Username"
                        value={monitorConfig.username}
                        onChange={(e) => setMonitorConfig({ ...monitorConfig, username: e.target.value })}
                      />
                    </div>

                    <div className="space-y-2">
                      <Label>Password</Label>
                      <Input
                        type="password"
                        placeholder="Password"
                        value={monitorConfig.password}
                        onChange={(e) => setMonitorConfig({ ...monitorConfig, password: e.target.value })}
                      />
                    </div>

                    <div className="space-y-2 md:col-span-2">
                      <Label>Login Path (optional)</Label>
                      <Input
                        placeholder="/login or leave empty"
                        value={monitorConfig.login_path}
                        onChange={(e) => setMonitorConfig({ ...monitorConfig, login_path: e.target.value })}
                      />
                      <p className="text-xs text-neutral-500">Relative path to login page if different from main URL</p>
                    </div>
                  </div>
                </div>
              )}
            </div>

            <Button onClick={handleCreateMonitoring} className="w-full bg-orange-500 hover:bg-orange-600 text-black">
              Create Monitoring Job
            </Button>
          </CardContent>
        </Card>
      )}

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card className="bg-neutral-900 border-orange-900/30">
          <CardContent className="pt-6">
            <p className="text-xs text-neutral-500 uppercase tracking-wider mb-2">Total Monitoring Jobs</p>
            <p className="text-3xl font-bold text-orange-400 font-mono">{monitoringJobs?.length || 0}</p>
            <p className="text-xs text-green-400 mt-2">
              {monitoringJobs?.filter((j) => j.status === "active").length || 0} active
            </p>
          </CardContent>
        </Card>

        <Card className="bg-neutral-900 border-orange-900/30">
          <CardContent className="pt-6">
            <p className="text-xs text-neutral-500 uppercase tracking-wider mb-2">Search Jobs</p>
            <p className="text-3xl font-bold text-orange-400 font-mono">{stats?.total_searches || 0}</p>
            <p className="text-xs text-neutral-400 mt-2">{stats?.active_jobs || 0} running</p>
          </CardContent>
        </Card>

        <Card className="bg-neutral-900 border-orange-900/30">
          <CardContent className="pt-6">
            <p className="text-xs text-neutral-500 uppercase tracking-wider mb-2">Total Alerts</p>
            <p className="text-3xl font-bold text-orange-400 font-mono">{stats?.active_threats || 0}</p>
            <p className="text-xs text-yellow-400 mt-2">Threat indicators</p>
          </CardContent>
        </Card>
      </div>

      <Card className="bg-neutral-900 border-orange-900/30">
        <CardHeader className="pb-3">
          <CardTitle className="text-sm font-medium text-orange-400 tracking-wider">MONITORING ACTIVITY</CardTitle>
        </CardHeader>
        <CardContent>
          <ResponsiveContainer width="100%" height={250}>
            <LineChart data={collectionTrendData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#333" />
              <XAxis dataKey="time" stroke="#666" />
              <YAxis stroke="#666" />
              <Tooltip contentStyle={{ backgroundColor: "#1a1a1a", border: "1px solid #FF6B35" }} />
              <Line type="monotone" dataKey="rate" stroke="#FF6B35" strokeWidth={2} dot={{ fill: "#FF6B35" }} />
            </LineChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>

      <Card className="bg-neutral-900 border-orange-900/30">
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <CardTitle className="text-sm font-medium text-orange-400 tracking-wider">MONITORING JOBS</CardTitle>
            <Button variant="ghost" size="icon" onClick={refresh} className="text-neutral-400 hover:text-orange-500">
              <RefreshCw className="w-4 h-4" />
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="flex justify-center py-8">
              <Loader2 className="w-8 h-8 animate-spin text-orange-500" />
            </div>
          ) : monitoringJobs && monitoringJobs.length > 0 ? (
            <div className="space-y-3">
              {monitoringJobs.map((job) => (
                <div
                  key={job.id}
                  className="flex items-center justify-between p-4 bg-neutral-800 border border-neutral-700 rounded hover:border-orange-500/50 transition-colors"
                >
                  <div className="flex-1">
                    <div className="flex items-center gap-3 mb-2">
                      <div
                        className={`w-2 h-2 rounded-full ${
                          job.status === "active"
                            ? "bg-green-500 animate-pulse"
                            : job.status === "paused"
                              ? "bg-yellow-500"
                              : "bg-red-500"
                        }`}
                      ></div>
                      <p className="text-sm text-white font-mono">{job.target_url}</p>
                      <span
                        className={`text-xs font-bold px-2 py-1 rounded ${
                          job.status === "active"
                            ? "bg-green-500/20 text-green-400"
                            : "bg-yellow-500/20 text-yellow-400"
                        }`}
                      >
                        {job.status.toUpperCase()}
                      </span>
                    </div>
                    <div className="flex gap-4 text-xs text-neutral-500">
                      <span>Interval: Every {job.interval_hours}h</span>
                      <span>Checks: {job.total_checks}</span>
                      <span>Findings: {job.findings_count}</span>
                      <span>Created: {formatDistanceToNow(new Date(job.created_at), { addSuffix: true })}</span>
                    </div>
                  </div>
                  <div className="flex gap-2">
                    <Button
                      onClick={() => handleStartLiveMirror(job.target_url)}
                      variant="ghost"
                      size="icon"
                      disabled={isStartingLiveMirror}
                      className="text-neutral-400 hover:text-blue-400"
                      title="View Live"
                    >
                      {isStartingLiveMirror ? (
                        <Loader2 className="w-4 h-4 animate-spin" />
                      ) : (
                        <Eye className="w-4 h-4" />
                      )}
                    </Button>
                    <Button
                      onClick={() => toggleJobStatus(job.id, job.status)}
                      variant="ghost"
                      size="icon"
                      className="text-neutral-400 hover:text-orange-500"
                      title={job.status === "active" ? "Pause" : "Resume"}
                    >
                      {job.status === "active" ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4" />}
                    </Button>
                    <Button
                      onClick={() => deleteJob(job.id)}
                      variant="ghost"
                      size="icon"
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
            <div className="text-center py-8 text-neutral-500">
              <RefreshCw className="w-12 h-12 mx-auto mb-3 opacity-50" />
              <p>No monitoring jobs yet. Click "Setup Monitoring" to get started.</p>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
