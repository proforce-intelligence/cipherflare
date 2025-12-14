import useSWR from "swr"
import { apiClient } from "@/lib/api-client"

export function useJobs(filters?: { status?: string; job_type?: string }) {
  const { data, error, isLoading, mutate } = useSWR(["/api/v1/jobs", filters], () => apiClient.getJobs(filters), {
    refreshInterval: 3000, // Poll every 3 seconds for active jobs
  })

  return {
    jobs: data?.jobs || [],
    total: data?.total || 0,
    isLoading,
    error,
    refresh: mutate,
  }
}

export function useJob(jobId: string | null) {
  const { data, error, isLoading, mutate } = useSWR(
    jobId ? `/api/v1/jobs/${jobId}` : null,
    () => (jobId ? apiClient.getJob(jobId) : null),
    {
      refreshInterval: (data) => {
        // Stop polling when job is completed or failed
        if (data && ["completed", "failed"].includes(data.status)) {
          return 0
        }
        return 2000 // Poll every 2 seconds for active job
      },
    },
  )

  return {
    job: data,
    isLoading,
    error,
    refresh: mutate,
  }
}

export function useAlerts(unreadOnly = false) {
  const { data, error, isLoading, mutate } = useSWR(
    `/api/v1/alerts?unread=${unreadOnly}`,
    () => apiClient.getAlerts(unreadOnly),
    {
      refreshInterval: 5000, // Poll every 5 seconds
    },
  )

  return {
    alerts: data || [],
    isLoading,
    error,
    refresh: mutate,
  }
}

export function useStats() {
  const { data, error, isLoading, mutate } = useSWR("/api/v1/stats", () => apiClient.getStats(), {
    refreshInterval: 10000, // Poll every 10 seconds
  })

  return {
    stats: data,
    isLoading,
    error,
    refresh: mutate,
  }
}

export function useMonitoringJobs() {
  const { data, error, isLoading, mutate } = useSWR("/api/v1/monitoring/jobs", () => apiClient.getMonitoringJobs(), {
    refreshInterval: 30000, // Poll every 30 seconds
  })

  return {
    jobs: data || [],
    isLoading,
    error,
    refresh: mutate,
  }
}

export function useRecentJobs(limit = 10) {
  const { data, error, isLoading, mutate } = useSWR(
    [`/api/v1/jobs/recent`, limit],
    () => apiClient.getJobs({ limit }),
    {
      refreshInterval: 10000, // Poll every 10 seconds
    },
  )

  return {
    jobs: data?.jobs || [],
    isLoading,
    error,
    refresh: mutate,
  }
}
