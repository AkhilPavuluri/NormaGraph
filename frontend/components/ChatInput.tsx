'use client'

import { useState, useRef, useEffect } from 'react'
import { Button } from '@/components/ui/button'
import { Send, Plus, Loader2, Zap, Brain, Lightbulb, Paperclip, X, Globe, FileText, FileEdit, Mic, MicOff } from 'lucide-react'
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip'
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
  DropdownMenuSeparator
} from '@/components/ui/dropdown-menu'
import { useSpeechRecognition } from '@/hooks/useSpeechRecognition'

interface ChatInputProps {
  onSendMessage: (message: string, files?: File[]) => void
  isLoading: boolean
  placeholder?: string
  onThinkingModeChange?: (mode: 'qa' | 'deep_think' | 'brainstorm') => void
  onInternetToggle?: (enabled: boolean) => void
  onDraftToggle?: (enabled: boolean) => void
  isDraftEnabled?: boolean
  /** Optional draft strip (ChatBot passes for active draft context) */
  activeDraftTitle?: string
  isDraftNew?: boolean
}

interface ModeButtonProps {
  mode: 'qa' | 'deep_think' | 'brainstorm'
  icon: React.ReactNode
  isActive: boolean
  onClick: () => void
  title: string
  description: string
  additionalInfo: string
}

function ModeButton({ mode, icon, isActive, onClick, title, description, additionalInfo }: ModeButtonProps) {
  const [isHovered, setIsHovered] = useState(false)

  const getModeDisplayText = (mode: 'qa' | 'deep_think' | 'brainstorm') => {
    switch (mode) {
      case 'qa': return 'Q&A'
      case 'deep_think': return 'Deep Think'
      case 'brainstorm': return 'Brainstorm'
      default: return 'Q&A'
    }
  }

  return (
    <Popover open={isHovered} onOpenChange={setIsHovered}>
      <PopoverTrigger asChild>
        <Button
          variant="ghost"
          onClick={onClick}
          onMouseEnter={() => setIsHovered(true)}
          onMouseLeave={() => setIsHovered(false)}
          className={`h-8 transition-all flex items-center ${isActive
            ? 'bg-primary text-primary-foreground border border-primary/50 px-2 gap-1.5'
            : 'text-muted-foreground hover:text-foreground hover:bg-accent w-8 p-0'
            }`}
        >
          {icon}
          {isActive && (
            <span className="text-xs font-medium whitespace-nowrap">{getModeDisplayText(mode)}</span>
          )}
        </Button>
      </PopoverTrigger>
      <PopoverContent
        side="bottom"
        align="start"
        className="w-64 p-0"
        onMouseEnter={() => setIsHovered(true)}
        onMouseLeave={() => setIsHovered(false)}
      >
        <div className="p-4">
          <h3 className="font-semibold text-sm mb-1">{title}</h3>
          <p className="text-xs text-muted-foreground">{description}</p>
        </div>
        <div className="h-px bg-border" />
        <div className="p-4">
          <p className="text-xs text-muted-foreground">
            {additionalInfo}
          </p>
        </div>
      </PopoverContent>
    </Popover>
  )
}

interface InternetButtonProps {
  isEnabled: boolean
  onClick: () => void
}

function InternetButton({ isEnabled, onClick }: InternetButtonProps) {
  const [isHovered, setIsHovered] = useState(false)

  return (
    <Popover open={isHovered} onOpenChange={setIsHovered}>
      <PopoverTrigger asChild>
        <Button
          variant="ghost"
          onClick={onClick}
          onMouseEnter={() => setIsHovered(true)}
          onMouseLeave={() => setIsHovered(false)}
          className={`h-8 transition-all flex items-center ${isEnabled
            ? 'bg-blue-500/10 text-blue-500 border border-blue-500/30 px-2 gap-1.5'
            : 'text-muted-foreground hover:text-foreground hover:bg-accent w-8 p-0'
            }`}
        >
          <Globe className="h-4 w-4" />
          {isEnabled && (
            <span className="text-xs font-medium whitespace-nowrap">Internet</span>
          )}
        </Button>
      </PopoverTrigger>
      <PopoverContent
        side="bottom"
        align="start"
        className="w-64 p-0"
        onMouseEnter={() => setIsHovered(true)}
        onMouseLeave={() => setIsHovered(false)}
      >
        <div className="p-4">
          <h3 className="font-semibold text-sm mb-1">Internet Search</h3>
          <p className="text-xs text-muted-foreground">
            {isEnabled
              ? 'Internet search is enabled'
              : 'Enable real-time web search for up-to-date information'}
          </p>
        </div>
        <div className="h-px bg-border" />
        <div className="p-4">
          <p className="text-xs text-muted-foreground">
            {isEnabled
              ? 'Your queries will include real-time web search results'
              : 'Click to enable internet search capabilities'}
          </p>
        </div>
      </PopoverContent>
    </Popover>
  )
}

