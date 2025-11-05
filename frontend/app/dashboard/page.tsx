"use client"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { AlertTriangle, TrendingUp, Database, Zap } from "lucide-react"

export default function DashboardPage() {
  return (
    <div className="p-6 space-y-6">
      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card className="bg-neutral-900 border-orange-900/30">
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-neutral-500 uppercase tracking-wider">Active Threats</p>
                <p className="text-3xl font-bold text-orange-500 font-mono mt-2">247</p>
              </div>
              <AlertTriangle className="w-8 h-8 text-red-500/50" />
            </div>
          </CardContent>
        </Card>

        <Card className="bg-neutral-900 border-orange-900/30">
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-neutral-500 uppercase tracking-wider">Data Sources</p>
                <p className="text-3xl font-bold text-orange-500 font-mono mt-2">1,247</p>
              </div>
              <Database className="w-8 h-8 text-orange-500/50" />
            </div>
          </CardContent>
        </Card>

        <Card className="bg-neutral-900 border-orange-900/30">
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-neutral-500 uppercase tracking-wider">Wallets Tracked</p>
                <p className="text-3xl font-bold text-orange-500 font-mono mt-2">3,891</p>
              </div>
              <Zap className="w-8 h-8 text-yellow-500/50" />
            </div>
          </CardContent>
        </Card>

        <Card className="bg-neutral-900 border-orange-900/30">
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-neutral-500 uppercase tracking-wider">Alerts Today</p>
                <p className="text-3xl font-bold text-orange-500 font-mono mt-2">89</p>
              </div>
              <TrendingUp className="w-8 h-8 text-green-500/50" />
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Main Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Recent Threats */}
        <Card className="lg:col-span-8 bg-neutral-900 border-orange-900/30">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium text-orange-500 tracking-wider">RECENT THREATS</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {[
                { id: "THR-001", severity: "CRITICAL", source: "Dark Web Forum", time: "2 min ago" },
                { id: "THR-002", severity: "HIGH", source: "Breach Database", time: "15 min ago" },
                { id: "THR-003", severity: "MEDIUM", source: "Social Media", time: "1 hour ago" },
                { id: "THR-004", severity: "HIGH", source: "Paste Site", time: "3 hours ago" },
              ].map((threat) => (
                <div
                  key={threat.id}
                  className="flex items-center justify-between p-3 bg-neutral-800 border border-neutral-700 rounded hover:border-orange-500/50 transition-colors cursor-pointer"
                >
                  <div className="flex items-center gap-3">
                    <div
                      className={`w-2 h-2 rounded-full ${
                        threat.severity === "CRITICAL"
                          ? "bg-red-500"
                          : threat.severity === "HIGH"
                            ? "bg-orange-500"
                            : "bg-yellow-500"
                      }`}
                    ></div>
                    <div>
                      <p className="text-sm text-white font-mono">{threat.id}</p>
                      <p className="text-xs text-neutral-400">{threat.source}</p>
                    </div>
                  </div>
                  <div className="text-right">
                    <p className="text-xs text-neutral-500">{threat.time}</p>
                    <p
                      className={`text-xs font-bold ${threat.severity === "CRITICAL" ? "text-red-400" : "text-orange-400"}`}
                    >
                      {threat.severity}
                    </p>
                  </div>
                </div>
              ))}
            </div>
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
      </div>
    </div>
  )
}
