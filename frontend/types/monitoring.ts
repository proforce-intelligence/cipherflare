export interface MonitoringJob {
  id: string
  target_url: string
  interval_hours: number
  status: "active" | "paused" | "completed" | "failed"
  created_at: string
  last_run_at?: string
  next_run_at?: string
  total_checks: number
  findings_count: number
  alerts_triggered: number
  error_message?: string
}