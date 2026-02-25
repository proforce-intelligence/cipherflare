"use client"

import { useState } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { ScrollArea } from "@/components/ui/scroll-area"
import { useAlerts } from "@/hooks/use-api"
import { apiClient, type Alert } from "@/lib/api-client"
import { Bell, CheckCheck, Trash2, AlertCircle, AlertTriangle, Info, CheckCircle, Loader2 } from "lucide-react"
import { formatDistanceToNow } from "date-fns"
import { toast } from "sonner"

export function AlertsDashboard() {
  const [showUnreadOnly, setShowUnreadOnly] = useState(false)
  const { alerts, isLoading, refresh } = useAlerts(showUnreadOnly)

  const unreadCount = Array.isArray(alerts) ? alerts.filter((a) => !a.read).length : 0

  const handleMarkRead = async (alertId: string) => {
    try {
      await apiClient.markAlertRead(alertId)
      await refresh()
      toast.success("Alert marked as read")
    } catch (error) {
      toast.error("Failed to mark alert as read")
    }
  }

  const handleMarkAllRead = async () => {
    try {
      await apiClient.markAllAlertsRead()
      await refresh()
      toast.success("All alerts marked as read")
    } catch (error) {
      toast.error("Failed to mark alerts as read")
    }
  }

  const handleDelete = async (alertId: string) => {
    try {
      await apiClient.deleteAlert(alertId)
      await refresh()
      toast.success("Alert deleted")
    } catch (error) {
      toast.error("Failed to delete alert")
    }
  }

  const getSeverityIcon = (severity: Alert["severity"]) => {
    switch (severity) {
      case "error":
        return <AlertCircle className="h-5 w-5 text-destructive" />
      case "warning":
        return <AlertTriangle className="h-5 w-5 text-yellow-500" />
      case "success":
        return <CheckCircle className="h-5 w-5 text-green-500" />
      default:
        return <Info className="h-5 w-5 text-blue-500" />
    }
  }

  const getSeverityBadge = (severity: Alert["severity"]) => {
    const variants: Record<Alert["severity"], "default" | "secondary" | "destructive" | "outline"> = {
      error: "destructive",
      warning: "default",
      success: "outline",
      info: "secondary",
    }

    return <Badge variant={variants[severity]}>{severity.toUpperCase()}</Badge>
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex items-start justify-between">
          <div>
            <CardTitle className="flex items-center gap-2">
              <Bell className="h-5 w-5" />
              Alerts Center
              {unreadCount > 0 && (
                <Badge variant="destructive" className="ml-2">
                  {unreadCount} new
                </Badge>
              )}
            </CardTitle>
            <CardDescription>Monitor system alerts and job notifications</CardDescription>
          </div>
          <div className="flex items-center gap-2">
            <Button variant="outline" size="sm" onClick={() => setShowUnreadOnly(!showUnreadOnly)}>
              {showUnreadOnly ? "Show All" : "Unread Only"}
            </Button>
            {unreadCount > 0 && (
              <Button variant="outline" size="sm" onClick={handleMarkAllRead}>
                <CheckCheck className="h-4 w-4 mr-2" />
                Mark All Read
              </Button>
            )}
          </div>
        </div>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
          </div>
        ) : !Array.isArray(alerts) || alerts.length === 0 ? (
          <div className="text-center py-8">
            <Bell className="h-12 w-12 text-muted-foreground mx-auto mb-3 opacity-50" />
            <p className="text-muted-foreground">{showUnreadOnly ? "No unread alerts" : "No alerts yet"}</p>
          </div>
        ) : (
          <ScrollArea className="h-[600px] pr-4">
            <div className="space-y-4">
              {alerts.map((alert) => (
                <div
                  key={alert.id}
                  className={`border rounded-lg p-4 space-y-3 transition-colors ${
                    alert.read ? "bg-background" : "bg-accent/50"
                  }`}
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex items-start gap-3 flex-1">
                      {getSeverityIcon(alert.severity)}
                      <div className="flex-1 space-y-1">
                        <div className="flex items-center gap-2">
                          <h4 className="font-semibold text-sm">{alert.title}</h4>
                          {getSeverityBadge(alert.severity)}
                          {!alert.read && (
                            <Badge variant="secondary" className="text-xs">
                              NEW
                            </Badge>
                          )}
                        </div>
                        <p className="text-sm text-muted-foreground">{alert.message}</p>
                        {alert.job_name && <p className="text-xs text-muted-foreground">Job: {alert.job_name}</p>}
                        <p className="text-xs text-muted-foreground">
                          {formatDistanceToNow(new Date(alert.created_at), { addSuffix: true })}
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center gap-1">
                      {!alert.read && (
                        <Button variant="ghost" size="sm" onClick={() => handleMarkRead(alert.id)}>
                          <CheckCheck className="h-4 w-4" />
                        </Button>
                      )}
                      <Button variant="ghost" size="sm" onClick={() => handleDelete(alert.id)}>
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </ScrollArea>
        )}
      </CardContent>
    </Card>
  )
}
