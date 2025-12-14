"use client"

import { useState } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Play, Pause, Plus, Trash2, RefreshCw, Loader2 } from "lucide-react"
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts"
import { useMonitoringJobs, useStats } from "@/hooks/use-api"
import { apiClient, type MonitoringJobConfig } from "@/lib/api-client"
import { toast } from "sonner"
import { formatDistanceToNow } from "date-fns"

export default function AggregationPage() {
  const [showForm, setShowForm] = useState(false)
  const { monitoringJobs, isLoading, refresh } = useMonitoringJobs()
  const { stats } = useStats()

  const [jobConfig, setJobConfig] = useState<Partial<MonitoringJobConfig>>({
    name: "",
    keywords: [],
    sites: [],
    frequency: "hourly",
    notification_type: "dashboard",
  })
  const [keywordInput, setKeywordInput] = useState("")
  const [siteInput, setSiteInput] = useState("")

  const handleCreateJob = async () => {
    if (!jobConfig.name || !jobConfig.keywords || jobConfig.keywords.length === 0) {
      toast.error("Please provide job name and at least one keyword")
      return
    }

    try {
      await apiClient.createMonitoringJob(jobConfig as MonitoringJobConfig)
      toast.success("Monitoring job created successfully")
      setShowForm(false)
      setJobConfig({
        name: "",
        keywords: [],
        sites: [],
        frequency: "hourly",
        notification_type: "dashboard",
      })
      setKeywordInput("")
      setSiteInput("")
      refresh()
    } catch (error) {
      toast.error("Failed to create monitoring job")
    }
  }

  const addKeyword = () => {
    if (keywordInput.trim()) {
      setJobConfig({
        ...jobConfig,
        keywords: [...(jobConfig.keywords || []), keywordInput.trim()],
      })
      setKeywordInput("")
    }
  }

  const addSite = () => {
    if (siteInput.trim()) {
      setJobConfig({
        ...jobConfig,
        sites: [...(jobConfig.sites || []), siteInput.trim()],
      })
      setSiteInput("")
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

  // Mock collection trend data
  const collectionTrendData = [
    { time: "00:00", rate: 200 },
    { time: "04:00", rate: 350 },
    { time: "08:00", rate: 520 },
    { time: "12:00", rate: 680 },
    { time: "16:00", rate: 750 },
    { time: "20:00", rate: 847 },
  ]

  return (
    <div className="p-6 space-y-6">
      {/* Header - Added functional Create Job button */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-orange-400">CONTINUOUS MONITORING</h2>
          <p className="text-sm text-neutral-500 mt-1">Monitor dark web, breach forums, and paste sites continuously</p>
        </div>
        <Button onClick={() => setShowForm(!showForm)} className="bg-orange-500 hover:bg-orange-600 text-black">
          <Plus className="w-4 h-4 mr-2" />
          {showForm ? "Cancel" : "Create Monitoring Job"}
        </Button>
      </div>

      {showForm && (
        <Card className="bg-neutral-900 border-orange-900/30 animate-in fade-in slide-in-from-top-4 duration-300">
          <CardHeader>
            <CardTitle className="text-sm font-medium text-orange-400">CREATE MONITORING JOB</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Job Name</Label>
                <Input
                  placeholder="e.g., Ransomware Monitor"
                  value={jobConfig.name}
                  onChange={(e) => setJobConfig({ ...jobConfig, name: e.target.value })}
                />
              </div>

              <div className="space-y-2">
                <Label>Frequency</Label>
                <Select
                  value={jobConfig.frequency}
                  onValueChange={(value) => setJobConfig({ ...jobConfig, frequency: value as any })}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="hourly">Hourly</SelectItem>
                    <SelectItem value="daily">Daily</SelectItem>
                    <SelectItem value="weekly">Weekly</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2 md:col-span-2">
                <Label>Keywords to Monitor</Label>
                <div className="flex gap-2">
                  <Input
                    placeholder="Enter keyword"
                    value={keywordInput}
                    onChange={(e) => setKeywordInput(e.target.value)}
                    onKeyPress={(e) => e.key === "Enter" && (e.preventDefault(), addKeyword())}
                  />
                  <Button onClick={addKeyword} type="button" variant="outline">
                    <Plus className="w-4 h-4" />
                  </Button>
                </div>
                {jobConfig.keywords && jobConfig.keywords.length > 0 && (
                  <div className="flex flex-wrap gap-2 mt-2">
                    {jobConfig.keywords.map((keyword) => (
                      <span
                        key={keyword}
                        className="bg-orange-500/20 text-orange-400 px-2 py-1 rounded text-sm flex items-center gap-2"
                      >
                        {keyword}
                        <button
                          onClick={() =>
                            setJobConfig({
                              ...jobConfig,
                              keywords: jobConfig.keywords?.filter((k) => k !== keyword),
                            })
                          }
                          className="hover:text-orange-300"
                        >
                          ✕
                        </button>
                      </span>
                    ))}
                  </div>
                )}
              </div>

              <div className="space-y-2 md:col-span-2">
                <Label>Target Sites (Optional)</Label>
                <div className="flex gap-2">
                  <Input
                    placeholder="Enter .onion URL"
                    value={siteInput}
                    onChange={(e) => setSiteInput(e.target.value)}
                    onKeyPress={(e) => e.key === "Enter" && (e.preventDefault(), addSite())}
                  />
                  <Button onClick={addSite} type="button" variant="outline">
                    <Plus className="w-4 h-4" />
                  </Button>
                </div>
                {jobConfig.sites && jobConfig.sites.length > 0 && (
                  <div className="flex flex-wrap gap-2 mt-2">
                    {jobConfig.sites.map((site) => (
                      <span
                        key={site}
                        className="bg-blue-500/20 text-blue-400 px-2 py-1 rounded text-sm flex items-center gap-2"
                      >
                        {site}
                        <button
                          onClick={() =>
                            setJobConfig({
                              ...jobConfig,
                              sites: jobConfig.sites?.filter((s) => s !== site),
                            })
                          }
                          className="hover:text-blue-300"
                        >
                          ✕
                        </button>
                      </span>
                    ))}
                  </div>
                )}
              </div>
            </div>

            <Button onClick={handleCreateJob} className="w-full bg-orange-500 hover:bg-orange-600 text-black">
              Create Monitoring Job
            </Button>
          </CardContent>
        </Card>
      )}

      {/* Stats - Using real stats */}
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

      {/* Collection Rate Chart */}
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

      {/* Active Monitoring Jobs - Real data with pause/resume/delete */}
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
                  key={job.job_id}
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
                      <p className="text-sm text-white font-mono">{job.name}</p>
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
                      <span>Keywords: {job.keywords?.join(", ")}</span>
                      <span>Frequency: {job.frequency}</span>
                      <span>Created: {formatDistanceToNow(new Date(job.created_at), { addSuffix: true })}</span>
                    </div>
                  </div>
                  <div className="flex gap-2">
                    <Button
                      onClick={() => toggleJobStatus(job.job_id, job.status)}
                      variant="ghost"
                      size="icon"
                      className="text-neutral-400 hover:text-orange-500"
                    >
                      {job.status === "active" ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4" />}
                    </Button>
                    <Button
                      onClick={() => deleteJob(job.job_id)}
                      variant="ghost"
                      size="icon"
                      className="text-neutral-400 hover:text-red-400"
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
              <p>No monitoring jobs yet. Click "Create Monitoring Job" to get started.</p>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
