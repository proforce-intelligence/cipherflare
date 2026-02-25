"use client"

import type React from "react"

import { useState } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Checkbox } from "@/components/ui/checkbox"
import { apiClient, type MonitoringJobConfig } from "@/lib/api-client"
import { toast } from "sonner"
import { Loader2, Lock, Monitor } from "lucide-react"

interface MonitorJobFormProps {
  onJobCreated?: (jobId: string) => void
}

export function MonitorJobForm({ onJobCreated }: MonitorJobFormProps) {
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [requiresAuth, setRequiresAuth] = useState(false)
  const [formData, setFormData] = useState<MonitoringJobConfig>({
    url: "",
    interval_hours: 6,
    username: "",
    password: "",
    login_path: "",
  })

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    if (!formData.url.trim()) {
      toast.error("Please enter a .onion URL")
      return
    }

    if (!formData.url.match(/^http:\/\/.*\.onion/)) {
      toast.error("Invalid .onion URL format")
      return
    }

    if (requiresAuth && (!formData.username || !formData.password)) {
      toast.error("Please provide authentication credentials")
      return
    }

    setIsSubmitting(true)

    try {
      const config: MonitoringJobConfig = {
        url: formData.url,
        interval_hours: formData.interval_hours || 6,
      }

      if (requiresAuth) {
        config.username = formData.username
        config.password = formData.password
        config.login_path = formData.login_path || ""
      }

      const response = await apiClient.setupMonitoring(config)
      toast.success("Monitoring job created successfully", {
        description: `Job ID: ${response.job_id}`,
      })

      // Reset form
      setFormData({
        url: "",
        interval_hours: 6,
        username: "",
        password: "",
        login_path: "",
      })
      setRequiresAuth(false)

      onJobCreated?.(response.job_id)
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Failed to create monitoring job")
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <Card className="bg-neutral-900 border-orange-900/30">
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-orange-400">
          <Monitor className="w-5 h-5" />
          Setup Continuous Monitoring
        </CardTitle>
        <CardDescription>
          Configure a dark web site to monitor continuously with optional authentication
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-6">
          {/* Target URL */}
          <div className="space-y-2">
            <Label htmlFor="url">Target .onion URL *</Label>
            <Input
              id="url"
              placeholder="http://example.onion"
              value={formData.url}
              onChange={(e) => setFormData({ ...formData, url: e.target.value })}
              required
            />
            <p className="text-xs text-neutral-500">The dark web site you want to monitor continuously</p>
          </div>

          {/* Check Interval */}
          <div className="space-y-2">
            <Label htmlFor="interval">Check Interval</Label>
            <Select
              value={formData.interval_hours?.toString()}
              onValueChange={(value) => setFormData({ ...formData, interval_hours: Number.parseInt(value) })}
            >
              <SelectTrigger id="interval">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="1">Every hour</SelectItem>
                <SelectItem value="3">Every 3 hours</SelectItem>
                <SelectItem value="6">Every 6 hours (Recommended)</SelectItem>
                <SelectItem value="12">Every 12 hours</SelectItem>
                <SelectItem value="24">Every 24 hours</SelectItem>
              </SelectContent>
            </Select>
            <p className="text-xs text-neutral-500">How often to check the site for changes</p>
          </div>

          {/* Authentication Toggle */}
          <div className="flex items-center space-x-2 pt-2">
            <Checkbox
              id="requires-auth"
              checked={requiresAuth}
              onCheckedChange={(checked) => setRequiresAuth(checked as boolean)}
            />
            <Label htmlFor="requires-auth" className="flex items-center gap-2 cursor-pointer">
              <Lock className="w-4 h-4" />
              Site requires authentication
            </Label>
          </div>

          {/* Authentication Fields */}
          {requiresAuth && (
            <div className="space-y-4 p-4 bg-neutral-800 rounded-lg border border-orange-900/30">
              <p className="text-xs text-neutral-400 mb-3">
                Provide credentials to access authenticated dark web sites. All credentials are encrypted before
                storage.
              </p>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="username">Username</Label>
                  <Input
                    id="username"
                    placeholder="Username"
                    value={formData.username}
                    onChange={(e) => setFormData({ ...formData, username: e.target.value })}
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="password">Password</Label>
                  <Input
                    id="password"
                    type="password"
                    placeholder="Password"
                    value={formData.password}
                    onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                  />
                </div>

                <div className="space-y-2 md:col-span-2">
                  <Label htmlFor="login_path">Login Path (optional)</Label>
                  <Input
                    id="login_path"
                    placeholder="/login or leave empty"
                    value={formData.login_path}
                    onChange={(e) => setFormData({ ...formData, login_path: e.target.value })}
                  />
                  <p className="text-xs text-neutral-500">Relative path to login page if different from main URL</p>
                </div>
              </div>
            </div>
          )}

          <Button type="submit" disabled={isSubmitting} className="w-full bg-orange-500 hover:bg-orange-600 text-black">
            {isSubmitting ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Creating Monitoring Job...
              </>
            ) : (
              <>
                <Monitor className="mr-2 h-4 w-4" />
                Start Monitoring
              </>
            )}
          </Button>
        </form>
      </CardContent>
    </Card>
  )
}
