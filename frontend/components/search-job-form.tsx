"use client"

import type React from "react"

import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Checkbox } from "@/components/ui/checkbox"
import { toast } from "sonner"
import { apiClient, type SearchParams } from "@/lib/api-client"
import { Loader2, Search } from "lucide-react"

interface SearchJobFormProps {
  onJobCreated?: (jobId: string) => void
}

export function SearchJobForm({ onJobCreated }: SearchJobFormProps) {
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [formData, setFormData] = useState<SearchParams>({
    keyword: "",
    job_name: "",
    max_results: 100,
    depth: 2,
    timeout_seconds: 30,
    include_summary: true,
    model_choice: "gemini-2.5-flash",
    pgp_verify: true,
    report_type: "threat_intel",
  })

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    if (!formData.keyword.trim()) {
      toast.error("Please enter a search keyword")
      return
    }

    setIsSubmitting(true)

    try {
      const response = await apiClient.createSearchJob(formData)
      toast.success(`Search job created successfully`, {
        description: `Job ID: ${response.job_id}`,
      })

      // Reset form
      setFormData({
        keyword: "",
        job_name: "",
        max_results: 100,
        depth: 2,
        timeout_seconds: 30,
        include_summary: true,
        model_choice: "gemini-2.5-flash",
        pgp_verify: true,
        report_type: "threat_intel",
      })

      onJobCreated?.(response.job_id)
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Failed to create search job")
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Create Search Job</CardTitle>
        <CardDescription>Configure and launch a dark web search investigation</CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-6">
          <div className="space-y-2">
            <Label htmlFor="job_name">Job Name (Optional)</Label>
            <Input
              id="job_name"
              placeholder="e.g., Ransomware Investigation 2024"
              value={formData.job_name}
              onChange={(e) => setFormData({ ...formData, job_name: e.target.value })}
            />
            <p className="text-sm text-muted-foreground">If not provided, one will be generated from your search</p>
          </div>

          <div className="space-y-2">
            <Label htmlFor="keyword">Search Keyword *</Label>
            <Input
              id="keyword"
              placeholder="e.g., ransomware, data breach, stolen credentials"
              value={formData.keyword}
              onChange={(e) => setFormData({ ...formData, keyword: e.target.value })}
              required
            />
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="max_results">Max Results</Label>
              <Input
                id="max_results"
                type="number"
                min="10"
                max="10000"
                value={formData.max_results || 100}
                onChange={(e) => setFormData({ ...formData, max_results: Number.parseInt(e.target.value) || 100 })}
              />
            </div>

            {/* Depth */}
            <div className="space-y-2">
              <Label htmlFor="depth">Crawl Depth</Label>
              <Select
                value={formData.depth?.toString() || "2"}
                onValueChange={(value) => setFormData({ ...formData, depth: Number.parseInt(value) })}
              >
                <SelectTrigger id="depth">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="1">1 - Quick scan</SelectItem>
                  <SelectItem value="2">2 - Standard</SelectItem>
                  <SelectItem value="3">3 - Deep scan</SelectItem>
                  <SelectItem value="4">4 - Very deep</SelectItem>
                  <SelectItem value="5">5 - Maximum depth</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label htmlFor="timeout_seconds">Timeout (seconds)</Label>
              <Input
                id="timeout_seconds"
                type="number"
                min="10"
                max="300"
                value={formData.timeout_seconds || 30}
                onChange={(e) => setFormData({ ...formData, timeout_seconds: Number.parseInt(e.target.value) || 30 })}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="model_choice">AI Model</Label>
              <Select
                value={formData.model_choice}
                onValueChange={(value) => setFormData({ ...formData, model_choice: value })}
              >
                <SelectTrigger id="model_choice">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="gemini-2.5-flash">Gemini 2.5 Flash (Default)</SelectItem>
                  <SelectItem value="gpt-5-mini">GPT-5 Mini</SelectItem>
                  <SelectItem value="claude-sonnet-4-5">Claude Sonnet 4.5</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label htmlFor="report_type">Intelligence Report Type</Label>
              <Select
                value={formData.report_type}
                onValueChange={(value) => setFormData({ ...formData, report_type: value as any })}
              >
                <SelectTrigger id="report_type">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="threat_intel">General Threat Intel</SelectItem>
                  <SelectItem value="ransomware_malware">Malware & Ransomware</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          <div className="space-y-4">
            <div className="flex items-center space-x-2">
              <Checkbox
                id="include_summary"
                checked={formData.include_summary}
                onCheckedChange={(checked) => setFormData({ ...formData, include_summary: checked as boolean })}
              />
              <Label htmlFor="include_summary" className="cursor-pointer">
                Generate AI summary of results
              </Label>
            </div>

            <div className="flex items-center space-x-2">
              <Checkbox
                id="pgp_verify"
                checked={formData.pgp_verify}
                onCheckedChange={(checked) => setFormData({ ...formData, pgp_verify: checked as boolean })}
              />
              <Label htmlFor="pgp_verify" className="cursor-pointer">
                Verify .onion site legitimacy via PGP
              </Label>
            </div>
          </div>

          <Button type="submit" disabled={isSubmitting} className="w-full">
            {isSubmitting ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Creating Job...
              </>
            ) : (
              <>
                <Search className="mr-2 h-4 w-4" />
                Start Search
              </>
            )}
          </Button>
        </form>
      </CardContent>
    </Card>
  )
}
