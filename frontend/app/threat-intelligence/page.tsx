"use client"

import { useState } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { AlertTriangle, AlertCircle, Bell, Plus, Loader2, Trash2 } from "lucide-react"
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts"
import { useAlerts, useStats } from "@/hooks/use-api"
import { apiClient, type AlertConfig } from "@/lib/api-client"
import { toast } from "sonner"
import { formatDistanceToNow } from "date-fns"

export default function ThreatIntelligencePage() {
  const [showAlertForm, setShowAlertForm] = useState(false)
  const { alerts, isLoading: alertsLoading, refresh: refreshAlerts } = useAlerts()
  const { stats, isLoading: statsLoading } = useStats()
  const [alertFilter, setAlertFilter] = useState("all")

  const [alertConfig, setAlertConfig] = useState<Partial<AlertConfig>>({
    name: "",
    keywords: [],
    notification_type: "dashboard",
    severity: "info",
    email: "",
    webhook_url: "",
    slack_webhook: "",
  })
  const [keywordInput, setKeywordInput] = useState("")

  const handleCreateAlert = async () => {
    if (!alertConfig.name || !alertConfig.keywords || alertConfig.keywords.length === 0) {
      toast.error("Please provide alert name and at least one keyword")
      return
    }

    try {
      await apiClient.createAlertConfig(alertConfig as AlertConfig)
      toast.success("Alert configuration created successfully")
      setShowAlertForm(false)
      setAlertConfig({
        name: "",
        keywords: [],
        notification_type: "dashboard",
        severity: "info",
        email: "",
        webhook_url: "",
        slack_webhook: "",
      })
      setKeywordInput("")
    } catch (error) {
      toast.error("Failed to create alert configuration")
    }
  }

  const addKeyword = () => {
    if (keywordInput.trim()) {
      setAlertConfig({
        ...alertConfig,
        keywords: [...(alertConfig.keywords || []), keywordInput.trim()],
      })
      setKeywordInput("")
    }
  }

  const removeKeyword = (keyword: string) => {
    setAlertConfig({
      ...alertConfig,
      keywords: alertConfig.keywords?.filter((k) => k !== keyword),
    })
  }

  const filteredAlerts = alertFilter === "all" ? alerts : alerts.filter((a) => a.severity === alertFilter)

  const threatTrendData = [
    { time: "00:00", threats: 12 },
    { time: "04:00", threats: 18 },
    { time: "08:00", threats: 25 },
    { time: "12:00", threats: 34 },
    { time: "16:00", threats: 42 },
    { time: "20:00", threats: stats?.active_threats || 47 },
  ]

  return (
    <div className="p-6 space-y-6">
      {/* Header - Added functional alert configuration button */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-orange-400">THREAT INTELLIGENCE & ALERTS</h2>
          <p className="text-sm text-neutral-500 mt-1">Real-time threat detection and risk scoring</p>
        </div>
        <Button
          onClick={() => setShowAlertForm(!showAlertForm)}
          className="bg-orange-500 hover:bg-orange-600 text-black"
        >
          <Bell className="w-4 h-4 mr-2" />
          {showAlertForm ? "Cancel" : "Configure Alerts"}
        </Button>
      </div>

      {showAlertForm && (
        <Card className="bg-neutral-900 border-orange-900/30 animate-in fade-in slide-in-from-top-4 duration-300">
          <CardHeader>
            <CardTitle className="text-sm font-medium text-orange-400">CREATE ALERT CONFIGURATION</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Alert Name</Label>
                <Input
                  placeholder="e.g., Ransomware Alert"
                  value={alertConfig.name}
                  onChange={(e) => setAlertConfig({ ...alertConfig, name: e.target.value })}
                />
              </div>

              <div className="space-y-2">
                <Label>Severity Level</Label>
                <Select
                  value={alertConfig.severity}
                  onValueChange={(value) => setAlertConfig({ ...alertConfig, severity: value as any })}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="info">Info</SelectItem>
                    <SelectItem value="warning">Warning</SelectItem>
                    <SelectItem value="error">Error</SelectItem>
                    <SelectItem value="success">Success</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <Label>Notification Type</Label>
                <Select
                  value={alertConfig.notification_type}
                  onValueChange={(value) => setAlertConfig({ ...alertConfig, notification_type: value as any })}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="dashboard">Dashboard Only</SelectItem>
                    <SelectItem value="email">Email</SelectItem>
                    <SelectItem value="webhook">Webhook</SelectItem>
                    <SelectItem value="slack">Slack</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              {alertConfig.notification_type === "email" && (
                <div className="space-y-2">
                  <Label>Email Address</Label>
                  <Input
                    type="email"
                    placeholder="alerts@example.com"
                    value={alertConfig.email}
                    onChange={(e) => setAlertConfig({ ...alertConfig, email: e.target.value })}
                  />
                </div>
              )}

              {alertConfig.notification_type === "webhook" && (
                <div className="space-y-2">
                  <Label>Webhook URL</Label>
                  <Input
                    placeholder="https://api.example.com/webhook"
                    value={alertConfig.webhook_url}
                    onChange={(e) => setAlertConfig({ ...alertConfig, webhook_url: e.target.value })}
                  />
                </div>
              )}

              {alertConfig.notification_type === "slack" && (
                <div className="space-y-2">
                  <Label>Slack Webhook URL</Label>
                  <Input
                    placeholder="https://hooks.slack.com/services/..."
                    value={alertConfig.slack_webhook}
                    onChange={(e) => setAlertConfig({ ...alertConfig, slack_webhook: e.target.value })}
                  />
                </div>
              )}
            </div>

            <div className="space-y-2">
              <Label>Keywords to Monitor</Label>
              <div className="flex gap-2">
                <Input
                  placeholder="Enter keyword and press Add"
                  value={keywordInput}
                  onChange={(e) => setKeywordInput(e.target.value)}
                  onKeyPress={(e) => e.key === "Enter" && (e.preventDefault(), addKeyword())}
                />
                <Button onClick={addKeyword} type="button" variant="outline">
                  <Plus className="w-4 h-4" />
                </Button>
              </div>
              {alertConfig.keywords && alertConfig.keywords.length > 0 && (
                <div className="flex flex-wrap gap-2 mt-2">
                  {alertConfig.keywords.map((keyword) => (
                    <span
                      key={keyword}
                      className="bg-orange-500/20 text-orange-400 px-2 py-1 rounded text-sm flex items-center gap-2"
                    >
                      {keyword}
                      <button onClick={() => removeKeyword(keyword)} className="hover:text-orange-300">
                        <Trash2 className="w-3 h-3" />
                      </button>
                    </span>
                  ))}
                </div>
              )}
            </div>

            <Button onClick={handleCreateAlert} className="w-full bg-orange-500 hover:bg-orange-600 text-black">
              Create Alert Configuration
            </Button>
          </CardContent>
        </Card>
      )}

      {/* Alert Summary - Using real stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card className="bg-neutral-900 border-red-900/30">
          <CardContent className="pt-6">
            <p className="text-xs text-neutral-500 uppercase tracking-wider mb-2">Error Alerts</p>
            <p className="text-3xl font-bold text-red-400 font-mono">
              {alerts.filter((a) => a.severity === "error").length}
            </p>
            <p className="text-xs text-red-400 mt-2">Require immediate action</p>
          </CardContent>
        </Card>

        <Card className="bg-neutral-900 border-orange-900/30">
          <CardContent className="pt-6">
            <p className="text-xs text-neutral-500 uppercase tracking-wider mb-2">Warnings</p>
            <p className="text-3xl font-bold text-orange-400 font-mono">
              {alerts.filter((a) => a.severity === "warning").length}
            </p>
            <p className="text-xs text-orange-400 mt-2">Needs investigation</p>
          </CardContent>
        </Card>

        <Card className="bg-neutral-900 border-yellow-900/30">
          <CardContent className="pt-6">
            <p className="text-xs text-neutral-500 uppercase tracking-wider mb-2">Info Alerts</p>
            <p className="text-3xl font-bold text-yellow-400 font-mono">
              {alerts.filter((a) => a.severity === "info").length}
            </p>
            <p className="text-xs text-yellow-400 mt-2">For awareness</p>
          </CardContent>
        </Card>

        <Card className="bg-neutral-900 border-orange-900/30">
          <CardContent className="pt-6">
            <p className="text-xs text-neutral-500 uppercase tracking-wider mb-2">Total Alerts</p>
            <p className="text-3xl font-bold text-orange-400 font-mono">{alerts.length}</p>
            <p className="text-xs text-orange-400 mt-2">All time</p>
          </CardContent>
        </Card>
      </div>

      {/* Threat Trend Chart */}
      <Card className="bg-neutral-900 border-orange-900/30">
        <CardHeader className="pb-3">
          <CardTitle className="text-sm font-medium text-orange-400 tracking-wider">THREAT TREND (24H)</CardTitle>
        </CardHeader>
        <CardContent>
          <ResponsiveContainer width="100%" height={250}>
            <LineChart data={threatTrendData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#333" />
              <XAxis dataKey="time" stroke="#666" />
              <YAxis stroke="#666" />
              <Tooltip contentStyle={{ backgroundColor: "#1a1a1a", border: "1px solid #FF6B35" }} />
              <Line type="monotone" dataKey="threats" stroke="#FF6B35" strokeWidth={2} dot={{ fill: "#FF6B35" }} />
            </LineChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>

      {/* Active Alerts - Real alerts from backend */}
      <Card className="bg-neutral-900 border-orange-900/30">
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <CardTitle className="text-sm font-medium text-orange-400 tracking-wider">ACTIVE ALERTS</CardTitle>
            <div className="flex gap-2">
              {["all", "error", "warning", "info"].map((filter) => (
                <Button
                  key={filter}
                  onClick={() => setAlertFilter(filter)}
                  size="sm"
                  className={`h-7 text-xs ${
                    alertFilter === filter
                      ? "bg-orange-500 text-black"
                      : "bg-neutral-800 text-neutral-400 hover:text-orange-400"
                  }`}
                >
                  {filter}
                </Button>
              ))}
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {alertsLoading ? (
            <div className="flex justify-center py-8">
              <Loader2 className="w-8 h-8 animate-spin text-orange-500" />
            </div>
          ) : filteredAlerts.length > 0 ? (
            <div className="space-y-3 max-h-96 overflow-y-auto">
              {filteredAlerts.map((alert) => (
                <div
                  key={alert.id}
                  className="p-4 rounded bg-neutral-800 border border-neutral-700 hover:border-orange-500/50 transition-colors"
                >
                  <div className="flex items-start gap-3 mb-2">
                    {alert.severity === "error" ? (
                      <AlertTriangle className="w-5 h-5 text-red-500 flex-shrink-0 mt-0.5" />
                    ) : (
                      <AlertCircle className="w-5 h-5 text-orange-500 flex-shrink-0 mt-0.5" />
                    )}
                    <div className="flex-1">
                      <p className="text-sm text-white font-mono">{alert.title}</p>
                      <p className="text-sm text-neutral-300 mt-1">{alert.message}</p>
                    </div>
                    <div className="text-right">
                      <p className="text-xs text-neutral-500">
                        {formatDistanceToNow(new Date(alert.created_at), { addSuffix: true })}
                      </p>
                    </div>
                  </div>
                  <div className="flex gap-4 text-xs text-neutral-500">
                    <span className={`font-bold ${alert.severity === "error" ? "text-red-400" : "text-orange-400"}`}>
                      {alert.severity.toUpperCase()}
                    </span>
                    {alert.job_name && <span>Job: {alert.job_name}</span>}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-8 text-neutral-500">
              <Bell className="w-12 h-12 mx-auto mb-3 opacity-50" />
              <p>No alerts matching filter</p>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
