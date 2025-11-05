"use client"

import { useState } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Play, Pause, Plus, Trash2, RefreshCw } from "lucide-react"
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts"

export default function AggregationPage() {
  const [sources, setSources] = useState([
    { id: 1, name: "Dark Web Forum Alpha", status: "collecting", items: 1247, lastUpdate: "2 min ago" },
    { id: 2, name: "Breach Database Aggregator", status: "collecting", items: 3891, lastUpdate: "5 min ago" },
    { id: 3, name: "Paste Site Monitor", status: "idle", items: 567, lastUpdate: "15 min ago" },
    { id: 4, name: "Social Media Tracker", status: "collecting", items: 2134, lastUpdate: "1 min ago" },
    { id: 5, name: "Marketplace Monitor", status: "error", items: 0, lastUpdate: "Connection lost" },
  ])

  const collectionTrendData = [
    { time: "00:00", rate: 200 },
    { time: "04:00", rate: 350 },
    { time: "08:00", rate: 520 },
    { time: "12:00", rate: 680 },
    { time: "16:00", rate: 750 },
    { time: "20:00", rate: 847 },
  ]

  const toggleSourceStatus = (id) => {
    setSources(
      sources.map((s) =>
        s.id === id
          ? {
              ...s,
              status: s.status === "collecting" ? "idle" : "collecting",
              lastUpdate: "Just now",
            }
          : s,
      ),
    )
  }

  const removeSource = (id) => {
    setSources(sources.filter((s) => s.id !== id))
  }

  const totalItems = sources.reduce((sum, s) => sum + s.items, 0)
  const activeSourcesCount = sources.filter((s) => s.status === "collecting").length

  return (
    <div className="p-6 space-y-6">
      {/* Header with Controls */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-orange-400">MULTI-SOURCE AGGREGATION</h2>
          <p className="text-sm text-neutral-500 mt-1">Monitor dark web, breach forums, and social media</p>
        </div>
        <Button className="bg-orange-500 hover:bg-orange-600 text-black">
          <Plus className="w-4 h-4 mr-2" />
          Add Source
        </Button>
      </div>

      {/* Data Collection Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card className="bg-neutral-900 border-orange-900/30">
          <CardContent className="pt-6">
            <p className="text-xs text-neutral-500 uppercase tracking-wider mb-2">Total Items Collected</p>
            <p className="text-3xl font-bold text-orange-400 font-mono">{totalItems.toLocaleString()}</p>
            <p className="text-xs text-green-400 mt-2">↑ 1,247 today</p>
          </CardContent>
        </Card>

        <Card className="bg-neutral-900 border-orange-900/30">
          <CardContent className="pt-6">
            <p className="text-xs text-neutral-500 uppercase tracking-wider mb-2">Collection Rate</p>
            <p className="text-3xl font-bold text-orange-400 font-mono">847/min</p>
            <p className="text-xs text-neutral-400 mt-2">Peak: 1,200/min</p>
          </CardContent>
        </Card>

        <Card className="bg-neutral-900 border-orange-900/30">
          <CardContent className="pt-6">
            <p className="text-xs text-neutral-500 uppercase tracking-wider mb-2">Active Sources</p>
            <p className="text-3xl font-bold text-orange-400 font-mono">
              {activeSourcesCount}/{sources.length}
            </p>
            <p className="text-xs text-yellow-400 mt-2">{sources.length - activeSourcesCount} offline</p>
          </CardContent>
        </Card>
      </div>

      {/* Collection Rate Chart */}
      <Card className="bg-neutral-900 border-orange-900/30">
        <CardHeader className="pb-3">
          <CardTitle className="text-sm font-medium text-orange-400 tracking-wider">COLLECTION RATE (24H)</CardTitle>
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

      {/* Active Sources */}
      <Card className="bg-neutral-900 border-orange-900/30">
        <CardHeader className="pb-3">
          <CardTitle className="text-sm font-medium text-orange-400 tracking-wider">ACTIVE SOURCES</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {sources.map((source) => (
              <div
                key={source.id}
                className="flex items-center justify-between p-4 bg-neutral-800 border border-neutral-700 rounded hover:border-orange-500/50 transition-colors"
              >
                <div className="flex-1">
                  <div className="flex items-center gap-3 mb-2">
                    <div
                      className={`w-2 h-2 rounded-full ${
                        source.status === "collecting"
                          ? "bg-green-500 animate-pulse"
                          : source.status === "idle"
                            ? "bg-yellow-500"
                            : "bg-red-500"
                      }`}
                    ></div>
                    <p className="text-sm text-white font-mono">{source.name}</p>
                  </div>
                  <div className="flex gap-4 text-xs text-neutral-500">
                    <span>Items: {source.items.toLocaleString()}</span>
                    <span>Last: {source.lastUpdate}</span>
                  </div>
                </div>
                <div className="flex gap-2">
                  <Button
                    onClick={() => toggleSourceStatus(source.id)}
                    variant="ghost"
                    size="icon"
                    className="text-neutral-400 hover:text-orange-500"
                  >
                    {source.status === "collecting" ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4" />}
                  </Button>
                  <Button
                    onClick={() => removeSource(source.id)}
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
        </CardContent>
      </Card>

      {/* Recent Collections */}
      <Card className="bg-neutral-900 border-orange-900/30">
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <CardTitle className="text-sm font-medium text-orange-400 tracking-wider">RECENT COLLECTIONS</CardTitle>
            <Button size="sm" variant="ghost" className="text-neutral-400 hover:text-orange-400 h-7">
              <RefreshCw className="w-3 h-3" />
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          <div className="space-y-2 max-h-64 overflow-y-auto">
            {[
              { time: "20:45:32", source: "Dark Web Forum", items: 23, keywords: "ransomware, payment" },
              { time: "20:44:18", source: "Breach Database", items: 5, keywords: "credentials, leaked" },
              { time: "20:43:05", source: "Social Media", items: 12, keywords: "threat actor, campaign" },
              { time: "20:42:41", source: "Paste Site", items: 8, keywords: "config, exploit" },
              { time: "20:41:22", source: "Marketplace", items: 3, keywords: "malware, tools" },
              { time: "20:40:15", source: "Dark Web Forum", items: 18, keywords: "vulnerability, zero-day" },
              { time: "20:39:08", source: "Breach Database", items: 7, keywords: "database, dump" },
            ].map((item, idx) => (
              <div
                key={idx}
                className="flex items-center justify-between p-2 bg-neutral-800 rounded text-xs hover:bg-neutral-700/50 transition-colors"
              >
                <div className="flex-1">
                  <p className="text-neutral-400 font-mono">{item.time}</p>
                  <p className="text-white">{item.source}</p>
                  <p className="text-neutral-500">{item.keywords}</p>
                </div>
                <span className="text-orange-400 font-mono">{item.items} items</span>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
