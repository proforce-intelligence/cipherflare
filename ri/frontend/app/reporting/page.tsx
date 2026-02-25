"use client"

import { useState, useEffect } from "react"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Download, Send, Eye, FileText, BarChart3, AlertCircle, Loader2, RefreshCcw, Trash2 } from "lucide-react"
import { apiClient } from "@/lib/api-client"
import { toast } from "sonner"
import { format } from "date-fns"

export default function ReportingPage() {
  const [reportType, setReportType] = useState("comprehensive")
  const [isGenerating, setIsSubmitting] = useState(false)
  const [reports, setReports] = useState([])
  const [isLoading, setIsLoading] = useState(true)
  
  // Filters
  const [reportTitle, setReportTitle] = useState("")
  const [filterType, setFilterType] = useState("job_name")
  const [filterValue, setFilterValue] = useState("")
  const [modelChoice, setModelChoice] = useState("gemini-2.5-flash")

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

  const fetchReports = async () => {
    try {
      const data = await apiClient.listReports()
      setReports(data.reports || [])
    } catch (error) {
      console.error("Failed to fetch reports:", error)
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    fetchReports()
    const interval = setInterval(fetchReports, 10000) // Refresh every 10s
    return () => clearInterval(interval)
  }, [])

  const handleGenerateReport = async () => {
    if (!reportTitle.trim()) {
      toast.error("Please enter a report title")
      return
    }
    if (!filterValue.trim()) {
      toast.error(`Please enter a ${filterType.replace('_', ' ')}`)
      return
    }

    setIsSubmitting(true)
    try {
      const params = {
        report_type: reportType,
        report_title: reportTitle,
        model_choice: modelChoice,
        [filterType]: filterValue
      }
      
      const res = await apiClient.generateReport(params)
      toast.success(res.message)
      setReportTitle("")
      setFilterValue("")
      fetchReports()
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Failed to generate report")
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleDeleteReport = async (id: string) => {
    try {
      await apiClient.deleteReport(id)
      toast.success("Report deleted")
      fetchReports()
    } catch (error) {
      toast.error("Failed to delete report")
    }
  }

  const handleDownload = (report: any) => {
    if (!report.download_url) return
    const url = `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}${report.download_url}`
    window.open(url, "_blank")
  }

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-orange-400">INTEGRATION & REPORTING</h2>
          <p className="text-sm text-neutral-500 mt-1">Generate AI-powered threat intelligence reports using your local LLM</p>
        </div>
        <Button onClick={fetchReports} variant="outline" size="sm" className="border-orange-500/30 text-orange-400">
          <RefreshCcw className={`w-4 h-4 mr-2 ${isLoading ? 'animate-spin' : ''}`} />
          Refresh
        </Button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Report Generator Form */}
        <Card className="lg:col-span-2 bg-neutral-900 border-orange-900/30">
          <CardHeader>
            <CardTitle className="text-orange-400">CREATE NEW REPORT</CardTitle>
            <CardDescription>Configure report filters and AI parameters</CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="space-y-4">
              <div className="space-y-2">
                <Label>Report Title *</Label>
                <Input 
                  placeholder="e.g., Monthly Ransomware Trends - Feb 2026" 
                  value={reportTitle}
                  onChange={(e) => setReportTitle(e.target.value)}
                />
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>Filter By</Label>
                  <Select value={filterType} onValueChange={setFilterType}>
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="job_name">Investigation Title</SelectItem>
                      <SelectItem value="job_id">Specific Job ID</SelectItem>
                      <SelectItem value="keyword">Global Keyword</SelectItem>
                      <SelectItem value="monitor_title">Monitoring Job Title</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label>Filter Value *</Label>
                  <Input 
                    placeholder={`Enter ${filterType.replace('_', ' ')}...`}
                    value={filterValue}
                    onChange={(e) => setFilterValue(e.target.value)}
                  />
                </div>
              </div>

              <div className="space-y-2">
                <Label>AI Model (Local Ollama/LM Studio)</Label>
                <Select value={modelChoice} onValueChange={setModelChoice}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="llama3.1">Llama 3.1 (Recommended)</SelectItem>
                    <SelectItem value="mistral">Mistral</SelectItem>
                    <SelectItem value="gemini-2.5-flash">Gemini 2.5 Flash</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>

            <div className="space-y-3">
              <Label>Select Report Type</Label>
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
                    <p className="text-xs text-neutral-500 mt-1 line-clamp-2">{type.description}</p>
                  </div>
                ))}
              </div>
            </div>

            <Button 
              onClick={handleGenerateReport} 
              disabled={isGenerating}
              className="w-full bg-orange-500 hover:bg-orange-600 text-black font-bold h-12"
            >
              {isGenerating ? (
                <><Loader2 className="w-5 h-5 mr-2 animate-spin" /> DISPATCHING TASK...</>
              ) : (
                <><FileText className="w-5 h-5 mr-2" /> GENERATE REPORT</>
              )}
            </Button>
          </CardContent>
        </Card>

        {/* External Integrations - Static placeholder */}
        <Card className="bg-neutral-900 border-orange-900/30">
          <CardHeader>
            <CardTitle className="text-orange-400 text-sm tracking-widest">SIEM INTEGRATIONS</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {[
              { name: "Splunk SIEM", status: "Connected" },
              { name: "Slack Alerts", status: "Connected" },
              { name: "Email Alerts", status: "Connected" },
              { name: "Telegram Bot", status: "Offline" },
            ].map((i) => (
              <div key={i.name} className="flex items-center justify-between p-3 bg-neutral-800 rounded border border-neutral-700/50">
                <span className="text-xs font-mono text-white">{i.name}</span>
                <span className={`text-[10px] uppercase font-bold px-2 py-0.5 rounded ${i.status === 'Connected' ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'}`}>
                  {i.status}
                </span>
              </div>
            ))}
            <div className="pt-4 border-t border-orange-900/20">
              <p className="text-[10px] text-neutral-500 italic uppercase">Reporting server status: Operational</p>
              <p className="text-[10px] text-neutral-500 italic uppercase">Local LLM: http://127.0.0.1:1234</p>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Generated Reports List */}
      <Card className="bg-neutral-900 border-orange-900/30">
        <CardHeader>
          <CardTitle className="text-orange-400">RECENT REPORTS</CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="flex justify-center py-12"><Loader2 className="w-8 h-8 animate-spin text-orange-500" /></div>
          ) : reports.length > 0 ? (
            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
              {reports.map((report: any) => (
                <div key={report.id} className="p-4 bg-neutral-800 border border-neutral-700 rounded-lg hover:border-orange-500/40 transition-all group">
                  <div className="flex justify-between items-start mb-3">
                    <div>
                      <p className="text-[10px] text-orange-500 font-mono uppercase tracking-widest">{report.code}</p>
                      <h3 className="text-sm font-bold text-white mt-1 group-hover:text-orange-400 transition-colors">{report.title}</h3>
                    </div>
                    <span className={`text-[10px] px-2 py-0.5 rounded font-bold uppercase ${
                      report.status === 'completed' ? 'bg-green-500/20 text-green-400' : 
                      report.status === 'failed' ? 'bg-red-500/20 text-red-400' : 'bg-orange-500/20 text-orange-400 animate-pulse'
                    }`}>
                      {report.status}
                    </span>
                  </div>

                  <div className="grid grid-cols-3 gap-2 mb-4">
                    <div className="text-center p-2 bg-neutral-900 rounded">
                      <p className="text-[9px] text-neutral-500 uppercase">Threats</p>
                      <p className="text-xs font-bold text-white">{report.threats}</p>
                    </div>
                    <div className="text-center p-2 bg-neutral-900 rounded">
                      <p className="text-[9px] text-neutral-500 uppercase">IOCs</p>
                      <p className="text-xs font-bold text-white">{report.indicators}</p>
                    </div>
                    <div className="text-center p-2 bg-neutral-900 rounded">
                      <p className="text-[9px] text-neutral-500 uppercase">Size</p>
                      <p className="text-xs font-bold text-white">{report.size}</p>
                    </div>
                  </div>

                  <div className="flex gap-2">
                    <Button 
                      onClick={() => handleDownload(report)}
                      disabled={report.status !== 'completed'}
                      className="flex-1 bg-orange-500 hover:bg-orange-600 text-black h-8 text-xs"
                    >
                      <Download className="w-3.5 h-3.5 mr-1.5" /> Download
                    </Button>
                    <Button 
                      variant="outline" 
                      onClick={() => handleDeleteReport(report.id)}
                      className="border-red-900/50 text-red-400 hover:bg-red-500/10 h-8 px-3"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-12 border-2 border-dashed border-neutral-800 rounded-xl">
              <FileText className="w-12 h-12 text-neutral-700 mx-auto mb-4 opacity-20" />
              <p className="text-neutral-500 text-sm uppercase tracking-widest">No reports found in registry</p>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
