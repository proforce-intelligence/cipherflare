"use client"

import { useState } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Download, Send, Eye, FileText, BarChart3, AlertCircle } from "lucide-react"
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts"

export default function ReportingPage() {
  const [reportType, setReportType] = useState("comprehensive")
  const [selectedReport, setSelectedReport] = useState(null)
  const [showPreview, setShowPreview] = useState(false)

  const reportTypes = [
    {
      id: "comprehensive",
      name: "Comprehensive Threat Report",
      description: "Complete analysis with all threat data, indicators, and recommendations",
      icon: FileText,
    },
    {
      id: "executive",
      name: "Executive Summary",
      description: "High-level overview for management and stakeholders",
      icon: BarChart3,
    },
    {
      id: "technical",
      name: "Technical Analysis",
      description: "Detailed IOCs, TTPs, and technical indicators",
      icon: AlertCircle,
    },
  ]

  const threatData = [
    { category: "Ransomware", count: 45, severity: "Critical" },
    { category: "Phishing", count: 128, severity: "High" },
    { category: "Data Breach", count: 23, severity: "Critical" },
    { category: "Malware", count: 67, severity: "High" },
    { category: "DDoS", count: 12, severity: "Medium" },
  ]

  const generatedReports = [
    {
      id: "RPT-001",
      title: "LockBit Campaign Analysis",
      type: "Comprehensive",
      date: "2025-06-25",
      status: "Completed",
      threats: 45,
      indicators: 234,
      size: "2.4 MB",
    },
    {
      id: "RPT-002",
      title: "Credential Dump Report",
      type: "Technical",
      date: "2025-06-24",
      status: "Completed",
      threats: 12,
      indicators: 89,
      size: "1.8 MB",
    },
    {
      id: "RPT-003",
      title: "Weekly Threat Summary",
      type: "Executive",
      date: "2025-06-23",
      status: "Completed",
      threats: 156,
      indicators: 567,
      size: "3.2 MB",
    },
    {
      id: "RPT-004",
      title: "Wallet Tracking Report",
      type: "Technical",
      date: "2025-06-22",
      status: "Completed",
      threats: 8,
      indicators: 45,
      size: "1.2 MB",
    },
  ]

  const handleGenerateReport = () => {
    const newReport = {
      id: `RPT-${String(generatedReports.length + 1).padStart(3, "0")}`,
      title: `${reportTypes.find((r) => r.id === reportType)?.name} - ${new Date().toLocaleDateString()}`,
      type: reportTypes.find((r) => r.id === reportType)?.name,
      date: new Date().toISOString().split("T")[0],
      status: "Completed",
      threats: Math.floor(Math.random() * 200),
      indicators: Math.floor(Math.random() * 500),
      size: `${(Math.random() * 3 + 1).toFixed(1)} MB`,
    }
    setSelectedReport(newReport)
    setShowPreview(true)
  }

  const handleDownloadReport = (report) => {
    const reportContent = `
================================================================================
                        THREAT INTELLIGENCE REPORT
================================================================================

Report ID: ${report.id}
Title: ${report.title}
Type: ${report.type}
Generated: ${new Date().toLocaleString()}
Status: ${report.status}

================================================================================
                            EXECUTIVE SUMMARY
================================================================================

Total Threats Identified: ${report.threats}
Total Indicators: ${report.indicators}
Report Classification: TOP SECRET

This comprehensive threat intelligence report provides detailed analysis of
current threat landscape, including threat actors, attack patterns, and
recommended mitigation strategies.

================================================================================
                          THREAT DISTRIBUTION
================================================================================

${threatData.map((t) => `${t.category.padEnd(20)} | Count: ${String(t.count).padStart(3)} | Severity: ${t.severity}`).join("\n")}

================================================================================
                        THREAT ACTOR PROFILES
================================================================================

1. LockBit Gang
   - Threat Level: CRITICAL
   - Known Targets: Financial Institutions, Healthcare
   - Attack Vector: Ransomware
   - Last Seen: 2 hours ago

2. Wizard Spider
   - Threat Level: CRITICAL
   - Known Targets: Enterprise Networks
   - Attack Vector: Trojan, Ransomware
   - Last Seen: 4 hours ago

3. Scattered Spider
   - Threat Level: HIGH
   - Known Targets: Technology Companies
   - Attack Vector: Social Engineering, Phishing
   - Last Seen: 1 day ago

================================================================================
                      INDICATORS OF COMPROMISE (IOCs)
================================================================================

IP Addresses:
- 192.168.1.100 (Malware C2)
- 10.0.0.50 (Phishing Server)
- 172.16.0.25 (Data Exfiltration)

File Hashes (SHA256):
- a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3x4y5z6a7b8c9d0e1f2
- b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3x4y5z6a7b8c9d0e1f2g3

Domains:
- malicious-domain.com
- phishing-site.net
- c2-server.ru

================================================================================
                         RECOMMENDATIONS
================================================================================

1. Immediate Actions:
   - Block identified IOCs at network perimeter
   - Scan systems for indicators of compromise
   - Review access logs for suspicious activity

2. Short-term (1-2 weeks):
   - Implement additional email filtering
   - Conduct security awareness training
   - Update incident response procedures

3. Long-term (1-3 months):
   - Deploy advanced threat detection
   - Implement zero-trust architecture
   - Establish threat intelligence sharing

================================================================================
                      REPORT CLASSIFICATION
================================================================================

Classification: TOP SECRET
Distribution: Authorized Personnel Only
Handling: Secure Channels Only

This report contains sensitive threat intelligence information.
Unauthorized distribution is prohibited.

================================================================================
Report Generated by: Cipherflare Threat Intelligence Platform
Report Version: 1.0
================================================================================
    `

    const element = document.createElement("a")
    element.setAttribute("href", "data:text/plain;charset=utf-8," + encodeURIComponent(reportContent))
    element.setAttribute("download", `${report.id}-threat-report.txt`)
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
          <h2 className="text-2xl font-bold text-orange-400">INTEGRATION & REPORTING</h2>
          <p className="text-sm text-neutral-500 mt-1">Generate comprehensive threat intelligence reports</p>
        </div>
      </div>

      {/* Report Generator */}
      <Card className="bg-neutral-900 border-orange-900/30">
        <CardHeader className="pb-3">
          <CardTitle className="text-sm font-medium text-orange-400 tracking-wider">REPORT GENERATOR</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <p className="text-sm text-neutral-300 mb-3">Select Report Type:</p>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
              {reportTypes.map((type) => (
                <div
                  key={type.id}
                  onClick={() => setReportType(type.id)}
                  className={`p-4 rounded cursor-pointer transition-all ${
                    reportType === type.id
                      ? "bg-orange-500/20 border-2 border-orange-500"
                      : "bg-neutral-800 border border-neutral-700 hover:border-orange-500/50"
                  }`}
                >
                  <type.icon className="w-5 h-5 text-orange-400 mb-2" />
                  <p className="text-sm font-mono text-white">{type.name}</p>
                  <p className="text-xs text-neutral-500 mt-1">{type.description}</p>
                </div>
              ))}
            </div>
          </div>

          <div className="flex gap-2 pt-4">
            <Button onClick={handleGenerateReport} className="bg-orange-500 hover:bg-orange-600 text-black flex-1">
              <FileText className="w-4 h-4 mr-2" />
              Generate Report
            </Button>
            <Button
              onClick={() => setShowPreview(!showPreview)}
              variant="outline"
              className="border-orange-500/50 text-orange-400 hover:bg-orange-500/10"
            >
              <Eye className="w-4 h-4 mr-2" />
              Preview
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Report Preview */}
      {showPreview && selectedReport && (
        <Card className="bg-neutral-900 border-orange-900/30">
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <CardTitle className="text-sm font-medium text-orange-400 tracking-wider">REPORT PREVIEW</CardTitle>
              <Button
                onClick={() => setShowPreview(false)}
                variant="ghost"
                className="text-neutral-400 hover:text-orange-400"
              >
                ✕
              </Button>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="bg-neutral-800 p-4 rounded border border-neutral-700 space-y-3">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-xs text-neutral-500 uppercase tracking-wider mb-1">Report ID</p>
                  <p className="text-sm text-orange-400 font-mono">{selectedReport.id}</p>
                </div>
                <div>
                  <p className="text-xs text-neutral-500 uppercase tracking-wider mb-1">Type</p>
                  <p className="text-sm text-white">{selectedReport.type}</p>
                </div>
                <div>
                  <p className="text-xs text-neutral-500 uppercase tracking-wider mb-1">Total Threats</p>
                  <p className="text-sm text-orange-400 font-mono">{selectedReport.threats}</p>
                </div>
                <div>
                  <p className="text-xs text-neutral-500 uppercase tracking-wider mb-1">Indicators</p>
                  <p className="text-sm text-orange-400 font-mono">{selectedReport.indicators}</p>
                </div>
              </div>

              <div className="pt-4 border-t border-neutral-700">
                <p className="text-xs text-neutral-500 uppercase tracking-wider mb-3">Threat Distribution</p>
                <ResponsiveContainer width="100%" height={250}>
                  <BarChart data={threatData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#333" />
                    <XAxis dataKey="category" stroke="#666" />
                    <YAxis stroke="#666" />
                    <Tooltip contentStyle={{ backgroundColor: "#1a1a1a", border: "1px solid #FF6B35" }} />
                    <Bar dataKey="count" fill="#FF6B35" />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>

            <div className="flex gap-2">
              <Button
                onClick={() => handleDownloadReport(selectedReport)}
                className="bg-orange-500 hover:bg-orange-600 text-black flex-1"
              >
                <Download className="w-4 h-4 mr-2" />
                Download Report
              </Button>
              <Button
                variant="outline"
                className="border-orange-500/50 text-orange-400 hover:bg-orange-500/10 bg-transparent"
              >
                <Send className="w-4 h-4 mr-2" />
                Share
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Generated Reports */}
      <Card className="bg-neutral-900 border-orange-900/30">
        <CardHeader className="pb-3">
          <CardTitle className="text-sm font-medium text-orange-400 tracking-wider">GENERATED REPORTS</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {generatedReports.map((report) => (
              <div
                key={report.id}
                className="p-4 bg-neutral-800 border border-neutral-700 rounded hover:border-orange-500/50 transition-colors"
              >
                <div className="flex items-start justify-between mb-3">
                  <div className="flex-1">
                    <p className="text-sm text-orange-400 font-mono">{report.id}</p>
                    <p className="text-sm text-white mt-1">{report.title}</p>
                    <div className="flex gap-4 text-xs text-neutral-500 mt-2">
                      <span>{report.date}</span>
                      <span>{report.type}</span>
                      <span>{report.size}</span>
                    </div>
                  </div>
                  <span className="text-xs font-bold px-2 py-1 rounded bg-green-500/20 text-green-400">
                    {report.status}
                  </span>
                </div>

                <div className="grid grid-cols-2 gap-2 mb-3 text-xs">
                  <div className="bg-neutral-900 p-2 rounded">
                    <p className="text-neutral-500">Threats</p>
                    <p className="text-orange-400 font-mono">{report.threats}</p>
                  </div>
                  <div className="bg-neutral-900 p-2 rounded">
                    <p className="text-neutral-500">Indicators</p>
                    <p className="text-orange-400 font-mono">{report.indicators}</p>
                  </div>
                </div>

                <div className="flex gap-2">
                  <Button
                    onClick={() => handleDownloadReport(report)}
                    size="sm"
                    className="bg-orange-500 hover:bg-orange-600 text-black h-7 flex-1"
                  >
                    <Download className="w-3 h-3 mr-1" />
                    Download
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    className="border-orange-500/50 text-orange-400 hover:bg-orange-500/10 h-7 bg-transparent"
                  >
                    <Send className="w-3 h-3 mr-1" />
                    Share
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    className="border-orange-500/50 text-orange-400 hover:bg-orange-500/10 h-7 bg-transparent"
                  >
                    <Eye className="w-3 h-3 mr-1" />
                    View
                  </Button>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Integrations */}
      <Card className="bg-neutral-900 border-orange-900/30">
        <CardHeader className="pb-3">
          <CardTitle className="text-sm font-medium text-orange-400 tracking-wider">EXTERNAL INTEGRATIONS</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {[
              { name: "Splunk SIEM", status: "Connected", lastSync: "5 min ago" },
              { name: "Slack Alerts", status: "Connected", lastSync: "2 min ago" },
              { name: "Email Notifications", status: "Connected", lastSync: "1 hour ago" },
              { name: "Telegram Bot", status: "Disconnected", lastSync: "N/A" },
            ].map((integration) => (
              <div key={integration.name} className="p-4 bg-neutral-800 border border-neutral-700 rounded">
                <div className="flex items-center justify-between mb-2">
                  <p className="text-sm text-white font-mono">{integration.name}</p>
                  <div
                    className={`w-2 h-2 rounded-full ${
                      integration.status === "Connected" ? "bg-green-500" : "bg-red-500"
                    }`}
                  ></div>
                </div>
                <p className="text-xs text-neutral-500">
                  {integration.status === "Connected" ? `Last sync: ${integration.lastSync}` : "Not connected"}
                </p>
                <Button size="sm" className="mt-3 w-full bg-orange-500 hover:bg-orange-600 text-black h-7">
                  {integration.status === "Connected" ? "Configure" : "Connect"}
                </Button>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
