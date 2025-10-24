"use client"

interface ProgressBarProps {
  current: number
  total: number
}

export function ProgressBar({ current, total }: ProgressBarProps) {
  const percentage = (current / total) * 100

  return (
    <div className="border-b border-border bg-card px-6 py-3">
      <div className="mx-auto max-w-3xl">
        <div className="mb-2 flex items-center justify-between text-sm">
          <span className="font-medium text-card-foreground">Learning Progress</span>
          <span className="text-muted-foreground">
            Question {current} of {total}
          </span>
        </div>
        <div className="h-2 overflow-hidden rounded-full bg-secondary">
          <div
            className="h-full rounded-full bg-primary transition-all duration-500 ease-out"
            style={{ width: `${percentage}%` }}
          />
        </div>
      </div>
    </div>
  )
}
