"use client"

import { useState, useEffect } from "react"
import { Monitor, Play, Loader2, ExternalLink, X } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Card } from "@/components/ui/card"
import { LiveMirrorViewer } from "@/components/live-mirror-viewer"
import { apiClient } from "@/lib/api-client"
import { toast } from "sonner"

export default function LiveMirrorPage() {
  const [targetUrl, setTargetUrl] = useState("")
  const [isStarting, setIsStarting] = useState(false)
  const [activeSessions, setActiveSessions] = useState<
    Array<{
      sessionId: string
      targetUrl: string
      startedAt: string
      isInteracting?: boolean  // per-session loading state
    }>
  >([])
  const [selectedSession, setSelectedSession] = useState<{
    sessionId: string
    targetUrl: string
  } | null>(null)

  const handleStartSession = async () => {
    if (!targetUrl.trim() || !targetUrl.includes(".onion")) {
      toast.error("Valid .onion URL required")
      return
    }

    setIsStarting(true)
    try {
      const session = await apiClient.startLiveMirror(targetUrl.trim(), false)

      const newSession = {
        sessionId: session.session_id,
        targetUrl: session.target_url,
        startedAt: new Date().toISOString(),
        isInteracting: false,
      }

      setActiveSessions((prev) => [...prev, newSession])
      setSelectedSession({
        sessionId: session.session_id,
        targetUrl: session.target_url,
      })

      toast.success("Live mirror session started")
      setTargetUrl("")
    } catch (error) {
      console.error("Failed to start session:", error)
      toast.error("Failed to start session")
    } finally {
      setIsStarting(false)
    }
  }

  const handleCloseSession = async (sessionId: string) => {
    try {
      await apiClient.stopLiveMirror(sessionId)
      setActiveSessions((prev) => prev.filter((s) => s.sessionId !== sessionId))

      if (selectedSession?.sessionId === sessionId) {
        setSelectedSession(null)
      }

      toast.success("Session closed (Tor Browser should close soon)")
    } catch (error) {
      console.error("Failed to close session:", error)
      toast.error("Failed to close session")
    }
  }

  const handleInteract = async (sessionId: string, url: string) => {
    if (!url || !sessionId) {
      toast.error("Invalid session")
      return
    }

    // Set loading state for this specific session only
    setActiveSessions((prev) =>
      prev.map((s) =>
        s.sessionId === sessionId ? { ...s, isInteracting: true } : s
      )
    )

    try {
      const response = await fetch("/api/v1/monitor/interact", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ 
          url,
          session_id: sessionId   // Required for backend to track & auto-close Tor
        }),
      })

      if (!response.ok) {
        const errorText = await response.text().catch(() => "Unknown error")
        throw new Error(`HTTP ${response.status}: ${errorText}`)
      }

      const data = await response.json()

      if (data.success) {
        toast.success(data.message || "Tor Browser launched!")
      } else {
        toast.error(data.error || "Failed to launch Tor Browser")
      }
    } catch (err: any) {
      console.error("Interact error:", err)
      toast.error(err.message || "Could not launch Tor Browser")
    } finally {
      // Reset loading state for this session
      setActiveSessions((prev) =>
        prev.map((s) =>
          s.sessionId === sessionId ? { ...s, isInteracting: false } : s
        )
      )
    }
  }

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-orange-500 flex items-center gap-2">
            <Monitor className="w-6 h-6" />
            LIVE MIRROR
          </h1>
          <p className="text-neutral-400 text-sm mt-1">Browse .onion sites in real-time with live mirroring</p>
        </div>
      </div>

      {/* Start New Session */}
      <Card className="bg-neutral-900 border-orange-900/30 p-6">
        <h2 className="text-lg font-semibold text-orange-500 mb-4">Start New Session</h2>

        <div className="flex gap-3">
          <Input
            placeholder="Enter .onion URL (e.g., http://example.onion)"
            value={targetUrl}
            onChange={(e) => setTargetUrl(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleStartSession()}
            className="bg-neutral-800 border-neutral-700 text-white placeholder:text-neutral-500"
          />
          <Button
            onClick={handleStartSession}
            disabled={isStarting || !targetUrl.trim()}
            className="bg-orange-500 hover:bg-orange-600 text-white px-6"
          >
            {isStarting ? (
              <>
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                Starting...
              </>
            ) : (
              <>
                <Play className="w-4 h-4 mr-2" />
                Start
              </>
            )}
          </Button>
        </div>

        <div className="mt-4 text-xs text-neutral-500">
          <p>• Only .onion URLs are supported for security reasons</p>
          <p>• Sessions automatically close after 30 minutes of inactivity</p>
          <p>• JavaScript is disabled by default for safety</p>
        </div>
      </Card>

      {/* Active Sessions */}
      {activeSessions.length > 0 && (
        <Card className="bg-neutral-900 border-orange-900/30 p-6">
          <h2 className="text-lg font-semibold text-orange-500 mb-4">Active Sessions</h2>

          <div className="space-y-3">
            {activeSessions.map((session) => (
              <div
                key={session.sessionId}
                className="flex items-center justify-between p-4 bg-neutral-800 border border-neutral-700 rounded hover:border-orange-500/50 transition-colors"
              >
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <div className="w-2 h-2 bg-orange-500 rounded-full animate-pulse" />
                    <span className="text-white font-medium truncate max-w-[300px]">
                      {session.targetUrl}
                    </span>
                  </div>
                  <div className="text-xs text-neutral-500 mt-1">
                    Started: {new Date(session.startedAt).toLocaleTimeString()}
                  </div>
                </div>

                <div className="flex gap-2">
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => handleInteract(session.sessionId, session.targetUrl)}
                    disabled={session.isInteracting}  // per-session disable
                    className="border-orange-500/50 text-orange-500 hover:bg-orange-500/10"
                  >
                    {session.isInteracting ? (
                      <>
                        <Loader2 className="w-4 h-4 mr-1 animate-spin" />
                        Opening...
                      </>
                    ) : (
                      <>
                        <ExternalLink className="w-4 h-4 mr-1" />
                        Interact
                      </>
                    )}
                  </Button>

                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => handleCloseSession(session.sessionId)}
                    className="border-red-500/50 text-red-500 hover:bg-red-500/10"
                  >
                    Close
                  </Button>
                </div>
              </div>
            ))}
          </div>
        </Card>
      )}

      {/* Live Mirror Viewer */}
      {selectedSession && (
        <LiveMirrorViewer
          sessionId={selectedSession.sessionId}
          targetUrl={selectedSession.targetUrl}
          onClose={() => setSelectedSession(null)}
        />
      )}

      {/* Empty State */}
      {activeSessions.length === 0 && !selectedSession && (
        <Card className="bg-neutral-900 border-orange-900/30 p-12 text-center">
          <Monitor className="w-16 h-16 mx-auto text-neutral-600 mb-4" />
          <h3 className="text-lg font-semibold text-neutral-400 mb-2">No Active Sessions</h3>
          <p className="text-neutral-500 text-sm">
            Start a new live mirror session to browse .onion sites in real-time
          </p>
        </Card>
      )}
    </div>
  )
}