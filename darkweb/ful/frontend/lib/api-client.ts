const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"

// Types
export interface SearchParams {
  keyword: string
  job_name?: string
  max_results?: number
  depth?: number
  timeout_seconds?: number
  include_summary?: boolean
  model_choice?: string
  pgp_verify?: boolean
}

export interface Job {
  job_id: string
  job_name: string
  query: string
  status: "queued" | "processing" | "completed" | "failed"
  progress: number
  total_sites: number
  scraped_sites: number
  created_at: string
  completed_at?: string
  error?: string
}

export interface JobResult {
  job_id: string
  results: SearchResult[]
  summary?: {
    success: boolean
    query: string
    model_used: string
    summary: string
    findings_analyzed: number
    source_links_count: number
    pgp_verification_results?: any
  }
  total_findings?: number
}

export interface SearchResult {
  url: string
  title: string
  content: string
  timestamp: string
  pgp_verified?: boolean
  relevance_score?: number
}

export interface Alert {
  id: string
  job_id: string
  job_name: string
  type: "job_completed" | "threat_detected" | "error" | "monitoring"
  title: string
  message: string
  severity: "info" | "warning" | "error" | "success"
  created_at: string
  read: boolean
  data?: any
}

export interface Stats {
  total_jobs: number
  active_jobs: number
  completed_jobs: number
  failed_jobs: number
  total_results: number
  alerts_count: number
  uptime: string
}

export interface MonitoringJob {
  id: string
  name: string
  query: string
  sites: string[]
  frequency: string
  is_active: boolean
  last_run?: string
  next_run?: string
  created_at: string
}

