'use client'

import { useState, useRef, useEffect } from 'react'
import { motion } from 'framer-motion'
import { User, Bot, AlertCircle, Brain, FileText, CheckCircle2, Copy, Check, Loader2, Sparkles, Wand2, ChevronDown, ChevronRight, Globe, ThumbsUp, ThumbsDown, MessageSquare, Send, X } from 'lucide-react'
import { Avatar, AvatarFallback } from '@/components/ui/avatar'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from '@/components/ui/dialog'
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible'
import { MarkdownRenderer } from '@/components/MarkdownRenderer'
import { usePdfViewer } from '@/hooks/usePdfViewer'
import { PdfViewer } from '@/components/PdfViewer'
import { AnimatedLoadingText } from '@/components/AnimatedLoadingText'
import { Textarea } from '@/components/ui/textarea'
import { Label } from '@/components/ui/label'
import { submitFeedback } from '@/lib/feedbackService'
import { toast } from 'sonner'

interface Message {
  id: string
  content: string
  role: 'user' | 'assistant' | 'system'
  timestamp: Date
  response?: any
  queryMode?: 'qa' | 'deep_think' | 'brainstorm'
  isThinking?: boolean
  currentStep?: string
  attachedFiles?: { name: string; size: number; type: string }[]
  internetEnabled?: boolean
}

interface ChatMessageProps {
  message: Message
  onCopyToDraft?: (content: string) => void
}

// Utility function to format time consistently across server and client
function formatTime(date: Date): string {
  const hours = date.getHours()
  const minutes = date.getMinutes()
  const ampm = hours >= 12 ? 'PM' : 'AM'
  const displayHours = hours % 12 || 12
  const displayMinutes = minutes.toString().padStart(2, '0')
  return `${displayHours}:${displayMinutes} ${ampm}`
}

