"use client"

import { useState } from "react"
import { Monitor, Play, Loader2, ExternalLink } from "lucide-react"
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
    }>
  >([])
  const [selectedSession, setSelectedSession] = useState<{
    sessionId: string
    targetUrl: string
  } | null>(null)

  const handleStartSession = async () => {
    if (!targetUrl.trim()) {
      toast.error("Please enter a .onion URL")
      return
    }

    if (!targetUrl.endsWith(".onion") && !targetUrl.includes(".onion/")) {
      toast.error("Only .onion URLs are supported")
      return
    }

    setIsStarting(true)
    try {
      const session = await apiClient.startLiveMirror(targetUrl, false)

      const newSession = {
        sessionId: session.session_id,
        targetUrl: session.target_url,
        startedAt: new Date().toISOString(),
      }

      setActiveSessions((prev) => [...prev, newSession])
      setSelectedSession({
        sessionId: session.session_id,
        targetUrl: session.target_url,
      })

      toast.success("Live mirror session started")
      setTargetUrl("")
    } catch (error) {
      console.error("Failed to start live mirror:", error)
      toast.error("Failed to start live mirror session")
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

      toast.success("Session closed")
    } catch (error) {
      console.error("Failed to close session:", error)
      toast.error("Failed to close session")
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
                    <span className="text-white font-medium">{session.targetUrl}</span>
                  </div>
                  <div className="text-xs text-neutral-500 mt-1">
                    Started: {new Date(session.startedAt).toLocaleTimeString()}
                  </div>
                </div>

                <div className="flex gap-2">
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() =>
                      setSelectedSession({
                        sessionId: session.sessionId,
                        targetUrl: session.targetUrl,
                      })
                    }
                    className="border-orange-500/50 text-orange-500 hover:bg-orange-500/10"
                  >
                    <ExternalLink className="w-4 h-4 mr-1" />
                    View
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
