"use client"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { AlertTriangle, TrendingUp, Database, Zap, Bell, RefreshCw } from "lucide-react"
import { useStats, useRecentJobs } from "@/hooks/use-api"
import { useState } from "react"
import { AlertsDashboard } from "@/components/alerts-dashboard"
import { Loader2 } from "lucide-react"
import { formatDistanceToNow } from "date-fns"

export default function DashboardPage() {
  const [showAlerts, setShowAlerts] = useState(false)
  const { stats, isLoading: statsLoading, refresh: refreshStats } = useStats()
  const { jobs: recentJobs, isLoading: jobsLoading, refresh: refreshJobs } = useRecentJobs(10)

  const handleRefresh = () => {
    refreshStats()
    refreshJobs()
  }

  if (statsLoading) {
    return (
      <div className="flex items-center justify-center h-full">
        <Loader2 className="w-8 h-8 animate-spin text-orange-500" />
      </div>
    )
  }

  return (
    <div className="p-6 space-y-6">
      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card className="bg-neutral-900 border-orange-900/30">
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-neutral-500 uppercase tracking-wider">Active Threats</p>
                <p className="text-3xl font-bold text-orange-500 font-mono mt-2">{stats?.active_threats || 0}</p>
              </div>
              <AlertTriangle className="w-8 h-8 text-red-500/50" />
            </div>
          </CardContent>
        </Card>

        <Card className="bg-neutral-900 border-orange-900/30">
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-neutral-500 uppercase tracking-wider">Total Searches</p>
                <p className="text-3xl font-bold text-orange-500 font-mono mt-2">{stats?.total_searches || 0}</p>
              </div>
              <Database className="w-8 h-8 text-orange-500/50" />
            </div>
          </CardContent>
        </Card>

        <Card className="bg-neutral-900 border-orange-900/30">
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-neutral-500 uppercase tracking-wider">Total Jobs</p>
                <p className="text-3xl font-bold text-orange-500 font-mono mt-2">{stats?.total_jobs || 0}</p>
              </div>
              <Database className="w-8 h-8 text-orange-500/50" />
            </div>
          </CardContent>
        </Card>

        <Card className="bg-neutral-900 border-orange-900/30">
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-neutral-500 uppercase tracking-wider">Active Jobs</p>
                <p className="text-3xl font-bold text-orange-500 font-mono mt-2">{stats?.active_jobs || 0}</p>
              </div>
              <Zap className="w-8 h-8 text-yellow-500/50" />
            </div>
          </CardContent>
        </Card>

        <Card className="bg-neutral-900 border-orange-900/30">
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-neutral-500 uppercase tracking-wider">Completed</p>
                <p className="text-3xl font-bold text-orange-500 font-mono mt-2">{stats?.completed_jobs || 0}</p>
              </div>
              <TrendingUp className="w-8 h-8 text-green-500/50" />
            </div>
          </CardContent>
        </Card>

        <Card className="bg-neutral-900 border-orange-900/30">
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-neutral-500 uppercase tracking-wider">Failed</p>
                <p className="text-3xl font-bold text-orange-500 font-mono mt-2">{stats?.failed_jobs || 0}</p>
              </div>
              <AlertTriangle className="w-8 h-8 text-red-500/50" />
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Alerts Dashboard toggle button and view */}
      <div className="flex justify-between items-center">
        <h3 className="text-lg font-semibold text-orange-400">SYSTEM OVERVIEW</h3>
        <Button onClick={() => setShowAlerts(!showAlerts)} className="bg-orange-500 hover:bg-orange-600 text-black">
          <Bell className="w-4 h-4 mr-2" />
          {showAlerts ? "Hide Alerts" : "View All Alerts"}
        </Button>
      </div>

      {showAlerts && (
        <div className="animate-in fade-in slide-in-from-top-4 duration-300">
          <AlertsDashboard />
        </div>
      )}

      {/* Main Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Recent Jobs */}
        <Card className="lg:col-span-8 bg-neutral-900 border-orange-900/30">
          <CardHeader className="pb-3 flex flex-row items-center justify-between">
            <CardTitle className="text-sm font-medium text-orange-500 tracking-wider">RECENT JOBS</CardTitle>
            <Button
              variant="ghost"
              size="icon"
              className="text-neutral-400 hover:text-orange-500"
              onClick={handleRefresh}
            >
              <RefreshCw className="w-4 h-4" />
            </Button>
          </CardHeader>
          <CardContent>
            {jobsLoading ? (
              <div className="flex justify-center py-8">
                <Loader2 className="w-6 h-6 animate-spin text-orange-500" />
              </div>
            ) : recentJobs && recentJobs.length > 0 ? (
              <div className="space-y-3">
                {recentJobs.slice(0, 5).map((job) => (
                  <div
                    key={job.job_id}
                    className="flex items-center justify-between p-3 bg-neutral-800 border border-neutral-700 rounded hover:border-orange-500/50 transition-colors cursor-pointer"
                  >
                    <div className="flex items-center gap-3">
                      <div
                        className={`w-2 h-2 rounded-full ${
                          job.status === "completed"
                            ? "bg-green-500"
                            : job.status === "running"
                              ? "bg-blue-500 animate-pulse"
                              : job.status === "failed"
                                ? "bg-red-500"
                                : "bg-yellow-500"
                        }`}
                      ></div>
                      <div>
                        <p className="text-sm text-white font-mono">{job.job_name}</p>
                        <p className="text-xs text-neutral-400">{job.query}</p>
                      </div>
                    </div>
                    <div className="text-right">
                      <p className="text-xs text-neutral-500">
                        {formatDistanceToNow(new Date(job.created_at), { addSuffix: true })}
                      </p>
                      <p className={`text-xs font-bold text-orange-400`}>{job.status.toUpperCase()}</p>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center py-8 text-neutral-500">
                <Database className="w-12 h-12 mx-auto mb-3 opacity-50" />
                <p>No recent jobs</p>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Threat Distribution */}
        <Card className="lg:col-span-4 bg-neutral-900 border-orange-900/30">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium text-orange-500 tracking-wider">THREAT DISTRIBUTION</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {[
                { label: "Ransomware", count: 45, percent: 35 },
                { label: "Data Breach", count: 38, percent: 28 },
                { label: "Phishing", count: 32, percent: 24 },
                { label: "Other", count: 13, percent: 13 },
              ].map((item) => (
                <div key={item.label}>
                  <div className="flex justify-between mb-1">
                    <span className="text-xs text-neutral-400">{item.label}</span>
                    <span className="text-xs text-orange-500 font-mono">{item.count}</span>
                  </div>
                  <div className="w-full bg-neutral-800 rounded-full h-2">
                    <div className="bg-orange-500 h-2 rounded-full" style={{ width: `${item.percent}%` }}></div>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Activity Timeline */}
        <Card className="lg:col-span-6 bg-neutral-900 border-orange-900/30">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium text-orange-500 tracking-wider">ACTIVITY TIMELINE</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3 max-h-64 overflow-y-auto">
              {[
                { time: "20:45 UTC", action: "Wallet 0x7f... received 2.5 BTC", type: "wallet" },
                { time: "20:32 UTC", action: "New breach data detected on forum", type: "breach" },
                { time: "20:15 UTC", action: "Ransomware campaign identified", type: "threat" },
                { time: "19:58 UTC", action: "Suspicious transaction pattern flagged", type: "wallet" },
              ].map((log, idx) => (
                <div key={idx} className="flex gap-3 text-xs">
                  <div className="text-neutral-500 font-mono min-w-fit">{log.time}</div>
                  <div className="flex-1 text-neutral-300">{log.action}</div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Top Actors */}
        <Card className="lg:col-span-6 bg-neutral-900 border-orange-900/30">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium text-orange-500 tracking-wider">TOP THREAT ACTORS</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {[
                { name: "LockBit Gang", activity: "Ransomware", risk: "CRITICAL" },
                { name: "Scattered Spider", activity: "Data Theft", risk: "HIGH" },
                { name: "Cl0p Group", activity: "Exploitation", risk: "HIGH" },
                { name: "Unknown APT", activity: "Reconnaissance", risk: "MEDIUM" },
              ].map((actor) => (
                <div key={actor.name} className="flex items-center justify-between p-2 bg-neutral-800 rounded">
                  <div>
                    <p className="text-sm text-white font-mono">{actor.name}</p>
                    <p className="text-xs text-neutral-500">{actor.activity}</p>
                  </div>
                  <span
                    className={`text-xs font-bold px-2 py-1 rounded ${
                      actor.risk === "CRITICAL"
                        ? "bg-red-500/20 text-red-400"
                        : actor.risk === "HIGH"
                          ? "bg-orange-500/20 text-orange-400"
                          : "bg-yellow-500/20 text-yellow-400"
                    }`}
                  >
                    {actor.risk}
                  </span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Quick Stats */}
        <Card className="lg:col-span-4 bg-neutral-900 border-orange-900/30">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium text-orange-500 tracking-wider">QUICK STATS</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div>
                <div className="flex justify-between mb-1">
                  <span className="text-xs text-neutral-400">Completed Jobs</span>
                  <span className="text-xs text-orange-500 font-mono">{stats?.completed_jobs || 0}</span>
                </div>
                <div className="w-full bg-neutral-800 rounded-full h-2">
                  <div
                    className="bg-green-500 h-2 rounded-full"
                    style={{
                      width: `${stats?.total_searches ? ((stats.completed_jobs || 0) / stats.total_searches) * 100 : 0}%`,
                    }}
                  ></div>
                </div>
              </div>
              <div>
                <div className="flex justify-between mb-1">
                  <span className="text-xs text-neutral-400">Failed Jobs</span>
                  <span className="text-xs text-orange-500 font-mono">{stats?.failed_jobs || 0}</span>
                </div>
                <div className="w-full bg-neutral-800 rounded-full h-2">
                  <div
                    className="bg-red-500 h-2 rounded-full"
                    style={{
                      width: `${stats?.total_searches ? ((stats.failed_jobs || 0) / stats.total_searches) * 100 : 0}%`,
                    }}
                  ></div>
                </div>
              </div>
              <div>
                <div className="flex justify-between mb-1">
                  <span className="text-xs text-neutral-400">Running Jobs</span>
                  <span className="text-xs text-orange-500 font-mono">{stats?.active_jobs || 0}</span>
                </div>
                <div className="w-full bg-neutral-800 rounded-full h-2">
                  <div
                    className="bg-blue-500 h-2 rounded-full"
                    style={{
                      width: `${stats?.total_searches ? ((stats.active_jobs || 0) / stats.total_searches) * 100 : 0}%`,
                    }}
                  ></div>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
