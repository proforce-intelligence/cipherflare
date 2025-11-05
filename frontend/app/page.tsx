"use client"

import { useState } from "react"
import { ChevronRight, Database, AlertTriangle, Search, Zap, BarChart3, Bell, RefreshCw } from "lucide-react"
import { Button } from "@/components/ui/button"
import AggregationPage from "./aggregation/page"
import WalletTrackerPage from "./wallet-tracker/page"
import ThreatIntelligencePage from "./threat-intelligence/page"
import InvestigationsPage from "./investigations/page"
import ReportingPage from "./reporting/page"
import DashboardPage from "./dashboard/page"

export default function CipherflareApp() {
  const [activeSection, setActiveSection] = useState("dashboard")
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false)

  return (
    <div className="flex h-screen">
      {/* Sidebar */}
      <div
        className={`${sidebarCollapsed ? "w-16" : "w-70"} bg-neutral-900 border-r border-orange-900/30 transition-all duration-300 fixed md:relative z-50 md:z-auto h-full md:h-auto ${!sidebarCollapsed ? "md:block" : ""}`}
      >
        <div className="p-4">
          <div className="flex items-center justify-between mb-8">
            <div className={`${sidebarCollapsed ? "hidden" : "block"}`}>
              <h1 className="text-orange-500 font-bold text-lg tracking-wider">CIPHERFLARE</h1>
              <p className="text-neutral-500 text-xs">THREAT INTELLIGENCE</p>
            </div>
            <Button
              variant="ghost"
              size="icon"
              onClick={() => setSidebarCollapsed(!sidebarCollapsed)}
              className="text-neutral-400 hover:text-orange-500"
            >
              <ChevronRight
                className={`w-4 h-4 sm:w-5 sm:h-5 transition-transform ${sidebarCollapsed ? "" : "rotate-180"}`}
              />
            </Button>
          </div>

          <nav className="space-y-2">
            {[
              { id: "dashboard", icon: BarChart3, label: "DASHBOARD" },
              { id: "investigations", icon: Search, label: "INVESTIGATIONS" },
              { id: "aggregation", icon: Database, label: "AGGREGATION" },
              { id: "wallet", icon: Zap, label: "WALLET TRACKER" },
              { id: "threats", icon: AlertTriangle, label: "THREAT INTEL" },
              { id: "reporting", icon: BarChart3, label: "REPORTING" },
            ].map((item) => (
              <button
                key={item.id}
                onClick={() => setActiveSection(item.id)}
                className={`w-full flex items-center gap-3 p-3 rounded transition-colors ${
                  activeSection === item.id
                    ? "bg-orange-500/20 text-orange-500 border border-orange-500/50"
                    : "text-neutral-400 hover:text-orange-500 hover:bg-neutral-800"
                }`}
              >
                <item.icon className="w-5 h-5 md:w-5 md:h-5 sm:w-6 sm:h-6" />
                {!sidebarCollapsed && <span className="text-sm font-medium">{item.label}</span>}
              </button>
            ))}
          </nav>

          {!sidebarCollapsed && (
            <div className="mt-8 p-4 bg-neutral-800 border border-orange-900/30 rounded">
              <div className="flex items-center gap-2 mb-2">
                <div className="w-2 h-2 bg-orange-500 rounded-full animate-pulse"></div>
                <span className="text-xs text-orange-500">SYSTEM ONLINE</span>
              </div>
              <div className="text-xs text-neutral-500 space-y-1">
                <div>UPTIME: 847:23:15</div>
                <div>SOURCES: 1,247 ACTIVE</div>
                <div>ALERTS: 89 PENDING</div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Mobile Overlay */}
      {!sidebarCollapsed && (
        <div className="fixed inset-0 bg-black/50 z-40 md:hidden" onClick={() => setSidebarCollapsed(true)} />
      )}

      {/* Main Content */}
      <div className={`flex-1 flex flex-col ${!sidebarCollapsed ? "md:ml-0" : ""}`}>
        {/* Top Toolbar */}
        <div className="h-16 bg-neutral-800 border-b border-orange-900/30 flex items-center justify-between px-6">
          <div className="flex items-center gap-4">
            <div className="text-sm text-neutral-400">
              CIPHERFLARE / <span className="text-orange-500">{activeSection.toUpperCase()}</span>
            </div>
          </div>
          <div className="flex items-center gap-4">
            <div className="text-xs text-neutral-500">LAST UPDATE: 05/06/2025 20:00 UTC</div>
            <Button variant="ghost" size="icon" className="text-neutral-400 hover:text-orange-500">
              <Bell className="w-4 h-4" />
            </Button>
            <Button variant="ghost" size="icon" className="text-neutral-400 hover:text-orange-500">
              <RefreshCw className="w-4 h-4" />
            </Button>
          </div>
        </div>

        {/* Dashboard Content */}
        <div className="flex-1 overflow-auto">
          {activeSection === "dashboard" && <DashboardPage />}
          {activeSection === "aggregation" && <AggregationPage />}
          {activeSection === "wallet" && <WalletTrackerPage />}
          {activeSection === "threats" && <ThreatIntelligencePage />}
          {activeSection === "investigations" && <InvestigationsPage />}
          {activeSection === "reporting" && <ReportingPage />}
        </div>
      </div>
    </div>
  )
}
