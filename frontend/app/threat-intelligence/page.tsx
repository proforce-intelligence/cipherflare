"use client"

import { useState } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { AlertTriangle, AlertCircle, Download, Bell } from "lucide-react"
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts"

export default function ThreatIntelligencePage() {
  const [selectedAlert, setSelectedAlert] = useState(null)
  const [alertFilter, setAlertFilter] = useState("all")

  const threatTrendData = [
    { time: "00:00", threats: 12 },
    { time: "04:00", threats: 18 },
    { time: "08:00", threats: 25 },
    { time: "12:00", threats: 34 },
    { time: "16:00", threats: 42 },
    { time: "20:00", threats: 47 },
  ]

  const alerts = [
    {
      id: "ALT-001",
      title: "Ransomware Campaign Detected",
      severity: "CRITICAL",
      source: "Dark Web Forum",
      riskScore: 9.2,
      time: "2 min ago",
      description: "LockBit ransomware campaign targeting financial institutions",
      indicators: 45,
    },
    {
      id: "ALT-002",
      title: "Credential Dump - 50K Records",
      severity: "CRITICAL",
      source: "Paste Site",
      riskScore: 8.9,
      time: "15 min ago",
      description: "Leaked credentials from major healthcare provider",
      indicators: 50000,
    },
    {
      id: "ALT-003",
      title: "Suspicious Wallet Activity",
      severity: "HIGH",
      source: "Blockchain Monitor",
      riskScore: 7.5,
      time: "1 hour ago",
      description: "Ransom payment wallet showing unusual transaction patterns",
      indicators: 23,
    },
    {
      id: "ALT-004",
      title: "Phishing Campaign Identified",
      severity: "HIGH",
      source: "Email Monitor",
      riskScore: 7.1,
      time: "3 hours ago",
      description: "Targeted phishing emails impersonating Microsoft",
      indicators: 156,
    },
  ]

  const filteredAlerts = alertFilter === "all" ? alerts : alerts.filter((a) => a.severity === alertFilter)

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-orange-400">THREAT INTELLIGENCE & ALERTS</h2>
          <p className="text-sm text-neutral-500 mt-1">Real-time threat detection and risk scoring</p>
        </div>
        <Button className="bg-orange-500 hover:bg-orange-600 text-black">
          <Bell className="w-4 h-4 mr-2" />
          Configure Alerts
        </Button>
      </div>

      {/* Alert Summary */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card className="bg-neutral-900 border-red-900/30">
          <CardContent className="pt-6">
            <p className="text-xs text-neutral-500 uppercase tracking-wider mb-2">Critical Alerts</p>
            <p className="text-3xl font-bold text-red-400 font-mono">12</p>
            <p className="text-xs text-red-400 mt-2">Require immediate action</p>
          </CardContent>
        </Card>

        <Card className="bg-neutral-900 border-orange-900/30">
          <CardContent className="pt-6">
            <p className="text-xs text-neutral-500 uppercase tracking-wider mb-2">High Priority</p>
            <p className="text-3xl font-bold text-orange-400 font-mono">34</p>
            <p className="text-xs text-orange-400 mt-2">Needs investigation</p>
          </CardContent>
        </Card>

        <Card className="bg-neutral-900 border-yellow-900/30">
          <CardContent className="pt-6">
            <p className="text-xs text-neutral-500 uppercase tracking-wider mb-2">Medium Priority</p>
            <p className="text-3xl font-bold text-yellow-400 font-mono">67</p>
            <p className="text-xs text-yellow-400 mt-2">Monitor closely</p>
          </CardContent>
        </Card>

        <Card className="bg-neutral-900 border-orange-900/30">
          <CardContent className="pt-6">
            <p className="text-xs text-neutral-500 uppercase tracking-wider mb-2">Avg Risk Score</p>
            <p className="text-3xl font-bold text-orange-400 font-mono">7.8/10</p>
            <p className="text-xs text-orange-400 mt-2">Elevated threat level</p>
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

      {/* Active Alerts */}
      <Card className="bg-neutral-900 border-orange-900/30">
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <CardTitle className="text-sm font-medium text-orange-400 tracking-wider">ACTIVE ALERTS</CardTitle>
            <div className="flex gap-2">
              {["all", "CRITICAL", "HIGH"].map((filter) => (
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
          <div className="space-y-3">
            {filteredAlerts.map((alert) => (
              <div
                key={alert.id}
                onClick={() => setSelectedAlert(selectedAlert?.id === alert.id ? null : alert)}
                className={`p-4 rounded cursor-pointer transition-all ${
                  selectedAlert?.id === alert.id
                    ? "bg-orange-500/20 border-2 border-orange-500"
                    : "bg-neutral-800 border border-neutral-700 hover:border-orange-500/50"
                }`}
              >
                <div className="flex items-start gap-3 mb-2">
                  {alert.severity === "CRITICAL" ? (
                    <AlertTriangle className="w-5 h-5 text-red-500 flex-shrink-0 mt-0.5" />
                  ) : (
                    <AlertCircle className="w-5 h-5 text-orange-500 flex-shrink-0 mt-0.5" />
                  )}
                  <div className="flex-1">
                    <p className="text-sm text-white font-mono">{alert.id}</p>
                    <p className="text-sm text-orange-400 mt-1">{alert.title}</p>
                  </div>
                  <div className="text-right">
                    <p className="text-xs text-neutral-500">{alert.time}</p>
                    <p className="text-xs text-orange-400 font-mono mt-1">Risk: {alert.riskScore}</p>
                  </div>
                </div>
                <div className="flex gap-4 text-xs text-neutral-500 ml-8 mb-2">
                  <span>Source: {alert.source}</span>
                  <span className={`font-bold ${alert.severity === "CRITICAL" ? "text-red-400" : "text-orange-400"}`}>
                    {alert.severity}
                  </span>
                </div>

                {selectedAlert?.id === alert.id && (
                  <div className="mt-3 pt-3 border-t border-orange-500/30 ml-8">
                    <p className="text-xs text-neutral-300 mb-2">{alert.description}</p>
                    <p className="text-xs text-neutral-500">
                      Indicators Found: <span className="text-orange-400 font-mono">{alert.indicators}</span>
                    </p>
                    <Button size="sm" className="mt-2 bg-orange-500 hover:bg-orange-600 text-black h-7">
                      <Download className="w-3 h-3 mr-1" />
                      Export IOCs
                    </Button>
                  </div>
                )}
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Threat Attribution */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card className="bg-neutral-900 border-orange-900/30">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium text-orange-400 tracking-wider">THREAT ACTORS</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {[
                { name: "LockBit Gang", confidence: 95, activity: "Ransomware", lastSeen: "2 hours ago" },
                { name: "Scattered Spider", confidence: 87, activity: "Data Theft", lastSeen: "5 hours ago" },
                { name: "Cl0p Group", confidence: 92, activity: "Exploitation", lastSeen: "1 hour ago" },
              ].map((actor) => (
                <div key={actor.name} className="p-3 bg-neutral-800 rounded hover:bg-neutral-700/50 transition-colors">
                  <div className="flex justify-between mb-2">
                    <p className="text-sm text-white font-mono">{actor.name}</p>
                    <span className="text-xs text-orange-400 font-mono">{actor.confidence}%</span>
                  </div>
                  <p className="text-xs text-neutral-500 mb-1">{actor.activity}</p>
                  <p className="text-xs text-neutral-600 mb-2">Last seen: {actor.lastSeen}</p>
                  <div className="w-full bg-neutral-700 rounded-full h-1.5">
                    <div className="bg-orange-500 h-1.5 rounded-full" style={{ width: `${actor.confidence}%` }}></div>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        <Card className="bg-neutral-900 border-orange-900/30">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium text-orange-400 tracking-wider">THREAT PATTERNS</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {[
                { pattern: "Ransomware Deployment", count: 45, trend: "↑", change: "+12%" },
                { pattern: "Credential Harvesting", count: 38, trend: "↑", change: "+8%" },
                { pattern: "Malware Distribution", count: 23, trend: "→", change: "0%" },
                { pattern: "Phishing Campaigns", count: 17, trend: "↓", change: "-5%" },
              ].map((item) => (
                <div
                  key={item.pattern}
                  className="flex items-center justify-between p-2 bg-neutral-800 rounded hover:bg-neutral-700/50 transition-colors"
                >
                  <div className="flex-1">
                    <p className="text-sm text-neutral-300">{item.pattern}</p>
                    <p className="text-xs text-neutral-500">{item.change}</p>
                  </div>
                  <div className="text-right">
                    <p className="text-sm text-orange-400 font-mono">{item.count}</p>
                    <p
                      className={`text-xs ${item.trend === "↑" ? "text-red-400" : item.trend === "↓" ? "text-green-400" : "text-yellow-400"}`}
                    >
                      {item.trend}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