class ApiClient {
  private async request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
    try {
      console.log("[v0] API Request:", endpoint)
      const response = await fetch(`${API_BASE_URL}${endpoint}`, {
        ...options,
        headers: {
          "Content-Type": "application/json",
          ...options.headers,
        },
      })

      if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: response.statusText }))
        console.error("[v0] API Error:", error)
        throw new Error(error.detail || "Request failed")
      }

      const data = await response.json()
      console.log("[v0] API Response:", endpoint, data)
      return data
    } catch (error) {
      console.error("[v0] API request failed:", error)
      throw error
    }
  }

  private mapBackendJobToFrontend(backendJob: any): Job {
    return {
      job_id: backendJob.id || backendJob.job_id,
      job_name: backendJob.job_name,
      query: backendJob.keyword || backendJob.query || "",
      status: backendJob.status,
      progress: backendJob.progress || 0,
      total_sites: backendJob.max_results || 100,
      scraped_sites: backendJob.findings_count || 0,
      created_at: backendJob.created_at,
      completed_at: backendJob.completed_at,
      error: backendJob.error_message || backendJob.error,
    }
  }

  // Job Management
  async createSearchJob(params: SearchParams): Promise<Job> {
    const queryParams = new URLSearchParams()
    queryParams.append("keyword", params.keyword)
    if (params.job_name) queryParams.append("job_name", params.job_name)
    if (params.max_results) queryParams.append("max_results", params.max_results.toString())
    if (params.depth) queryParams.append("depth", params.depth.toString())
    if (params.timeout_seconds) queryParams.append("timeout_seconds", params.timeout_seconds.toString())
    if (params.include_summary) queryParams.append("include_summary", "true")
    if (params.model_choice) queryParams.append("model_choice", params.model_choice)
    if (params.pgp_verify) queryParams.append("pgp_verify", "true")

    return this.request<Job>(`/api/v1/jobs/search?${queryParams.toString()}`, {
      method: "POST",
    })
  }

  async getJobs(filters?: { status?: string; job_type?: string; limit?: number; offset?: number }): Promise<{
    jobs: Job[]
    total: number
  }> {
    const queryParams = new URLSearchParams()
    if (filters?.status) queryParams.append("status", filters.status)
    if (filters?.job_type) queryParams.append("job_type", filters.job_type)
    if (filters?.limit) queryParams.append("limit", filters.limit.toString())
    if (filters?.offset) queryParams.append("offset", filters.offset.toString())

    const response = await this.request<{ success: boolean; jobs: any[]; total: number }>(
      `/api/v1/jobs?${queryParams.toString()}`,
    )

    const mappedJobs = response.jobs.map((job) => this.mapBackendJobToFrontend(job))
    console.log("[v0] Mapped jobs:", mappedJobs)

    return { jobs: mappedJobs, total: response.total }
  }

  async getJob(jobId: string): Promise<Job> {
    const response = await this.request<{ success: boolean; job: any }>(`/api/v1/jobs/${jobId}`)

    const mappedJob = this.mapBackendJobToFrontend(response.job)
    console.log("[v0] Mapped single job:", mappedJob)

    return mappedJob
  }

  async getJobResults(
    jobId: string,
    params?: { include_summary?: boolean; model_choice?: string },
  ): Promise<JobResult> {
    const queryParams = new URLSearchParams()
    if (params?.include_summary) queryParams.append("include_summary", "true")
    if (params?.model_choice) queryParams.append("model_choice", params.model_choice)

    const response = await this.request<any>(`/api/v1/jobs/${jobId}/results?${queryParams.toString()}`)

    return {
      job_id: response.job_id,
      results: response.findings || [],
      summary: response.summary, // Keep the full object with metadata
      total_findings: response.total_findings,
    }
  }

  async deleteJob(jobId: string): Promise<void> {
    return this.request<void>(`/api/v1/jobs/${jobId}`, {
      method: "DELETE",
    })
  }

  // Alerts
  async getAlerts(unreadOnly = false): Promise<Alert[]> {
    const query = unreadOnly ? "?unread_only=true" : ""
    return this.request<Alert[]>(`/api/v1/alerts${query}`)
  }

  async markAlertRead(alertId: string): Promise<void> {
    return this.request<void>(`/api/v1/alerts/${alertId}/read`, {
      method: "POST",
    })
  }

  async markAllAlertsRead(): Promise<void> {
    return this.request<void>("/api/v1/alerts/mark-all-read", {
      method: "POST",
    })
  }

  async deleteAlert(alertId: string): Promise<void> {
    return this.request<void>(`/api/v1/alerts/${alertId}`, {
      method: "DELETE",
    })
  }

  // Stats
  async getStats(): Promise<Stats> {
    return this.request<Stats>("/api/v1/stats")
  }

  // Monitoring Jobs
  async createMonitoringJob(data: {
    keyword: string
    name?: string
    frequency_hours: number
    target_sites?: string[]
    max_results?: number
  }): Promise<MonitoringJob> {
    return this.request<MonitoringJob>("/api/v1/monitoring/jobs", {
      method: "POST",
      body: JSON.stringify(data),
    })
  }

  async getMonitoringJobs(): Promise<MonitoringJob[]> {
    return this.request<MonitoringJob[]>("/api/v1/monitoring/jobs")
  }

  async updateMonitoringJob(jobId: string, data: Partial<MonitoringJob>): Promise<MonitoringJob> {
    return this.request<MonitoringJob>(`/api/v1/monitoring/jobs/${jobId}`, {
      method: "PUT",
      body: JSON.stringify(data),
    })
  }

  async deleteMonitoringJob(jobId: string): Promise<void> {
    return this.request<void>(`/api/v1/monitoring/jobs/${jobId}`, {
      method: "DELETE",
    })
  }

  async getMonitoringResults(jobId: string): Promise<any[]> {
    return this.request<any[]>(`/api/v1/monitoring/jobs/${jobId}/results`)
  }

  async getAvailableModels(): Promise<string[]> {
    const response = await this.request<{ available_models: string[] }>("/api/v1/models/available")
    return response.available_models
  }
}

export const apiClient = new ApiClient()
