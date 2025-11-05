"use client"

import { useState } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Search, Plus, Download, Share2 } from "lucide-react"

export default function InvestigationsPage() {
  const [searchQuery, setSearchQuery] = useState("")
  const [selectedInvestigation, setSelectedInvestigation] = useState(null)
  const [showDetails, setShowDetails] = useState(false)

  const investigations = [
    {
      id: "INV-001",
      title: "LockBit Ransomware Campaign",
      status: "In Progress",
      entities: 47,
      lastUpdate: "5 min ago",
      progress: 65,
      description: "Tracking LockBit gang ransomware deployment across financial sector",
      relatedEntities: {
        ips: 12,
        domains: 8,
        wallets: 5,
        usernames: 22,
      },
    },
    {
      id: "INV-002",
      title: "Credential Dump Analysis",
      status: "In Progress",
      entities: 23,
      lastUpdate: "1 hour ago",
      progress: 45,
      description: "Analyzing leaked credentials from healthcare provider breach",
      relatedEntities: {
        ips: 3,
        domains: 2,
        wallets: 0,
        usernames: 18,
      },
    },
    {
      id: "INV-003",
      title: "Wallet Tracking - Ransom Payments",
      status: "Completed",
      entities: 89,
      lastUpdate: "3 hours ago",
      progress: 100,
      description: "Completed tracking of ransom payment wallets and fund flows",
      relatedEntities: {
        ips: 5,
        domains: 3,
        wallets: 34,
        usernames: 47,
      },
    },
    {
      id: "INV-004",
      title: "Threat Actor Attribution",
      status: "In Progress",
      entities: 156,
      lastUpdate: "2 hours ago",
      progress: 78,
      description: "Attributing attack patterns to known threat actors",
      relatedEntities: {
        ips: 28,
        domains: 15,
        wallets: 8,
        usernames: 105,
      },
    },
  ]

  const filteredInvestigations = investigations.filter(
    (inv) =>
      inv.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      inv.id.toLowerCase().includes(searchQuery.toLowerCase()),
  )

  const handleExportInvestigation = (inv) => {
    const content = `
INVESTIGATION REPORT
ID: ${inv.id}
Title: ${inv.title}
Status: ${inv.status}
Progress: ${inv.progress}%
Last Updated: ${inv.lastUpdate}

Description:
${inv.description}

Related Entities:
- IP Addresses: ${inv.relatedEntities.ips}
- Domains: ${inv.relatedEntities.domains}
- Wallets: ${inv.relatedEntities.wallets}
- Usernames: ${inv.relatedEntities.usernames}

Total Entities: ${inv.entities}
    `

    const element = document.createElement("a")
    element.setAttribute("href", "data:text/plain;charset=utf-8," + encodeURIComponent(content))
    element.setAttribute("download", `investigation-${inv.id}.txt`)
    element.style.display = "none"
    document.body.appendChild(element)
    element.click()
    document.body.removeChild(element)
  }

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-orange-400">SEARCH & INVESTIGATIONS</h2>
          <p className="text-sm text-neutral-500 mt-1">Deep querying and forensic analysis</p>
        </div>
        <Button className="bg-orange-500 hover:bg-orange-600 text-black">
          <Plus className="w-4 h-4 mr-2" />
          New Investigation
        </Button>
      </div>

      {/* Search Bar */}
      <Card className="bg-neutral-900 border-orange-900/30">
        <CardContent className="pt-6">
          <div className="flex gap-2">
            <div className="flex-1 relative">
              <Search className="absolute left-3 top-3 w-4 h-4 text-neutral-500" />
              <input
                type="text"
                placeholder="Search investigations, entities, IPs, usernames, hashes..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-10 pr-4 py-2 bg-neutral-800 border border-neutral-700 rounded text-white placeholder-neutral-500 focus:outline-none focus:border-orange-500"
              />
            </div>
            <Button className="bg-orange-500 hover:bg-orange-600 text-black">Search</Button>
          </div>
        </CardContent>
      </Card>

      {/* Active Investigations */}
      <Card className="bg-neutral-900 border-orange-900/30">
        <CardHeader className="pb-3">
          <CardTitle className="text-sm font-medium text-orange-400 tracking-wider">
            ACTIVE INVESTIGATIONS ({filteredInvestigations.length})
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {filteredInvestigations.map((inv) => (
              <div
                key={inv.id}
                onClick={() => {
                  setSelectedInvestigation(inv)
                  setShowDetails(true)
                }}
                className={`p-4 rounded cursor-pointer transition-all ${
                  selectedInvestigation?.id === inv.id
                    ? "bg-orange-500/20 border-2 border-orange-500"
                    : "bg-neutral-800 border border-neutral-700 hover:border-orange-500/50"
                }`}
              >
                <div className="flex items-start justify-between mb-3">
                  <div className="flex-1">
                    <p className="text-sm text-orange-400 font-mono">{inv.id}</p>
                    <p className="text-sm text-white mt-1">{inv.title}</p>
                  </div>
                  <span
                    className={`text-xs font-bold px-2 py-1 rounded ${
                      inv.status === "Completed" ? "bg-green-500/20 text-green-400" : "bg-blue-500/20 text-blue-400"
                    }`}
                  >
                    {inv.status}
                  </span>
                </div>

                <div className="mb-2">
                  <div className="w-full bg-neutral-700 rounded-full h-1.5">
                    <div className="bg-orange-500 h-1.5 rounded-full" style={{ width: `${inv.progress}%` }}></div>
                  </div>
                  <p className="text-xs text-neutral-500 mt-1">{inv.progress}% complete</p>
                </div>

                <div className="flex gap-4 text-xs text-neutral-500">
                  <span>Entities: {inv.entities}</span>
                  <span>Updated: {inv.lastUpdate}</span>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Investigation Details */}
      {showDetails && selectedInvestigation && (
        <Card className="bg-neutral-900 border-orange-900/30">
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <CardTitle className="text-sm font-medium text-orange-400 tracking-wider">
                INVESTIGATION DETAILS
              </CardTitle>
              <Button
                onClick={() => setShowDetails(false)}
                variant="ghost"
                className="text-neutral-400 hover:text-orange-400"
              >
                ✕
              </Button>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="bg-neutral-800 p-4 rounded border border-neutral-700">
              <p className="text-sm text-white mb-2">{selectedInvestigation.description}</p>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mt-4">
                <div className="bg-neutral-900 p-3 rounded">
                  <p className="text-xs text-neutral-500">IP Addresses</p>
                  <p className="text-lg text-orange-400 font-mono">{selectedInvestigation.relatedEntities.ips}</p>
                </div>
                <div className="bg-neutral-900 p-3 rounded">
                  <p className="text-xs text-neutral-500">Domains</p>
                  <p className="text-lg text-orange-400 font-mono">{selectedInvestigation.relatedEntities.domains}</p>
                </div>
                <div className="bg-neutral-900 p-3 rounded">
                  <p className="text-xs text-neutral-500">Wallets</p>
                  <p className="text-lg text-orange-400 font-mono">{selectedInvestigation.relatedEntities.wallets}</p>
                </div>
                <div className="bg-neutral-900 p-3 rounded">
                  <p className="text-xs text-neutral-500">Usernames</p>
                  <p className="text-lg text-orange-400 font-mono">{selectedInvestigation.relatedEntities.usernames}</p>
                </div>
              </div>
            </div>

            <div className="flex gap-2">
              <Button
                onClick={() => handleExportInvestigation(selectedInvestigation)}
                className="bg-orange-500 hover:bg-orange-600 text-black flex-1"
              >
                <Download className="w-4 h-4 mr-2" />
                Export Investigation
              </Button>
              <Button
                variant="outline"
                className="border-orange-500/50 text-orange-400 hover:bg-orange-500/10 bg-transparent"
              >
                <Share2 className="w-4 h-4 mr-2" />
                Share
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Entity Graph */}
      <Card className="bg-neutral-900 border-orange-900/30">
        <CardHeader className="pb-3">
          <CardTitle className="text-sm font-medium text-orange-400 tracking-wider">ENTITY RELATIONSHIPS</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="h-64 bg-neutral-800 rounded border border-neutral-700 flex items-center justify-center">
            <div className="text-center">
              <p className="text-neutral-500 text-sm mb-4">Graph visualization of entity relationships</p>
              <div className="flex justify-center gap-8">
                {[
                  { label: "IP Addresses", count: 234 },
                  { label: "Domains", count: 89 },
                  { label: "Wallets", count: 45 },
                  { label: "Usernames", count: 156 },
                ].map((item) => (
                  <div key={item.label} className="text-center hover:scale-110 transition-transform cursor-pointer">
                    <p className="text-2xl font-bold text-orange-400 font-mono">{item.count}</p>
                    <p className="text-xs text-neutral-500 mt-1">{item.label}</p>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Timeline View */}
      <Card className="bg-neutral-900 border-orange-900/30">
        <CardHeader className="pb-3">
          <CardTitle className="text-sm font-medium text-orange-400 tracking-wider">TIMELINE</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {[
              { date: "2025-06-25", events: 12, description: "Campaign initiation detected" },
              { date: "2025-06-24", events: 8, description: "Credential harvesting phase" },
              { date: "2025-06-23", events: 15, description: "Malware distribution" },
              { date: "2025-06-22", events: 5, description: "Reconnaissance activities" },
            ].map((item) => (
              <div key={item.date} className="flex gap-4 hover:bg-neutral-800/50 p-2 rounded transition-colors">
                <div className="text-right min-w-fit">
                  <p className="text-sm text-orange-400 font-mono">{item.date}</p>
                  <p className="text-xs text-neutral-500">{item.events} events</p>
                </div>
                <div className="flex-1 pt-1">
                  <div className="w-full h-1 bg-neutral-800 rounded-full">
                    <div
                      className="h-1 bg-orange-500 rounded-full"
                      style={{ width: `${(item.events / 15) * 100}%` }}
                    ></div>
                  </div>
                  <p className="text-xs text-neutral-400 mt-2">{item.description}</p>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
