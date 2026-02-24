"use client"

import { useState, useEffect, useRef } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { X, RefreshCw, Loader2, AlertCircle } from "lucide-react"
import { apiClient } from "@/lib/api-client"
import { toast } from "sonner"

interface LiveMirrorViewerProps {
  sessionId: string
  targetUrl: string
  onClose: () => void
}

export function LiveMirrorViewer({ sessionId, targetUrl, onClose }: LiveMirrorViewerProps) {
  const [isConnected, setIsConnected] = useState(false)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [currentHtml, setCurrentHtml] = useState("")
  const [currentUrl, setCurrentUrl] = useState(targetUrl)
  const [screenshot, setScreenshot] = useState("")
  const [pageTitle, setPageTitle] = useState("")
  const wsRef = useRef<WebSocket | null>(null)
  const iframeRef = useRef<HTMLIFrameElement | null>(null)

  useEffect(() => {
    connectWebSocket()

    return () => {
      if (wsRef.current) {
        wsRef.current.close()
      }
    }
  }, [sessionId])

  const connectWebSocket = () => {
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:"
    const wsUrl = `${protocol}//localhost:8000/api/v1/ws/live/${sessionId}`

    console.log("[v0] Connecting to WebSocket:", wsUrl)

    const ws = new WebSocket(wsUrl)

    ws.onopen = () => {
      console.log("[LiveMirror] WebSocket connected")
      setIsConnected(true)
      setIsLoading(false)
      setError(null)
    }

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)

        if (data.type === "snapshot") {
          const snapshot = data.data
          if (snapshot.html) {
            setCurrentHtml(snapshot.html)
          }
          if (snapshot.screenshot) {
            setScreenshot(snapshot.screenshot)
          }
          if (snapshot.current_url) {
            setCurrentUrl(snapshot.current_url)
          }
          if (snapshot.title) {
            setPageTitle(snapshot.title)
          }
        } else if (data.type === "error") {
          setError(data.message)
          toast.error(`Live mirror error: ${data.message}`)
        }
      } catch (err) {
        console.error("[LiveMirror] Failed to parse message:", err)
      }
    }

    ws.onerror = (err) => {
      console.error("[LiveMirror] WebSocket error:", err)
      setError("WebSocket connection error")
      setIsLoading(false)
    }

    ws.onclose = () => {
      console.log("[LiveMirror] WebSocket closed")
      setIsConnected(false)
    }

    wsRef.current = ws
  }

  const handleRefresh = () => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: "refresh" }))
      toast.success("Refreshing page...")
    }
  }

  const handleClose = async () => {
    try {
      await apiClient.stopLiveMirror(sessionId)
      onClose()
    } catch (error) {
      console.error("[LiveMirror] Failed to stop session:", error)
      onClose()
    }
  }

  return (
    <Card className="bg-neutral-900 border-orange-900/30 h-full flex flex-col">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <div className="flex-1">
            <CardTitle className="text-sm font-medium text-orange-400 tracking-wider flex items-center gap-2">
              LIVE MIRROR
              {isConnected && <span className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></span>}
            </CardTitle>
            <p className="text-xs text-neutral-500 mt-1">{currentUrl}</p>
            {pageTitle && <p className="text-xs text-neutral-400 mt-1">{pageTitle}</p>}
          </div>
          <div className="flex gap-2">
            <Button
              onClick={handleRefresh}
              variant="ghost"
              size="icon"
              disabled={!isConnected}
              className="text-neutral-400 hover:text-orange-500"
              title="Refresh"
            >
              <RefreshCw className="w-4 h-4" />
            </Button>
            <Button
              onClick={handleClose}
              variant="ghost"
              size="icon"
              className="text-neutral-400 hover:text-red-400"
              title="Close"
            >
              <X className="w-4 h-4" />
            </Button>
          </div>
        </div>
      </CardHeader>
      <CardContent className="flex-1 p-0 relative">
        {isLoading ? (
          <div className="flex flex-col items-center justify-center h-full gap-4">
            <Loader2 className="w-12 h-12 animate-spin text-orange-500" />
            <p className="text-sm text-neutral-400">Connecting to live mirror...</p>
          </div>
        ) : error ? (
          <div className="flex flex-col items-center justify-center h-full gap-4 p-6">
            <AlertCircle className="w-12 h-12 text-red-500" />
            <p className="text-sm text-red-400 text-center">{error}</p>
            <Button onClick={connectWebSocket} variant="outline" size="sm">
              Retry Connection
            </Button>
          </div>
        ) : screenshot ? (
          <div className="h-full overflow-auto p-4">
            <img
              src={`data:image/png;base64,${screenshot}`}
              alt="Live mirror screenshot"
              className="w-full border border-neutral-700 rounded"
            />
            <div className="mt-4 p-4 bg-neutral-800 rounded border border-neutral-700">
              <p className="text-xs text-neutral-400 mb-2">Page HTML (sanitized):</p>
              <div className="max-h-96 overflow-auto">
                <pre className="text-xs text-neutral-300 whitespace-pre-wrap break-all">
                  {currentHtml.substring(0, 2000)}
                  {currentHtml.length > 2000 && "..."}
                </pre>
              </div>
            </div>
          </div>
        ) : (
          <div className="flex items-center justify-center h-full">
            <p className="text-sm text-neutral-500">No content available</p>
          </div>
        )}
      </CardContent>
    </Card>
  )
}




