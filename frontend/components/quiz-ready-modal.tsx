"use client"

import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { CheckCircle2 } from "lucide-react"

interface QuizReadyModalProps {
  isOpen: boolean
  totalQuestions: number
  onStart: () => void
}

export function QuizReadyModal({ isOpen, totalQuestions, onStart }: QuizReadyModalProps) {
  return (
    <Dialog open={isOpen}>
      <DialogContent showCloseButton={false} className="sm:max-w-md">
        <DialogHeader>
          <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-green-500/10">
            <CheckCircle2 className="h-8 w-8 text-green-500" />
          </div>
          <DialogTitle className="text-center">Questions Ready!</DialogTitle>
          <DialogDescription className="text-center">
            {totalQuestions} question{totalQuestions !== 1 ? 's' : ''} have been generated from your learning materials.
            Are you ready to start the questionnaire?
          </DialogDescription>
        </DialogHeader>
        <DialogFooter className="sm:justify-center">
          <Button onClick={onStart} className="w-full sm:w-auto">
            Start Questionnaire
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

