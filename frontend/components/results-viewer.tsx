"use client"

import { useState } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Shield, AlertTriangle, Info, ExternalLink, FileText, ImageIcon, Download } from "lucide-react"

interface Finding {
  url: string
  title: string
  category: string
  risk_level: string
  risk_score: number
  threats: string[]
  text_excerpt?: string
  screenshot_path?: string
  text_path?: string
  html_path?: string
}

interface ResultsViewerProps {
  findings: Finding[]
  jobId?: string
}

export function ResultsViewer({ findings, jobId }: ResultsViewerProps) {
  const [selectedFinding, setSelectedFinding] = useState<Finding | null>(null)

  const getRiskColor = (risk: string) => {
    switch (risk.toLowerCase()) {
      case "critical":
        return "text-red-500"
      case "high":
        return "text-orange-500"
      case "medium":
        return "text-yellow-500"
      case "low":
        return "text-blue-500"
      default:
        return "text-gray-500"
    }
  }

  const getRiskIcon = (risk: string) => {
    switch (risk.toLowerCase()) {
      case "critical":
      case "high":
        return <AlertTriangle className="h-4 w-4" />
      case "medium":
        return <Shield className="h-4 w-4" />
      default:
        return <Info className="h-4 w-4" />
    }
  }

  const handleDownloadFile = (filePath: string | undefined, filename: string) => {
    if (!filePath) return

    // Convert relative path to API URL
    const apiUrl = `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/files/${filePath}`

    // Open in new tab or trigger download
    window.open(apiUrl, "_blank")
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold">Search Results</h2>
        <Badge variant="outline">{findings.length} findings</Badge>
      </div>

      <div className="grid gap-4">
        {findings.map((finding, idx) => (
          <Card key={idx} className="hover:bg-accent/50 transition-colors">
            <CardHeader>
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1 space-y-1">
                  <CardTitle className="text-lg flex items-center gap-2">
                    {finding.title || "Untitled"}
                    <span className={`flex items-center gap-1 text-sm ${getRiskColor(finding.risk_level)}`}>
                      {getRiskIcon(finding.risk_level)}
                      {finding.risk_level}
                    </span>
                  </CardTitle>
                  <CardDescription className="flex items-center gap-2">
                    <ExternalLink className="h-3 w-3" />
                    <span className="text-xs break-all">{finding.url}</span>
                  </CardDescription>
                </div>
                <Badge variant="secondary">{finding.category}</Badge>
              </div>
            </CardHeader>

            <CardContent className="space-y-4">
              {finding.text_excerpt && (
                <p className="text-sm text-muted-foreground line-clamp-3">{finding.text_excerpt}</p>
              )}

              {finding.threats && finding.threats.length > 0 && (
                <div className="flex flex-wrap gap-2">
                  {finding.threats.slice(0, 3).map((threat, i) => (
                    <Badge key={i} variant="destructive" className="text-xs">
                      {threat}
                    </Badge>
                  ))}
                  {finding.threats.length > 3 && (
                    <Badge variant="outline" className="text-xs">
                      +{finding.threats.length - 3} more
                    </Badge>
                  )}
                </div>
              )}

              <div className="flex gap-2">
                {finding.text_path && (
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => handleDownloadFile(finding.text_path, "content.txt")}
                  >
                    <FileText className="h-4 w-4 mr-2" />
                    View Text
                  </Button>
                )}

                {finding.screenshot_path && (
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => handleDownloadFile(finding.screenshot_path, "screenshot.png")}
                  >
                    <ImageIcon className="h-4 w-4 mr-2" />
                    View Screenshot
                  </Button>
                )}

                {finding.html_path && (
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => handleDownloadFile(finding.html_path, "page.html")}
                  >
                    <Download className="h-4 w-4 mr-2" />
                    Download HTML
                  </Button>
                )}

                <Dialog>
                  <DialogTrigger asChild>
                    <Button size="sm" onClick={() => setSelectedFinding(finding)}>
                      View Details
                    </Button>
                  </DialogTrigger>
                  <DialogContent className="max-w-3xl max-h-[80vh]">
                    <DialogHeader>
                      <DialogTitle>{finding.title}</DialogTitle>
                    </DialogHeader>
                    <ScrollArea className="h-[60vh]">
                      <div className="space-y-4 p-4">
                        <div>
                          <h4 className="font-semibold mb-2">URL</h4>
                          <p className="text-sm text-muted-foreground break-all">{finding.url}</p>
                        </div>

                        <div>
                          <h4 className="font-semibold mb-2">Risk Assessment</h4>
                          <div className="flex items-center gap-2">
                            <Badge className={getRiskColor(finding.risk_level)}>
                              {finding.risk_level} ({finding.risk_score}/10)
                            </Badge>
                          </div>
                        </div>

                        {finding.threats && finding.threats.length > 0 && (
                          <div>
                            <h4 className="font-semibold mb-2">Detected Threats</h4>
                            <div className="flex flex-wrap gap-2">
                              {finding.threats.map((threat, i) => (
                                <Badge key={i} variant="destructive">
                                  {threat}
                                </Badge>
                              ))}
                            </div>
                          </div>
                        )}

                        {finding.text_excerpt && (
                          <div>
                            <h4 className="font-semibold mb-2">Content Preview</h4>
                            <p className="text-sm text-muted-foreground whitespace-pre-wrap">{finding.text_excerpt}</p>
                          </div>
                        )}
                      </div>
                    </ScrollArea>
                  </DialogContent>
                </Dialog>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  )
}
