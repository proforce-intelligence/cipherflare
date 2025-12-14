"use client"

import { useState } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Search, Download, Eye } from "lucide-react"
import { SearchJobForm } from "@/components/search-job-form"
import { JobProgressTracker } from "@/components/job-progress-tracker"
import { useJobs } from "@/hooks/use-api"
import { apiClient } from "@/lib/api-client"
import { formatDistanceToNow } from "date-fns"
import { toast } from "sonner"
import type { Job } from "@/lib/api-client"
import { Loader2 } from "lucide-react" // Import Loader2 here

export default function InvestigationsPage() {
  const [showForm, setShowForm] = useState(false)
  const [activeJobId, setActiveJobId] = useState<string | null>(null)
  const [selectedJob, setSelectedJob] = useState<Job | null>(null)
  const [results, setResults] = useState<any>(null)
  const [loadingResults, setLoadingResults] = useState(false)
  const { jobs, isLoading } = useJobs()

  const handleJobCreated = (jobId: string) => {
    setActiveJobId(jobId)
    setShowForm(false)
    toast.success("Search job started! Tracking progress...")
  }

  const handleJobComplete = (job: Job) => {
    setActiveJobId(null)
    toast.success(`Job completed! Click "${job.job_name}" to view results.`)
  }

  const handleViewJobResults = async (job: Job) => {
    if (selectedJob?.job_id === job.job_id) {
      setSelectedJob(null)
      setResults(null)
      return
    }

    setSelectedJob(job)
    setLoadingResults(true)

    try {
      const jobResults = await apiClient.getJobResults(job.job_id, {
        include_summary: true,
        model_choice: "gemini-2.5-flash",
      })
      setResults(jobResults)
    } catch (error) {
      toast.error("Failed to load results")
      console.error(error)
    } finally {
      setLoadingResults(false)
    }
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

RESULTS (${results.total_findings || 0} findings):
${results.findings
  ?.map(
    (r: any, i: number) => `
${i + 1}. ${r.title || "Untitled"}
   URL: ${r.url}
   Content: ${r.content?.substring(0, 200)}...
   Timestamp: ${r.timestamp}
   ${r.pgp_verified ? "✓ PGP Verified" : ""}
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
      {/* Header - Added functional New Search button */}
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
                              : job.status === "running"
                                ? "bg-blue-500/20 text-blue-400"
                                : job.status === "failed"
                                  ? "bg-red-500/20 text-red-400"
                                  : "bg-yellow-500/20 text-yellow-400"
                          }`}
                        >
                          {job.status.toUpperCase()}
                        </span>
                      </div>
                      <p className="text-sm text-white mt-1">Query: {job.query}</p>
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
            ) : results && results.findings && results.findings.length > 0 ? (
              <>
                {/* AI Summary */}
                {results.summary && (
                  <div className="bg-blue-500/10 border border-blue-500/30 rounded-lg p-4">
                    <h4 className="text-sm font-semibold text-blue-400 mb-2">AI SUMMARY</h4>
                    <p className="text-sm text-neutral-300">{results.summary}</p>
                  </div>
                )}

                {/* Results List */}
                <div className="space-y-3">
                  {results.findings.map((result: any, idx: number) => (
                    <div
                      key={`${selectedJob.job_id}-result-${idx}`}
                      className="bg-neutral-800 border border-neutral-700 rounded-lg p-4 hover:border-orange-500/50 transition-colors"
                    >
                      <div className="flex items-start justify-between mb-2">
                        <h4 className="text-sm font-semibold text-white">{result.title || "Untitled"}</h4>
                        {result.pgp_verified && (
                          <span className="text-xs bg-green-500/20 text-green-400 px-2 py-1 rounded">
                            ✓ PGP Verified
                          </span>
                        )}
                      </div>
                      <p className="text-xs text-neutral-400 mb-2">{result.url}</p>
                      <p className="text-sm text-neutral-300 mb-3">{result.content?.substring(0, 300)}...</p>
                      <div className="flex items-center gap-4 text-xs text-neutral-500">
                        {result.relevance_score && <span>Relevance: {result.relevance_score.toFixed(2)}</span>}
                        <span>Found: {formatDistanceToNow(new Date(result.timestamp), { addSuffix: true })}</span>
                      </div>
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
    </div>
  )
}