export function ChatMessage({ message, onCopyToDraft }: ChatMessageProps) {
  const [isDevInfoDialogOpen, setIsDevInfoDialogOpen] = useState(false)
  const [copied, setCopied] = useState(false)
  const [showSelectionTooltip, setShowSelectionTooltip] = useState(false)
  const [selectedText, setSelectedText] = useState('')
  const [loadingCitationIndex, setLoadingCitationIndex] = useState<number | null>(null)
  const [isSourcesOpen, setIsSourcesOpen] = useState(false)
  const messageRef = useRef<HTMLDivElement>(null)
  const tooltipRef = useRef<HTMLDivElement>(null)

  // Feedback State
  const [feedbackStatus, setFeedbackStatus] = useState<'idle' | 'up' | 'down'>('idle')
  const [isFeedbackDialogOpen, setIsFeedbackDialogOpen] = useState(false)
  const [feedbackComment, setFeedbackComment] = useState('')
  const [isSubmittingFeedback, setIsSubmittingFeedback] = useState(false)

  // PDF Viewer Hook (temporarily using openPdf instead of openWithSnippet)
  const { state: pdfState, openPdf, closePdf } = usePdfViewer()

  // Handle text selection within this message
  useEffect(() => {
    const handleSelection = () => {
      const selection = window.getSelection()
      if (!selection || selection.rangeCount === 0) {
        setShowSelectionTooltip(false)
        setSelectedText('')
        return
      }

      const range = selection.getRangeAt(0)
      const messageElement = messageRef.current

      // Check if selection is within this message
      if (messageElement && messageElement.contains(range.commonAncestorContainer)) {
        const selectedTextContent = selection.toString().trim()
        if (selectedTextContent && message.role === 'assistant') {
          setSelectedText(selectedTextContent)
          setShowSelectionTooltip(true)
        } else {
          setShowSelectionTooltip(false)
          setSelectedText('')
        }
      } else {
        setShowSelectionTooltip(false)
        setSelectedText('')
      }
    }

    document.addEventListener('mouseup', handleSelection)
    document.addEventListener('selectionchange', handleSelection)

    return () => {
      document.removeEventListener('mouseup', handleSelection)
      document.removeEventListener('selectionchange', handleSelection)
    }
  }, [message.role])

  // Position tooltip near selection
  useEffect(() => {
    if (showSelectionTooltip && tooltipRef.current) {
      const selection = window.getSelection()
      if (selection && selection.rangeCount > 0) {
        const range = selection.getRangeAt(0)
        const rect = range.getBoundingClientRect()
        const tooltip = tooltipRef.current

        // Position tooltip above selection, centered
        tooltip.style.position = 'fixed'
        tooltip.style.top = `${rect.top - 40}px`
        tooltip.style.left = `${rect.left + rect.width / 2}px`
        tooltip.style.transform = 'translateX(-50%)'
      }
    }
  }, [showSelectionTooltip, selectedText])

  // Extract dev info content from message
  const extractDevInfoContent = (content: string) => {
    const thinkMatch = content.match(/<think>([\s\S]*?)<\/think>/i)
    return thinkMatch ? thinkMatch[1].trim() : null
  }

  // Clean message content by removing think tags
  const cleanMessageContent = (content: string) => {
    if (!content) return ''
    return content.replace(/<think>[\s\S]*?<\/think>/gi, '').trim()
  }

  // Get HTML content from message (preserve formatting)
  const getMessageHTML = () => {
    if (messageRef.current) {
      const messageElement = messageRef.current.querySelector('[class*="break-words"]')
      if (messageElement) {
        return messageElement.innerHTML
      }
    }
    // Fallback to markdown-rendered content
    return cleanMessageContent(message.content)
  }

  const handleCopyToDraft = (content: string, isHTML: boolean = false) => {
    if (onCopyToDraft) {
      // If HTML, wrap in a div to preserve formatting
      const formattedContent = isHTML ? `<div>${content}</div>` : content
      onCopyToDraft(formattedContent)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    }
  }

  const handleCopySelection = () => {
    if (selectedText) {
      handleCopyToDraft(selectedText, false)
      setShowSelectionTooltip(false)
      window.getSelection()?.removeAllRanges()
    }
  }

  const handleCopyFullMessage = () => {
    const htmlContent = getMessageHTML()
    handleCopyToDraft(htmlContent, true)
  }


  // For cloud models, we don't have <think> tags, so we'll show generic dev info
  const getDevInfoForCloudModel = (queryMode: string) => {
    if (queryMode === 'deep_think') {
      return "This response was generated using deep thinking mode, which encourages step-by-step analysis and multiple perspectives."
    } else if (queryMode === 'brainstorm') {
      return "This response was generated using brainstorm mode, which encourages creative and innovative thinking."
    }
    return null
  }

  const devInfoContent = extractDevInfoContent(message.content)
  const cleanContent = cleanMessageContent(message.content)
  const cloudDevInfoContent = getDevInfoForCloudModel(message.queryMode || '')

  const getAvatarIcon = () => {
    switch (message.role) {
      case 'user':
        return <User className="h-4 w-4" />
      case 'assistant':
        return <Bot className="h-4 w-4" />
      case 'system':
        return <AlertCircle className="h-4 w-4" />
      default:
        return null
    }
  }

  const getInitials = () => {
    switch (message.role) {
      case 'user':
        return 'U'
      case 'assistant':
        return 'AI'
      case 'system':
        return 'S'
      default:
        return '?'
    }
  }

  const isUser = message.role === 'user'
  const isSystem = message.role === 'system'

  // Check if dev info data exists
  const hasDevInfoData = message.role === 'assistant' && (
    message.isThinking ||
    ((message.queryMode === 'deep_think' || message.queryMode === 'qa') && (message.response?.processing_trace || devInfoContent || cloudDevInfoContent))
  )

  // Handle avatar click with Shift key
  const handleAvatarClick = (e: React.MouseEvent) => {
    if (e.shiftKey && hasDevInfoData) {
      e.preventDefault()
      setIsDevInfoDialogOpen(true)
    }
  }

  const handleFeedback = async (type: 'up' | 'down', comment?: string) => {
    // Optimistic update
    setFeedbackStatus(type)

    if (type === 'down' && !comment && !isFeedbackDialogOpen) {
      setIsFeedbackDialogOpen(true)
      return
    }

    setIsSubmittingFeedback(true)
    try {
      const result = await submitFeedback({
        question: 'User Query', // Ideally pass this prop or context, for now we log the response ID or just the fact it happened. 
        // Note: We might need the actual user question if possible, but message.id might help trace it.
        response: message.content,
        type,
        comment,
        messageId: message.id,
      })

      if (result.success) {
        if (comment) {
          toast.success('Feedback submitted', { description: 'Thank you for your input!' })
          setIsFeedbackDialogOpen(false)
          setFeedbackComment('')
        }
      } else {
        toast.error('Failed to submit feedback')
      }
    } catch (err) {
      console.error(err)
      toast.error('Something went wrong')
    } finally {
      setIsSubmittingFeedback(false)
    }
  }

  return (
    <div className={`flex gap-4 ${isUser ? 'flex-row-reverse' : 'flex-row'}`}>
      {/* Avatar - Clickable with Shift for dev info */}
      <div
        onClick={handleAvatarClick}
        className={hasDevInfoData ? 'cursor-pointer hover:opacity-80 transition-opacity' : ''}
        title={hasDevInfoData ? 'Hold Shift and click to view dev info' : ''}
      >
        <Avatar className={`w-8 h-8 ${isUser
          ? 'bg-primary'
          : isSystem
            ? 'bg-destructive'
            : 'bg-gradient-to-br from-primary/20 via-primary/10 to-transparent border border-primary/30 shadow-sm'
          }`}>
          <AvatarFallback className={`text-sm font-medium ${isUser
            ? 'bg-primary text-primary-foreground'
            : isSystem
              ? 'bg-destructive text-destructive-foreground'
              : 'bg-transparent'
            }`}>
            {isUser || isSystem ? (
              getInitials()
            ) : (
              <div className="relative flex items-center justify-center w-full h-full">
                <Sparkles className="h-4 w-4 text-primary" strokeWidth={2.5} />
                <motion.div
                  className="absolute inset-0 flex items-center justify-center"
                  animate={{
                    scale: [1, 1.1, 1],
                    opacity: [0.3, 0.6, 0.3],
                  }}
                  transition={{
                    duration: 2,
                    repeat: Infinity,
                    ease: "easeInOut"
                  }}
                >
                  <Sparkles className="h-5 w-5 text-primary/30" strokeWidth={1.5} />
                </motion.div>
              </div>
            )}
          </AvatarFallback>
        </Avatar>
      </div>

      {/* Message Content */}
      <div className={`flex-1 ${isUser ? 'max-w-[60%] ml-auto text-left' : 'max-w-3xl text-left'}`} ref={messageRef}>
        <div className={`${isUser ? 'block w-fit ml-auto' : 'inline-block'} rounded-2xl px-4 py-3 text-sm leading-relaxed relative ${isUser
          ? 'bg-primary text-primary-foreground'
          : isSystem
            ? 'bg-destructive/10 text-destructive border border-destructive/20'
            : 'bg-transparent text-foreground p-0' // Transparent for assistant (NotebookLM style)
          }`}>
          {message.isThinking ? (
            <div className="py-2">
              <AnimatedLoadingText
                steps={[
                  ...(message.internetEnabled ? ["Searching the web..."] : []),
                  "Analysing information...",
                  "Drafting response...",
                  "Crafting answer...",
                  "Refining details...",
                  "Finalizing..."
                ]}
                interval={1800}
                className="text-sm text-muted-foreground"
              />
            </div>
          ) : (
            <div className="break-words">
              <MarkdownRenderer
                content={cleanContent || message.content || 'Processing your query...'}
                className="text-sm"
              />
            </div>
          )}

          {/* Copy to Page Button - Only for assistant messages */}
          {message.role === 'assistant' && !message.isThinking && onCopyToDraft && (
            <div className="mt-3 flex items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={handleCopyFullMessage}
                className="h-7 px-3 text-xs gap-1.5"
                aria-label="Copy entire message to draft document"
              >
                {copied ? (
                  <>
                    <Check className="h-3 w-3" />
                    Copied
                  </>
                ) : (
                  <>
                    <Copy className="h-3 w-3" />
                    Copy to page
                  </>
                )}
              </Button>
            </div>
          )}

          {/* Selection Tooltip */}
          {showSelectionTooltip && selectedText && (
            <div
              ref={tooltipRef}
              className="fixed z-50 bg-background border border-border rounded-lg shadow-lg p-2"
              style={{ pointerEvents: 'auto' }}
            >
              <Button
                variant="default"
                size="sm"
                onClick={handleCopySelection}
                className="h-7 px-3 text-xs gap-1.5"
                aria-label="Copy selected text to draft document"
              >
                <Copy className="h-3 w-3" />
                Copy selection
              </Button>
            </div>
          )}

          {/* Attached Files Display (User Message) - Fixed styling */}
          {message.role === 'user' && message.attachedFiles && message.attachedFiles.length > 0 && (
            <div className="mt-3 space-y-2">
              <div className="text-[10px] font-medium opacity-70 uppercase tracking-wider mb-1">Attached Context</div>
              {message.attachedFiles.map((file, idx) => (
                <div key={idx} className="flex items-center gap-2 bg-white/10 p-2 rounded-lg text-xs backdrop-blur-sm border border-white/10">
                  <div className="p-1.5 bg-white/20 rounded-md">
                    <FileText className="h-3.5 w-3.5" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="font-medium truncate max-w-[200px]">{file.name}</div>
                    <div className="opacity-70 text-[10px]">Processed</div>
                  </div>
                  <div className="text-primary">
                    <CheckCircle2 className="h-4 w-4" />
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Show placeholder warning for assistant messages */}
          {message.role === 'assistant' && message.content.includes('N/A') && (
            <div className="mt-3 p-2 bg-amber-500/10 border border-amber-500/20 rounded-lg text-xs text-amber-400">
              <Badge variant="outline" className="text-amber-400 border-amber-500/20 bg-amber-500/10">
                ⚠️ Placeholder Data
              </Badge>
              <p className="mt-1">System not yet connected to vector databases or LLM services.</p>
            </div>
          )}

          {/* Citations Section - NotebookLM Style with Collapsible */}
          {message.role === 'assistant' && Array.isArray(message.response?.citations) && message.response.citations.length > 0 && (
            <div className="mt-6 pt-4 border-t border-border/40">
              <Collapsible open={isSourcesOpen} onOpenChange={setIsSourcesOpen}>
                <div className="flex items-center justify-between mb-3">
                  <CollapsibleTrigger asChild>
                    <button className="flex items-center text-left hover:opacity-80 transition-opacity group">
                      <div className="h-4 w-1 bg-primary/60 rounded-full mr-2" />
                      <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Sources</span>
                      <span className="text-xs text-muted-foreground ml-1">({message.response.citations.length})</span>
                      <div className="ml-2">
                        {isSourcesOpen ? (
                          <ChevronDown className="h-3 w-3 text-muted-foreground group-hover:text-foreground transition-colors" />
                        ) : (
                          <ChevronRight className="h-3 w-3 text-muted-foreground group-hover:text-foreground transition-colors" />
                        )}
                      </div>
                    </button>
                  </CollapsibleTrigger>

                  {/* Feedback Buttons inline with Sources */}
                  <div className="flex items-center gap-1">
                    <Button
                      variant="ghost"
                      size="icon"
                      className={`h-6 w-6 ${feedbackStatus === 'up' ? 'text-primary' : 'text-muted-foreground hover:text-primary'}`}
                      onClick={() => handleFeedback('up')}
                      disabled={isSubmittingFeedback}
                    >
                      <ThumbsUp className="h-3.5 w-3.5" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="icon"
                      className={`h-6 w-6 ${feedbackStatus === 'down' ? 'text-red-500' : 'text-muted-foreground hover:text-red-500'}`}
                      onClick={() => handleFeedback('down')}
                      disabled={isSubmittingFeedback}
                    >
                      <ThumbsDown className="h-3.5 w-3.5" />
                    </Button>
                  </div>
                </div>

                <CollapsibleContent>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                    {message.response.citations.map((citation: any, index: number) => {
                      const hasUrl = !!citation.url
                      const isWebSource = hasUrl || citation.vertical === 'internet'
                      const displayName = citation.filename || citation.source || citation.docId
                      const pageInfo = citation.page ? `Page ${citation.page}` : ''
                      const isLoading = loadingCitationIndex === index

                      const CardContent = () => (
                        <div className="flex items-start gap-3">
                          <div className={`flex-shrink-0 flex items-center justify-center w-6 h-6 rounded-full text-[10px] font-bold ${isWebSource
                            ? 'bg-blue-500/20 text-blue-600 dark:text-blue-400'
                            : 'bg-primary/10 text-primary'
                            }`}>
                            {isWebSource ? (
                              <Globe className="h-3.5 w-3.5" />
                            ) : (
                              index + 1
                            )}
                          </div>
                          <div className="min-w-0 flex-1">
                            <div className="text-xs font-medium text-foreground truncate pr-2" title={displayName}>
                              {displayName}
                            </div>
                            <div className="text-[11px] text-muted-foreground mt-0.5 line-clamp-2 leading-relaxed group-hover:text-foreground/80 transition-colors">
                              {pageInfo && <span className="font-mono mr-1">[{pageInfo}]</span>}
                              {citation.span}
                            </div>
                          </div>
                          {isLoading && (
                            <div className="flex-shrink-0">
                              <Loader2 className="h-4 w-4 text-primary animate-spin" />
                            </div>
                          )}
                        </div>
                      )

                      // Handle citation click - temporarily skip snippet location
                      const handleCitationClick = async () => {
                        if (hasUrl) return // Allow default behavior for web links

                        try {
                          setLoadingCitationIndex(index)
                          console.log('Opening PDF for citation:', citation)
                          console.log('Citation fields:', {
                            docId: citation.docId,
                            source: citation.source,
                            filename: citation.filename,
                            url: citation.url
                          })

                          // Temporarily skip snippet location, just open the PDF
                          // Pass citation.source as sourceHint (4th argument)
                          await openPdf(
                            citation.filename || citation.docId,
                            citation.source || displayName,
                            1, // pageNumber
                            citation.source, // sourceHint
                            citation.filename // filename hint for fallbacks
                          )
                        } catch (error) {
                          console.error('Failed to open PDF:', error)
                          alert(`Failed to open PDF: ${error instanceof Error ? error.message : 'Unknown error'}\n\nThe PDF file may not exist in the storage bucket.`)
                        } finally {
                          setLoadingCitationIndex(null)
                        }
                      }

                      return hasUrl ? (
                        <a
                          key={index}
                          href={citation.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className={`group relative p-3 rounded-xl border transition-all duration-200 cursor-pointer block ${isWebSource
                            ? 'bg-blue-50/50 dark:bg-blue-950/20 border-blue-200/50 dark:border-blue-800/50 hover:bg-blue-100/50 dark:hover:bg-blue-900/30 hover:border-blue-300/50 dark:hover:border-blue-700/50'
                            : 'bg-card/50 hover:bg-card border-border/50 hover:border-primary/20'
                            }`}
                        >
                          <CardContent />
                        </a>
                      ) : (
                        <div
                          key={index}
                          onClick={handleCitationClick}
                          className={`group relative p-3 rounded-xl border transition-all duration-200 cursor-pointer hover:shadow-md hover:scale-[1.02] active:scale-[0.98] ${isLoading ? 'opacity-75' : ''} ${isWebSource
                            ? 'bg-blue-50/50 dark:bg-blue-950/20 border-blue-200/50 dark:border-blue-800/50 hover:bg-blue-100/50 dark:hover:bg-blue-900/30 hover:border-blue-300/50 dark:hover:border-blue-700/50'
                            : 'bg-card/50 hover:bg-card border-border/50 hover:border-primary/20'
                            }`}
                        >
                          <CardContent />
                        </div>
                      )
                    })}
                  </div>
                </CollapsibleContent>
              </Collapsible>
            </div>
          )}


          {/* Feedback UI - Fallback when no citations exist */}
          {message.role === 'assistant' && !message.isThinking && (!message.response?.citations || message.response.citations.length === 0) && (
            <div className="mt-4 pt-2 border-t border-border/40 flex justify-end items-center gap-1">
              <Button
                variant="ghost"
                size="icon"
                className={`h-6 w-6 ${feedbackStatus === 'up' ? 'text-primary' : 'text-muted-foreground hover:text-primary'}`}
                onClick={() => handleFeedback('up')}
                disabled={isSubmittingFeedback}
              >
                <ThumbsUp className="h-3.5 w-3.5" />
              </Button>
              <Button
                variant="ghost"
                size="icon"
                className={`h-6 w-6 ${feedbackStatus === 'down' ? 'text-red-500' : 'text-muted-foreground hover:text-red-500'}`}
                onClick={() => handleFeedback('down')}
                disabled={isSubmittingFeedback}
              >
                <ThumbsDown className="h-3.5 w-3.5" />
              </Button>
            </div>
          )}

          {/* Feedback Dialog (Always rendered at root of message but conditionally open) */}
          <Dialog open={isFeedbackDialogOpen} onOpenChange={setIsFeedbackDialogOpen}>
            <DialogContent className="sm:max-w-[425px]">
              <DialogHeader>
                <DialogTitle>Provide Additional Feedback</DialogTitle>
                <DialogDescription>
                  Help us understand what went wrong. Your feedback is valuable.
                </DialogDescription>
              </DialogHeader>
              <div className="grid gap-4 py-4">
                <Textarea
                  placeholder="What could be improved?"
                  value={feedbackComment}
                  onChange={(e) => setFeedbackComment(e.target.value)}
                  rows={4}
                />
              </div>
              <DialogFooter>
                <Button
                  type="submit"
                  onClick={() => handleFeedback('down', feedbackComment)}
                  disabled={isSubmittingFeedback}
                >
                  {isSubmittingFeedback ? 'Submitting...' : 'Submit Feedback'}
                </Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>

          {/* Dev info removed from visible view - accessible via Shift+Click on avatar */}
        </div>

        {/* Timestamp - Only show for user messages */}
        {isUser && (
          <div className="text-xs text-muted-foreground mt-2 text-right">
            {formatTime(message.timestamp)}
          </div>
        )}
      </div>

      {/* Dev Info Dialog - Accessible via Shift+Click on avatar */}
      {hasDevInfoData && (
        <Dialog open={isDevInfoDialogOpen} onOpenChange={setIsDevInfoDialogOpen}>
          <DialogContent className="max-w-3xl max-h-[80vh] overflow-y-auto">
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2">
                <Brain className={`h-5 w-5 ${message.isThinking ? 'animate-pulse text-primary' : ''}`} />
                {message.isThinking ? (
                  <span className="text-primary animate-pulse">
                    {message.currentStep || "Thinking..."}
                  </span>
                ) : (
                  <span>Dev Info</span>
                )}
              </DialogTitle>
            </DialogHeader>
            <div className="bg-muted/50 border border-border/50 rounded-lg p-4 text-xs space-y-3 mt-4">
              {/* Active Processing State */}
              {message.isThinking && (
                <div className="space-y-2 mb-3">
                  <div className="flex items-center gap-2 text-primary">
                    <div className="h-1.5 w-1.5 bg-primary rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                    <div className="h-1.5 w-1.5 bg-primary rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                    <div className="h-1.5 w-1.5 bg-primary rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                  </div>
                </div>
              )}
              {/* Show extracted dev info content or cloud model dev info */}
              {(devInfoContent || cloudDevInfoContent) && (
                <div>
                  <span className="font-medium text-foreground">Reasoning:</span>
                  <div className="ml-2 mt-1 text-xs text-muted-foreground">
                    <MarkdownRenderer
                      content={devInfoContent || cloudDevInfoContent || ''}
                      className="text-xs"
                    />
                  </div>
                </div>
              )}

              {/* Show processing trace data */}
              {message.response?.processing_trace && (
                <>
                  {/* Trace Steps List (ChatGPT Style) */}
                  {message.response.processing_trace.steps && message.response.processing_trace.steps.length > 0 && (
                    <div className="mb-3 pb-3 border-b border-border/50">
                      <span className="font-medium text-foreground block mb-1.5">Processing Steps:</span>
                      <div className="space-y-1.5">
                        {message.response.processing_trace.steps.map((step: string, index: number) => (
                          <div key={index} className="flex items-start gap-2 text-muted-foreground">
                            <div className="mt-0.5 min-w-[14px]">
                              <div className="flex h-3.5 w-3.5 items-center justify-center rounded-full bg-primary/15">
                                <div className="-mt-0.5 h-1.5 w-2.5 -rotate-45 border-b-[1.5px] border-l-[1.5px] border-primary" />
                              </div>
                            </div>
                            <span>{step}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {message.response.processing_trace.language && (
                    <div>
                      <span className="font-medium text-foreground">Language:</span>
                      <span className="ml-2 text-muted-foreground">{message.response.processing_trace.language}</span>
                    </div>
                  )}

                  {message.response.processing_trace.retrieval && (
                    <div>
                      <span className="font-medium text-foreground">Retrieval:</span>
                      <div className="ml-2 mt-1 space-y-1">
                        {message.response.processing_trace.retrieval.dense && message.response.processing_trace.retrieval.dense.length > 0 && (
                          <div>
                            <span className="text-muted-foreground">Dense:</span>
                            <div className="ml-2 text-xs text-muted-foreground">
                              {message.response.processing_trace.retrieval.dense.map((item: string, index: number) => (
                                <div key={index} className="truncate">• {item}</div>
                              ))}
                            </div>
                          </div>
                        )}
                        {message.response.processing_trace.retrieval.sparse && message.response.processing_trace.retrieval.sparse.length > 0 && (
                          <div>
                            <span className="text-muted-foreground">Sparse:</span>
                            <div className="ml-2 text-xs text-muted-foreground">
                              {message.response.processing_trace.retrieval.sparse.map((item: string, index: number) => (
                                <div key={index} className="truncate">• {item}</div>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                    </div>
                  )}

                  {message.response.processing_trace.kg_traversal && (
                    <div>
                      <span className="font-medium text-foreground">Knowledge Graph:</span>
                      <div className="ml-2 text-xs text-muted-foreground">
                        {message.response.processing_trace.kg_traversal}
                      </div>
                    </div>
                  )}

                  {message.response.processing_trace.controller_iterations && (
                    <div>
                      <span className="font-medium text-foreground">Controller Iterations:</span>
                      <span className="ml-2 text-muted-foreground">{message.response.processing_trace.controller_iterations}</span>
                    </div>
                  )}
                </>
              )}

              {Array.isArray(message.response?.citations) && message.response.citations.length > 0 && (
                <div>
                  <span className="font-medium text-foreground">Citations:</span>
                  <div className="ml-2 mt-1 space-y-1 text-muted-foreground">
                    {message.response.citations.map((c: any, i: number) => (
                      <div key={i} className="truncate">• Doc {c.docId} p.{c.page} — {c.span}</div>
                    ))}
                  </div>
                </div>
              )}

              {message.response?.risk_assessment && (
                <div>
                  <span className="font-medium text-foreground">Risk assessment:</span>
                  <div className="ml-2 text-xs text-muted-foreground whitespace-pre-wrap">
                    {message.response.risk_assessment}
                  </div>
                </div>
              )}
            </div>
          </DialogContent>
        </Dialog>
      )}

      {/* PDF Viewer Portal */}
      {pdfState.isOpen && pdfState.pdfUrl && (
        <PdfViewer
          fileUrl={pdfState.pdfUrl || ''}
          initialPage={pdfState.pageNumber || 1}
          highlightText={pdfState.highlightText || undefined}
          title={pdfState.title || undefined}
          onClose={closePdf}
        />
      )}


    </div>
  )
}