interface DraftButtonProps {
  isEnabled: boolean
  onClick: () => void
}

function DraftButton({ isEnabled, onClick }: DraftButtonProps) {
  return (
    <Button
      variant="ghost"
      onClick={onClick}
      className={`h-8 transition-all flex items-center rounded-full px-2 gap-1.5 ${isEnabled
        ? 'bg-primary text-primary-foreground border border-primary/50'
        : 'bg-muted text-foreground hover:bg-muted/80 border border-transparent'
        }`}
    >
      <FileEdit className="h-4 w-4" />
      <span className="text-xs font-medium whitespace-nowrap">Draft</span>
    </Button>
  )
}

export function ChatInput({
  onSendMessage,
  isLoading,
  placeholder = "Query the Decision Graph — authorities, clauses, rules, relationships…",
  onThinkingModeChange,
  onInternetToggle,
  onDraftToggle,
  isDraftEnabled = false,
}: ChatInputProps) {
  const [message, setMessage] = useState('')
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [thinkingMode, setThinkingMode] = useState<'qa' | 'deep_think' | 'brainstorm'>('qa')
  const [internetEnabled, setInternetEnabled] = useState(false)
  const [uploadedFiles, setUploadedFiles] = useState<File[]>([])
  const { isListening, transcript, interimTranscript, startListening, stopListening, hasRecognition, error, isProcessing } = useSpeechRecognition()
  const messageSnapshot = useRef('')

  // Sync speech transcript with message input
  useEffect(() => {
    if (isListening) {
      const prefix = messageSnapshot.current
      const spacer = (prefix && !prefix.match(/\s$/) && (transcript || interimTranscript)) ? ' ' : ''
      const newValue = prefix + spacer + transcript + interimTranscript
      setMessage(newValue)

      // Auto-resize
      if (textareaRef.current) {
        textareaRef.current.style.height = 'auto'
        textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 200)}px`
      }
    }
  }, [transcript, interimTranscript, isListening])

  const handleMicClick = () => {
    if (isListening) {
      stopListening()
    } else {
      messageSnapshot.current = message
      startListening()
      // Focus textarea to ensure we keep context if needed, though recognition is independent
      textareaRef.current?.focus()
    }
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!message.trim() || isLoading) return

    onSendMessage(message.trim(), uploadedFiles.length > 0 ? uploadedFiles : undefined)
    setMessage('')
    setUploadedFiles([])

    // Reset textarea height
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto'
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit(e)
    }
  }

  const handleInput = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const value = e.target.value
    setMessage(value)

    // Auto-resize textarea
    const textarea = e.target
    textarea.style.height = 'auto'
    textarea.style.height = `${Math.min(textarea.scrollHeight, 200)}px`
  }

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || [])

    // Validate file count
    if (uploadedFiles.length + files.length > 3) {
      alert('Maximum 3 files allowed')
      return
    }

    // Validate file types
    const validTypes = ['.pdf', '.txt', '.docx']
    const invalidFiles = files.filter(file => {
      const ext = '.' + file.name.split('.').pop()?.toLowerCase()
      return !validTypes.includes(ext)
    })

    if (invalidFiles.length > 0) {
      alert(`Unsupported file types. Only PDF, TXT, and DOCX files are allowed.`)
      return
    }

    // Validate file sizes (10MB max)
    const oversizedFiles = files.filter(file => file.size > 10 * 1024 * 1024)
    if (oversizedFiles.length > 0) {
      alert(`File too large. Maximum size is 10MB per file.`)
      return
    }

    setUploadedFiles(prev => [...prev, ...files])

    // Reset file input
    if (fileInputRef.current) {
      fileInputRef.current.value = ''
    }
  }

  const removeFile = (index: number) => {
    setUploadedFiles(prev => prev.filter((_, i) => i !== index))
  }

  const handleFileButtonClick = () => {
    fileInputRef.current?.click()
  }

  useEffect(() => {
    // Focus the input when component mounts
    if (textareaRef.current) {
      textareaRef.current.focus()
    }
  }, [])

  const handleThinkingModeChange = (value: 'qa' | 'deep_think' | 'brainstorm') => {
    setThinkingMode(value)
    onThinkingModeChange?.(value)
  }

  const handleInternetToggle = () => {
    const newValue = !internetEnabled
    setInternetEnabled(newValue)
    onInternetToggle?.(newValue)
  }

  const getModeIcon = (mode: 'qa' | 'deep_think' | 'brainstorm') => {
    switch (mode) {
      case 'qa': return <Lightbulb className="h-3 w-3" />
      case 'deep_think': return <Brain className="h-3 w-3" />
      case 'brainstorm': return <Zap className="h-3 w-3" />
      default: return <Lightbulb className="h-3 w-3" />
    }
  }

  const getModeDisplayText = (mode: 'qa' | 'deep_think' | 'brainstorm') => {
    switch (mode) {
      case 'qa': return 'Q&A'
      case 'deep_think': return 'Deep Think'
      case 'brainstorm': return 'Brainstorm'
      default: return 'Q&A'
    }
  }

  const getModeDescription = (mode: 'qa' | 'deep_think' | 'brainstorm') => {
    switch (mode) {
      case 'qa': return 'Fast answers to everyday questions'
      case 'deep_think': return 'Step-by-step analysis and reasoning'
      case 'brainstorm': return 'Creative and innovative ideas'
      default: return 'Fast answers to everyday questions'
    }
  }

  const getFileIcon = (filename: string) => {
    const ext = filename.split('.').pop()?.toLowerCase()
    return <FileText className="h-3.5 w-3.5" />
  }

  return (
    <TooltipProvider>
      <div className="relative">

        {/* File Chips */}
        {uploadedFiles.length > 0 && (
          <div className="mb-3 flex flex-wrap gap-2">
            {uploadedFiles.map((file, index) => (
              <div
                key={index}
                className="flex items-center gap-2 px-3 py-1.5 bg-blue-500/10 text-blue-600 rounded-lg border border-blue-500/30 text-xs"
              >
                {getFileIcon(file.name)}
                <span className="max-w-[150px] truncate">{file.name}</span>
                <button
                  onClick={() => removeFile(index)}
                  className="hover:bg-blue-500/20 rounded-full p-0.5 transition-colors"
                >
                  <X className="h-3 w-3" />
                </button>
              </div>
            ))}
          </div>
        )}

        {/* Main Input Container */}
        <div className="flex flex-col gap-2 bg-background border border-border rounded-2xl p-3 shadow-lg hover:border-border/80 transition-colors">
          {/* Hidden file input */}
          <input
            ref={fileInputRef}
            type="file"
            multiple
            accept=".pdf,.txt,.docx"
            onChange={handleFileSelect}
            className="hidden"
          />

          {/* Row 1: Text Input Area */}
          <div className="flex items-center gap-2">
            <div className="flex-1 relative min-w-0">
              <textarea
                id="chat-message-input"
                name="message"
                ref={textareaRef}
                value={message}
                onChange={handleInput}
                onKeyDown={handleKeyDown}
                placeholder={placeholder}
                disabled={isLoading}
                className="w-full bg-transparent border-0 text-foreground placeholder:text-muted-foreground resize-none focus:outline-none text-base leading-6"
                rows={1}
                style={{ minHeight: '24px', maxHeight: '200px' }}
                aria-label="Chat message input"
              />
            </div>
          </div>

          {/* Row 2: Mode Selector Icons and Action Buttons */}
          <div className="flex items-center justify-between gap-2">
            {/* Mode Selector Icons - Left side */}
            <div className="flex items-center gap-1 bg-muted/50 rounded-lg p-1 flex-shrink-0">
              <ModeButton
                mode="qa"
                icon={<Lightbulb className="h-4 w-4" />}
                isActive={thinkingMode === 'qa'}
                onClick={() => handleThinkingModeChange('qa')}
                title="Q&A"
                description={getModeDescription('qa')}
                additionalInfo="Quick responses for straightforward questions"
              />
              <ModeButton
                mode="deep_think"
                icon={<Brain className="h-4 w-4" />}
                isActive={thinkingMode === 'deep_think'}
                onClick={() => handleThinkingModeChange('deep_think')}
                title="Deep Think"
                description={getModeDescription('deep_think')}
                additionalInfo="Comprehensive analysis with detailed reasoning"
              />
              <ModeButton
                mode="brainstorm"
                icon={<Zap className="h-4 w-4" />}
                isActive={thinkingMode === 'brainstorm'}
                onClick={() => handleThinkingModeChange('brainstorm')}
                title="Brainstorm"
                description={getModeDescription('brainstorm')}
                additionalInfo="Generate creative solutions and innovative approaches"
              />
            </div>

            {/* Action Buttons - Right side */}
            <div className="flex items-center gap-1 flex-shrink-0">
              {/* Draft Button */}
              <DraftButton
                isEnabled={isDraftEnabled}
                onClick={() => onDraftToggle?.(!isDraftEnabled)}
              />

              {/* Internet Toggle */}
              <InternetButton
                isEnabled={internetEnabled}
                onClick={handleInternetToggle}
              />

              {/* Speech to Text Button */}
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={handleMicClick}
                    disabled={!hasRecognition || isProcessing}
                    className={`h-8 w-8 transition-all duration-200 ${isListening
                        ? 'text-red-500 bg-red-500/10 border border-red-500/20 hover:bg-red-500/20 animate-pulse'
                        : isProcessing
                          ? 'text-blue-500 animate-spin bg-blue-500/10'
                          : error
                            ? 'text-red-500/80 hover:text-red-500'
                            : !hasRecognition
                              ? 'text-muted-foreground/30 cursor-not-allowed'
                              : 'text-muted-foreground hover:text-foreground'
                      }`}
                  >
                    {isProcessing ? (
                      <Loader2 className="h-4 w-4" />
                    ) : isListening ? (
                      <MicOff className="h-4 w-4" />
                    ) : (
                      <Mic className="h-4 w-4" />
                    )}
                  </Button>
                </TooltipTrigger>
                <TooltipContent>
                  {!hasRecognition ? (
                    <p className="text-red-400">Speech recognition not supported in this browser</p>
                  ) : error === 'network' ? (
                    <p className="text-red-400">Network error - check connection</p>
                  ) : isProcessing ? (
                    <p>Transcribing audio...</p>
                  ) : error ? (
                    <p className="text-red-400">Error: {error}</p>
                  ) : (
                    <p>{isListening ? 'Stop recording' : 'Voice input'}</p>
                  )}
                </TooltipContent>
              </Tooltip>

              {/* File Upload Button */}
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={handleFileButtonClick}
                    className="h-8 w-8 text-muted-foreground hover:text-foreground"
                  >
                    <Paperclip className="h-4 w-4" />
                  </Button>
                </TooltipTrigger>
                <TooltipContent>
                  <p>Attach files</p>
                </TooltipContent>
              </Tooltip>

              {/* Send Button */}
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button
                    onClick={handleSubmit}
                    disabled={isLoading || !message.trim()}
                    className="h-8 w-8 bg-primary hover:bg-primary/90 disabled:bg-muted disabled:text-muted-foreground rounded-lg transition-colors"
                    size="icon"
                  >
                    {isLoading ? (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    ) : (
                      <Send className="h-4 w-4" />
                    )}
                  </Button>
                </TooltipTrigger>
                <TooltipContent>
                  <p>{isLoading ? 'Sending...' : 'Send message'}</p>
                </TooltipContent>
              </Tooltip>
            </div>
          </div>
        </div>
      </div>
    </TooltipProvider>
  )
}