import { ReactNode } from "react"

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://0.0.0.0:8000"

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
  findings: SearchResult[]
  summary?: string | SummaryObject // Can be string or object
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
  total_searches: number
  active_threats: number
}

export interface MonitoringJob {
  last_run_at: string | number | Date
  next_run_at: string | number | Date
  target_url: ReactNode
  interval_hours: ReactNode
  alerts_triggered: number
  findings_count: number
  total_checks: number
  status: string
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

export interface SummaryObject {
  success: boolean
  query: string
  model_used: string
  summary: string
  findings_analyzed: number
  source_links_count: number
  pgp_verification_results?: Array<{
    onion: string
    verified: boolean
    pgp_key?: string
    error?: string
  }>
}

export interface MonitoringJobConfig {
  url: string
  name?: string
  interval_hours?: number
  username?: string
  password?: string
  login_path?: string
  username_selector?: string
  password_selector?: string
  submit_selector?: string
}

export interface LiveMirrorSession {
  session_id: string
  target_url: string
  javascript_enabled: boolean
  websocket_url: string
  timeout_minutes: number
}

export interface AlertConfig {
  name: string
  keywords: string[]
  notification_type: "dashboard" | "email" | "webhook" | "slack"
  severity: "info" | "warning" | "error" | "success"
  email?: string
  webhook_url?: string
  slack_webhook?: string
}

class ApiClient {
  // Added token parameter for authentication and improved error logging
  private _getAuthToken(): string | null {
    // This is an example using localStorage.
    // In a production app, you might get this from a cookie, a global state, or NextAuth.js session.
    return localStorage.getItem('authToken');
  }

