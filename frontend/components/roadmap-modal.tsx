"use client"

import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import { CheckCircle2, Download } from "lucide-react"

interface RoadmapModalProps {
  isOpen: boolean
  onClose: () => void
  topics: string[]
}

export function RoadmapModal({ isOpen, onClose, topics }: RoadmapModalProps) {
  const handleDownload = () => {
    const content = topics.map((topic, index) => `${index + 1}. ${topic}`).join("\n")
    const blob = new Blob([content], { type: "text/plain" })
    const url = URL.createObjectURL(blob)
    const a = document.createElement("a")
    a.href = url
    a.download = "learning-roadmap.txt"
    a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 text-2xl">
            <CheckCircle2 className="h-6 w-6 text-accent" />
            Your Learning Roadmap
          </DialogTitle>
        </DialogHeader>

        <div className="mt-4">
          <p className="mb-6 text-sm text-muted-foreground leading-relaxed">
            Based on your responses and uploaded materials, here's a personalized roadmap of topics to review and
            master. Follow this sequence for optimal learning.
          </p>

          <div className="space-y-3">
            {topics.map((topic, index) => (
              <Card key={index} className="p-4">
                <div className="flex items-start gap-3">
                  <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-primary/10 text-sm font-semibold text-primary">
                    {index + 1}
                  </div>
                  <div className="flex-1 pt-1">
                    <p className="font-medium text-card-foreground leading-relaxed">{topic}</p>
                  </div>
                </div>
              </Card>
            ))}
          </div>

          <div className="mt-6 flex gap-3">
            <Button onClick={handleDownload} variant="outline" className="flex-1 bg-transparent">
              <Download className="mr-2 h-4 w-4" />
              Download Roadmap
            </Button>
            <Button onClick={onClose} className="flex-1">
              Close
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}
