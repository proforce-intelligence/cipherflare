"use client"

import { useState } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Search, Download, Eye, Pause, Play, Trash2, RefreshCw } from "lucide-react"
import { SearchJobForm } from "@/components/search-job-form"
import { JobProgressTracker } from "@/components/job-progress-tracker"
import { NetworkGraph } from "@/components/network-graph"
import { useJobs } from "@/hooks/use-api"
import { apiClient } from "@/lib/api-client"
import { formatDistanceToNow } from "date-fns"
import { toast } from "sonner"
import type { Job } from "@/lib/api-client"
import { Loader2, Network } from "lucide-react"
import Markdown from "react-markdown"

export default function InvestigationsPage() {
  const [showForm, setShowForm] = useState(false)
  const [activeJobId, setActiveJobId] = useState<string | null>(null)
  const [selectedJob, setSelectedJob] = useState<Job | null>(null)
  const [results, setResults] = useState<any>(null)
  const [loadingResults, setLoadingResults] = useState(false)
  const [showGraph, setShowGraph] = useState(false)
  const [previewModal, setPreviewModal] = useState<{ type: "screenshot" | "text"; url: string } | null>(null)
  const { jobs, isLoading, refresh } = useJobs()

  const handleJobCreated = (jobId: string) => {
    setActiveJobId(jobId)
    setShowForm(false)
    refresh()
    toast.success("Search job started! Tracking progress...")
  }

  const handleToggleStatus = async (e: React.MouseEvent, job: Job) => {
    e.stopPropagation()
    try {
      if (job.status === "processing" || job.status === "queued") {
        await apiClient.pauseJob(job.job_id)
        toast.success("Investigation paused")
      } else if (job.status === "paused") {
        await apiClient.resumeJob(job.job_id)
        toast.success("Investigation resumed")
      }
      refresh()
    } catch (error) {
      toast.error("Failed to toggle status")
    }
  }

  const handleDelete = async (e: React.MouseEvent, jobId: string) => {
    e.stopPropagation()
    try {
      await apiClient.deleteJob(jobId)
      toast.success("Job deleted successfully")
      if (selectedJob?.job_id === jobId) {
        setSelectedJob(null)
        setResults(null)
      }
      refresh()
    } catch (error) {
      toast.error("Failed to delete job")
    }
  }

  const handleJobComplete = (job: Job) => {
    setActiveJobId(null)
    toast.success(`Job completed! Click "${job.job_name}" to view results.`)
  }

  const handleViewJobResults = async (job: Job) => {
    if (selectedJob?.job_id === job.job_id) {
      setSelectedJob(null)
      setResults(null)
      setShowGraph(false)
      return
    }

    setSelectedJob(job)
    setLoadingResults(true)
    setShowGraph(false)

    try {
      const jobResults = await apiClient.getJobResults(job.job_id, {
        include_summary: false,
      })
      // Ensure results object has findings array even if empty
      setResults(jobResults || { findings: [] })
    } catch (error) {
      toast.error("Failed to load results")
      setResults({ findings: [] })
      console.error(error)
    } finally {
      setLoadingResults(false)
    }
  }

  const handleGenerateSummary = async () => {
    if (!selectedJob) return

    setLoadingResults(true)
    try {
      const jobResults = await apiClient.getJobResults(selectedJob.job_id, {
        include_summary: true,
        model_choice: "gemini-2.5-flash",
      })
      setResults(jobResults)
      toast.success("AI summary generated successfully")
    } catch (error) {
      toast.error("Failed to generate AI summary")
      console.error(error)
    } finally {
      setLoadingResults(false)
    }
  }

  const handlePreviewScreenshot = (screenshotFile: string) => {
    const url = `${process.env.NEXT_PUBLIC_API_URL || "http://0.0.0.0:8000"}/files/${screenshotFile}`
    setPreviewModal({ type: "screenshot", url })
  }

  const handlePreviewText = (textFile: string) => {
    const url = `${process.env.NEXT_PUBLIC_API_URL || "http://0.0.0.0:8000"}/files/${textFile}`
    setPreviewModal({ type: "text", url })
  }

  const handleExportResults = () => {
    if (!results || !selectedJob) return

    const content = `
SEARCH RESULTS REPORT
Job: ${selectedJob.job_name}
Query: ${selectedJob.query}
Status: ${selectedJob.status}
Created: ${selectedJob.created_at}
Completed: ${selectedJob.completed_at || "In progress"}
Sites Scraped: ${selectedJob.scraped_sites}

RESULTS (${results.findings?.length || 0} findings):
${results.findings
  ?.map(
    (r: any, i: number) => `
${i + 1}. ${r.title || "Untitled"}
   URL: ${r.url}
   Risk Level: ${r.risk_level || "N/A"}
   Content: ${(r.text_excerpt || r.content || "").substring(0, 200)}...
   Timestamp: ${r.scraped_at || r.timestamp}
`,
  )
  .join("\n")}

AI SUMMARY:
${results.summary || "No summary available"}
    `

    const element = document.createElement("a")
    element.setAttribute("href", "data:text/plain;charset=utf-8," + encodeURIComponent(content))
    element.setAttribute("download", `results-${selectedJob.job_name.replace(/\s+/g, "-")}.txt`)
    element.style.display = "none"
    document.body.appendChild(element)
    element.click()
    document.body.removeChild(element)
    toast.success("Results exported successfully")
  }

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-orange-400">SEARCH & INVESTIGATIONS</h2>
          <p className="text-sm text-neutral-500 mt-1">Deep querying and forensic analysis of dark web content</p>
        </div>
        <Button onClick={() => setShowForm(!showForm)} className="bg-orange-500 hover:bg-orange-600 text-black">
          <Search className="w-4 h-4 mr-2" />
          {showForm ? "Cancel" : "New Search"}
        </Button>
      </div>

      {showForm && (
        <div className="animate-in fade-in slide-in-from-top-4 duration-300">
          <SearchJobForm onJobCreated={handleJobCreated} />
        </div>
      )}

      {activeJobId && (
        <div className="animate-in fade-in slide-in-from-top-4 duration-300">
          <JobProgressTracker jobId={activeJobId} onComplete={handleJobComplete} />
        </div>
      )}

      <Card className="bg-neutral-900 border-orange-900/30">
        <CardHeader className="pb-3">
          <CardTitle className="text-sm font-medium text-orange-400 tracking-wider">
            ALL SEARCH JOBS ({jobs?.length || 0})
          </CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="flex justify-center py-8">
              <Loader2 className="w-8 h-8 animate-spin text-orange-500" />
            </div>
          ) : jobs && jobs.length > 0 ? (
            <div className="space-y-3">
              {jobs.map((job) => (
                <div
                  key={job.job_id}
                  onClick={() => handleViewJobResults(job)}
                  className={`p-4 rounded cursor-pointer transition-all ${
                    selectedJob?.job_id === job.job_id
                      ? "bg-orange-500/20 border-2 border-orange-500"
                      : "bg-neutral-800 border border-neutral-700 hover:border-orange-500/50"
                  }`}
                >
                  <div className="flex items-start justify-between mb-3">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        <p className="text-sm text-orange-400 font-mono">{job.job_name}</p>
                        <span
                          className={`text-xs font-bold px-2 py-1 rounded ${
                            job.status === "completed"
                              ? "bg-green-500/20 text-green-400"
                              : job.status === "running" || job.status === "processing"
                                ? "bg-blue-500/20 text-blue-400"
                                : job.status === "failed"
                                  ? "bg-red-500/20 text-red-400"
                                  : job.status === "paused"
                                    ? "bg-yellow-500/20 text-yellow-400"
                                    : "bg-neutral-500/20 text-neutral-400"
                          }`}
                        >
                          {job.status.toUpperCase()}
                        </span>
                      </div>
                      <p className="text-sm text-white mt-1">Query: {job.query}</p>
                    </div>
                    <div className="flex gap-1">
                      {["queued", "processing", "paused"].includes(job.status) && (
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={(e) => handleToggleStatus(e, job)}
                          className="h-8 w-8 text-neutral-400 hover:text-orange-500"
                        >
                          {job.status === "paused" ? <Play className="h-4 w-4" /> : <Pause className="h-4 w-4" />}
                        </Button>
                      )}
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={(e) => handleDelete(e, job.job_id)}
                        className="h-8 w-8 text-neutral-400 hover:text-red-500"
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
                  </div>

                  <div className="mb-2">
                    <div className="w-full bg-neutral-700 rounded-full h-1.5">
                      <div className="bg-orange-500 h-1.5 rounded-full" style={{ width: `${job.progress}%` }}></div>
                    </div>
                    <p className="text-xs text-neutral-500 mt-1">{job.progress}% complete</p>
                  </div>

                  <div className="flex gap-4 text-xs text-neutral-500">
                    <span>
                      Sites: {job.scraped_sites}/{job.total_sites}
                    </span>
                    <span>Created: {formatDistanceToNow(new Date(job.created_at), { addSuffix: true })}</span>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-8 text-neutral-500">
              <Search className="w-12 h-12 mx-auto mb-3 opacity-50" />
              <p>No search jobs yet. Click "New Search" to get started.</p>
            </div>
          )}
        </CardContent>
      </Card>

      {selectedJob && (
        <Card className="bg-neutral-900 border-orange-900/30 animate-in fade-in slide-in-from-bottom-4 duration-300">
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <CardTitle className="text-sm font-medium text-orange-400 tracking-wider">
                SEARCH RESULTS - {selectedJob.job_name}
              </CardTitle>
              <div className="flex gap-2">
                <Button 
                  onClick={() => selectedJob && handleViewJobResults(selectedJob)} 
                  variant="outline" 
                  size="sm"
                  title="Refresh results from server"
                >
                  <RefreshCw className={`w-4 h-4 ${loadingResults ? 'animate-spin' : ''}`} />
                </Button>
                
                {selectedJob && (
                  <Button
                    onClick={() => setShowGraph(!showGraph)}
                    className="bg-purple-500 hover:bg-purple-600 text-white"
                    size="sm"
                  >
                    <Network className="w-4 h-4 mr-2" />
                    {showGraph ? "Show Results List" : "View Network Map"}
                  </Button>
                )}

                {selectedJob && !results?.summary && (
                  <Button
                    onClick={handleGenerateSummary}
                    disabled={loadingResults}
                    className="bg-blue-500 hover:bg-blue-600 text-white"
                    size="sm"
                  >
                    {loadingResults ? <Loader2 className="w-4 h-4 animate-spin" /> : "Generate AI Summary"}
                  </Button>
                )}

                <Button
                  onClick={handleExportResults}
                  disabled={!results || !results.findings || results.findings.length === 0}
                  className="bg-orange-500 hover:bg-orange-600 text-black"
                  size="sm"
                >
                  <Download className="w-4 h-4 mr-2" />
                  Export
                </Button>
                <Button onClick={() => setSelectedJob(null)} variant="ghost" size="sm">
                  ✕
                </Button>
              </div>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            {loadingResults ? (
              <div className="flex justify-center py-8">
                <Loader2 className="w-8 h-8 animate-spin text-orange-500" />
              </div>
            ) : showGraph && selectedJob ? (
              <NetworkGraph jobId={selectedJob.job_id} onClose={() => setShowGraph(false)} />
            ) : results && results.findings && results.findings.length > 0 ? (
              <>
                {results.summary && (
                  <div className="bg-blue-500/10 border border-blue-500/30 rounded-lg p-6">
                    <h4 className="text-sm font-semibold text-blue-400 mb-4 border-b border-blue-500/20 pb-2 uppercase tracking-widest">
                      AI Intelligence Report
                    </h4>
                    <div className="prose prose-sm prose-invert max-w-none text-neutral-300 prose-headings:text-blue-400 prose-strong:text-white prose-a:text-orange-400">
                      <Markdown>
                        {typeof results.summary === "string"
                          ? results.summary
                          : results.summary?.summary || JSON.stringify(results.summary, null, 2)}
                      </Markdown>
                    </div>
                    {results.summary?.pgp_verification_results &&
                      results.summary.pgp_verification_results.length > 0 && (
                        <div className="mt-4 pt-4 border-t border-blue-500/20">
                          <h5 className="text-xs font-semibold text-blue-400 mb-2">PGP VERIFICATION RESULTS</h5>
                          <div className="space-y-2">
                            {results.summary.pgp_verification_results.map((pgp: any, idx: number) => (
                              <div key={idx} className="text-xs bg-neutral-800 p-2 rounded">
                                <span className="text-neutral-400">{pgp.onion}: </span>
                                <span className={pgp.verified ? "text-green-400" : "text-red-400"}>
                                  {pgp.verified ? "✓ Verified" : "✗ Not Verified"}
                                </span>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                  </div>
                )}

                <div className="space-y-3">
                  {results.findings.map((result: any, idx: number) => (
                    <div
                      key={result.id || `${selectedJob.job_id}-result-${idx}`}
                      className="bg-neutral-800 border border-neutral-700 rounded-lg p-4 hover:border-orange-500/50 transition-colors"
                    >
                      <div className="flex items-start justify-between mb-2">
                        <h4 className="text-sm font-semibold text-white">{result.title || "Untitled"}</h4>
                        {result.risk_level && (
                          <span
                            className={`text-xs px-2 py-1 rounded ${
                              result.risk_level === "critical"
                                ? "bg-red-500/20 text-red-400"
                                : result.risk_level === "high"
                                  ? "bg-orange-500/20 text-orange-400"
                                  : result.risk_level === "medium"
                                    ? "bg-yellow-500/20 text-yellow-400"
                                    : "bg-green-500/20 text-green-400"
                            }`}
                          >
                            {result.risk_level.toUpperCase()}
                          </span>
                        )}
                      </div>
                      <p className="text-xs text-neutral-400 mb-2 font-mono break-all">{result.url}</p>

                      {result.visual_summary && (
                        <div className="mb-3 p-3 bg-purple-500/10 border border-purple-500/30 rounded-lg">
                          <p className="text-xs font-semibold text-purple-400 flex items-center gap-1 mb-1">
                            <Eye className="w-3 h-3" /> VISUAL AI SUMMARY
                          </p>
                          <p className="text-sm text-neutral-200 italic">{result.visual_summary}</p>
                        </div>
                      )}

                      {result.ocr_text ? (
                        <div className="mb-3">
                          <p className="text-xs font-semibold text-orange-500/70 mb-1 tracking-widest uppercase">Captured Intelligence (OCR)</p>
                          <p className="text-sm text-neutral-300 bg-black/20 p-3 rounded border border-neutral-800 leading-relaxed">
                            {result.ocr_text}
                          </p>
                        </div>
                      ) : (
                        <p className="text-sm text-neutral-300 mb-3 leading-relaxed">
                          {result.text_excerpt?.substring(0, 500)}
                          {result.text_excerpt && result.text_excerpt.length > 500 && "..."}
                        </p>
                      )}

                      <div className="flex items-center gap-4 mb-3">
                        {result.screenshot_file && (
                          <Button
                            onClick={() => handlePreviewScreenshot(result.screenshot_file)}
                            size="sm"
                            variant="outline"
                            className="text-xs"
                          >
                            <Eye className="w-3 h-3 mr-1" />
                            View Screenshot
                          </Button>
                        )}
                      </div>

                      <div className="flex items-center gap-4 text-xs text-neutral-500">
                        {result.risk_score !== undefined && <span>Risk Score: {result.risk_score.toFixed(1)}</span>}
                        {result.relevance_score !== undefined && (
                          <span>Relevance: {result.relevance_score.toFixed(2)}</span>
                        )}
                        {result.scraped_at && (
                          <span>Found: {formatDistanceToNow(new Date(result.scraped_at), { addSuffix: true })}</span>
                        )}
                      </div>

                      {result.threat_indicators &&
                        Array.isArray(result.threat_indicators) &&
                        result.threat_indicators.length > 0 && (
                          <div className="mt-2 flex flex-wrap gap-1">
                            {result.threat_indicators.slice(0, 5).map((indicator: string, i: number) => (
                              <span key={i} className="text-xs bg-red-500/10 text-red-400 px-2 py-0.5 rounded">
                                {indicator}
                              </span>
                            ))}
                          </div>
                        )}

                      {result.entities && (
                        <div className="mt-3 pt-3 border-t border-neutral-700">
                          {result.entities.emails && result.entities.emails.length > 0 && (
                            <div className="mb-2">
                              <span className="text-xs text-neutral-500">Emails: </span>
                              {result.entities.emails.map((email: string, i: number) => (
                                <span key={i} className="text-xs text-orange-400 mr-2">
                                  {email}
                                </span>
                              ))}
                            </div>
                          )}
                          {result.entities.btc_addresses && result.entities.btc_addresses.length > 0 && (
                            <div className="mb-2">
                              <span className="text-xs text-neutral-500">BTC: </span>
                              {result.entities.btc_addresses.map((addr: string, i: number) => (
                                <span key={i} className="text-xs text-orange-400 mr-2 font-mono">
                                  {addr}
                                </span>
                              ))}
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </>
            ) : (
              <div className="text-center py-8 text-neutral-500">
                <Eye className="w-12 h-12 mx-auto mb-3 opacity-50" />
                <p>No results available yet. Job may still be running or no findings were discovered.</p>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {previewModal && (
        <div
          className="fixed inset-0 bg-black/80 flex items-center justify-center z-50 p-4"
          onClick={() => setPreviewModal(null)}
        >
          <div
            className="bg-neutral-900 border border-orange-500 rounded-lg max-w-6xl max-h-[90vh] w-full overflow-hidden"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between p-4 border-b border-neutral-700">
              <h3 className="text-orange-400 font-semibold">
                {previewModal.type === "screenshot" ? "Screenshot Preview" : "Scraped Text Preview"}
              </h3>
              <Button onClick={() => setPreviewModal(null)} variant="ghost" size="sm">
                ✕
              </Button>
            </div>
            <div className="p-4 overflow-auto max-h-[calc(90vh-80px)]">
              {previewModal.type === "screenshot" ? (
                <img src={previewModal.url || "/placeholder.svg"} alt="Screenshot" className="w-full rounded" />
              ) : (
                <iframe src={previewModal.url} className="w-full h-[70vh] bg-white rounded" />
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