  private async request<T>(endpoint: string, options: RequestInit = {}, token?: string): Promise<T> {
    try {
      const headers: HeadersInit = {
        "Content-Type": "application/json",
        ...options.headers,
      };

      if (token) {
        (headers as Record<string, string>).Authorization = `Bearer ${token}`;
      }

      console.log("[v0] API Request:", endpoint);
      const response = await fetch(`${API_BASE_URL}${endpoint}`, {
        ...options,
        headers,
      });

      if (!response.ok) {
        const errorBody = await response.json().catch(() => null);
        const errorDetail = errorBody?.detail || response.statusText;
        console.error(`[v0] API Error (Status: ${response.status} ${response.statusText}):`, errorBody || { detail: response.statusText });
        throw new Error(errorDetail);
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

    const authToken = this._getAuthToken();
    return this.request<Job>(`/api/v1/jobs/search?${queryParams.toString()}`, {
      method: "POST",
    }, authToken)
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

    const authToken = this._getAuthToken();
    const response = await this.request<{ success: boolean; jobs: any[]; total: number }>(
      `/api/v1/jobs?${queryParams.toString()}`,
      {}, // Pass empty options object if no other options are needed
      authToken
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
      findings: response.findings || response.results || [],
      summary: response.summary,
      total_findings: response.total_findings || response.total,
    }
  }

  async deleteJob(jobId: string): Promise<void> {
    return this.request<void>(`/api/v1/jobs/${jobId}`, {
      method: "DELETE",
    })
  }

  // Alerts
  async getAlerts(unreadOnly = false): Promise<Alert[]> {
    const query = unreadOnly ? "?status=unread" : "?status=all"
    const response = await this.request<{
      success: boolean
      alerts: Alert[]
      total: number
    }>(`/api/v1/alerts/dashboard${query}`)

    return Array.isArray(response.alerts) ? response.alerts : []
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

  async createAlertConfig(config: AlertConfig): Promise<{ success: boolean; alert_id: string }> {
    const keyword = config.keywords.join(",")
    const queryParams = new URLSearchParams()
    queryParams.append("keyword", keyword)
    queryParams.append("risk_threshold", config.severity === "error" ? "high" : "medium")
    queryParams.append("notification_type", config.notification_type)

    if (config.email) {
      queryParams.append("notification_endpoint", config.email)
    } else if (config.webhook_url) {
      queryParams.append("notification_endpoint", config.webhook_url)
    } else if (config.slack_webhook) {
      queryParams.append("notification_endpoint", config.slack_webhook)
    }

    return this.request<{ success: boolean; alert_id: string }>(`/api/v1/alert/setup?${queryParams.toString()}`, {
      method: "POST",
    })
  }

  // Stats
  async getStats(): Promise<Stats> {
    const response = await this.request<{
      success: boolean
      statistics: any
      total_jobs: number
      active_jobs: number
      completed_jobs: number
      failed_jobs: number
      total_searches: number
      active_threats: number
    }>("/api/v1/stats")

    return {
      total_jobs: response.total_jobs || 0,
      active_jobs: response.active_jobs || 0,
      completed_jobs: response.completed_jobs || 0,
      failed_jobs: response.failed_jobs || 0,
      total_searches: response.total_searches || 0,
      active_threats: response.active_threats || 0,
      total_results: response.statistics?.total_findings || 0,
      alerts_count: 0, // Will be updated later if needed
      uptime: "N/A",
    }
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

  async setupMonitoring(config: MonitoringJobConfig): Promise<{ success: boolean; job_id: string }> {
    const queryParams = new URLSearchParams()
    queryParams.append("url", config.url)
    if (config.interval_hours) queryParams.append("interval_hours", config.interval_hours.toString())
    if (config.username) queryParams.append("username", config.username)
    if (config.password) queryParams.append("password", config.password)
    if (config.login_path) queryParams.append("login_path", config.login_path)
    if (config.username_selector) queryParams.append("username_selector", config.username_selector)
    if (config.password_selector) queryParams.append("password_selector", config.password_selector)
    if (config.submit_selector) queryParams.append("submit_selector", config.submit_selector)

    return this.request<{ success: boolean; job_id: string }>(`/api/v1/monitor/target?${queryParams.toString()}`, {
      method: "POST",
    })
  }

  async pauseMonitoringJob(jobId: string): Promise<void> {
    return this.request<void>(`/api/v1/monitoring/jobs/${jobId}/pause`, {
      method: "POST",
    })
  }

  async resumeMonitoringJob(jobId: string): Promise<void> {
    return this.request<void>(`/api/v1/monitoring/jobs/${jobId}/resume`, {
      method: "POST",
    })
  }

  async startLiveMirror(url: string, javascriptEnabled = false): Promise<LiveMirrorSession> {
    const queryParams = new URLSearchParams()
    queryParams.append("url", url)
    queryParams.append("javascript_enabled", javascriptEnabled.toString())

    const response = await this.request<{
      success: boolean
      session_id: string
      websocket_url: string
      config: {
        url: string
        javascript_enabled: boolean
        timeout_minutes: number
      }
    }>(`/api/v1/monitor/live?${queryParams.toString()}`, {
      method: "POST",
    })

    return {
      session_id: response.session_id,
      target_url: response.config.url,
      javascript_enabled: response.config.javascript_enabled,
      websocket_url: response.websocket_url,
      timeout_minutes: response.config.timeout_minutes,
    }
  }

  async stopLiveMirror(sessionId: string): Promise<void> {
    return this.request<void>(`/api/v1/monitor/live/${sessionId}`, {
      method: "DELETE",
    })
  }

  async navigateLiveMirror(sessionId: string, url: string): Promise<void> {
    const queryParams = new URLSearchParams()
    queryParams.append("url", url)

    return this.request<void>(`/api/v1/monitor/live/${sessionId}/navigate?${queryParams.toString()}`, {
      method: "POST",
    })
  }

  async getMonitoringJob(jobId: string): Promise<MonitoringJob> {
    const response = await this.request<{ success: boolean; job: any }>(`/api/v1/monitoring/jobs/${jobId}`)
    return response.job
  }
}

export const apiClient = new ApiClient()
