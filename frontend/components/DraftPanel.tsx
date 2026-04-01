'use client'

import { useState, useEffect, useRef, useCallback } from 'react'
import { X, Trash2, Download, Upload, ChevronDown, Plus, Sparkles, CheckCircle2, Loader2, Undo2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Draft } from '@/hooks/useLocalChatStore'
import { aiEditDraft } from '@/lib/api'

interface DraftPanelProps {
  drafts: Draft[]
  activeDraftId: string | null
  onContentChange: (draftId: string, content: string) => void
  onCreateDraft: () => void
  onSetActiveDraft: (draftId: string) => void
  onRenameDraft: (draftId: string, newTitle: string) => void
  onDeleteDraft: (draftId: string) => void
  onClose: () => void
  isMobile?: boolean
}

export function DraftPanel({ 
  drafts, 
  activeDraftId, 
  onContentChange, 
  onCreateDraft, 
  onSetActiveDraft, 
  onRenameDraft, 
  onDeleteDraft, 
  onClose, 
  isMobile = false 
}: DraftPanelProps) {
  const editorRef = useRef<HTMLDivElement>(null)
  const instructionInputRef = useRef<HTMLInputElement>(null)
  const [hasChanges, setHasChanges] = useState(false)
  const [editingTitleId, setEditingTitleId] = useState<string | null>(null)
  const [editingTitleValue, setEditingTitleValue] = useState('')
  const [aiInstruction, setAiInstruction] = useState('')
  const [isAiEditing, setIsAiEditing] = useState(false)
  const [showSuccess, setShowSuccess] = useState(false)
  const [editHistory, setEditHistory] = useState<string[]>([]) // Undo history

  // Get active draft
  const activeDraft = activeDraftId 
    ? drafts.find(d => d.id === activeDraftId) 
    : (drafts.length > 0 ? drafts[0] : null)
  const activeContent = activeDraft?.content || ''

  // Auto-save to store (debounced 500ms)
  useEffect(() => {
    if (!hasChanges || !activeDraftId) return

    const timer = setTimeout(() => {
      if (editorRef.current) {
        onContentChange(activeDraftId, editorRef.current.innerHTML)
        setHasChanges(false)
      }
    }, 500)

    return () => clearTimeout(timer)
  }, [activeContent, hasChanges, activeDraftId, onContentChange])

  // Sync contentEditable with active draft content
  useEffect(() => {
    if (editorRef.current && activeDraft) {
      const currentText = editorRef.current.innerHTML || ''
      const newText = activeDraft.content || ''
      if (currentText !== newText) {
        editorRef.current.innerHTML = newText
        setHasChanges(false) // Reset changes flag when content is loaded from store
      }
    }
  }, [activeDraft?.id, activeDraft?.content])

  const handleInput = (e: React.FormEvent<HTMLDivElement>) => {
    setHasChanges(true)
  }

  const handleClear = () => {
    if (confirm('Are you sure you want to clear all draft content? This cannot be undone.')) {
      if (editorRef.current && activeDraftId) {
        editorRef.current.innerHTML = ''
        onContentChange(activeDraftId, '')
        setHasChanges(false)
      }
    }
  }

  const handleTabClick = (draftId: string) => {
    // Save current draft before switching
    if (editorRef.current && activeDraftId && hasChanges) {
      onContentChange(activeDraftId, editorRef.current.innerHTML)
      setHasChanges(false)
    }
    onSetActiveDraft(draftId)
  }

  const handleTabDoubleClick = (e: React.MouseEvent, draft: Draft) => {
    e.stopPropagation()
    setEditingTitleId(draft.id)
    setEditingTitleValue(draft.title)
  }

  const handleTitleBlur = () => {
    if (editingTitleId && editingTitleValue.trim()) {
      onRenameDraft(editingTitleId, editingTitleValue.trim())
    }
    setEditingTitleId(null)
    setEditingTitleValue('')
  }

  const handleTitleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      e.preventDefault()
      handleTitleBlur()
    } else if (e.key === 'Escape') {
      setEditingTitleId(null)
      setEditingTitleValue('')
    }
  }

  const handleDeleteDraft = (e: React.MouseEvent, draftId: string) => {
    e.stopPropagation()
    if (drafts.length <= 1) {
      alert('Cannot delete the last draft. At least one draft must exist.')
      return
    }
    if (confirm('Are you sure you want to delete this draft?')) {
      onDeleteDraft(draftId)
    }
  }

  const handleDownload = (format: 'txt' | 'html') => {
    const blob = format === 'txt' 
      ? new Blob([editorRef.current?.textContent || ''], { type: 'text/plain' })
      : new Blob([editorRef.current?.innerHTML || ''], { type: 'text/html' })
    
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `draft-document.${format}`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  }

  // Focus editor on mount
  useEffect(() => {
    if (editorRef.current && !isMobile) {
      // Small delay to ensure panel is fully rendered
      setTimeout(() => {
        editorRef.current?.focus()
      }, 100)
    }
  }, [isMobile])

  // Handle AI edit
  const handleApplyAiEdit = useCallback(async () => {
    if (!activeDraftId || !editorRef.current || !aiInstruction.trim() || isAiEditing) return

    const currentContent = editorRef.current.innerHTML || ''
    if (!currentContent.trim()) {
      alert('Please add some content to the draft before editing.')
      return
    }

    // Save current state to history for undo
    setEditHistory(prev => [...prev, currentContent])

    setIsAiEditing(true)
    setShowSuccess(false)

    try {
      const response = await aiEditDraft({
        draft: currentContent,
        instruction: aiInstruction.trim()
      })

      if (response.editedDraft) {
        // Replace draft content
        editorRef.current.innerHTML = response.editedDraft
        onContentChange(activeDraftId, response.editedDraft)
        setHasChanges(false)
        
        // Show success indicator
        setShowSuccess(true)
        setTimeout(() => setShowSuccess(false), 3000)
        
        // Clear instruction
        setAiInstruction('')
      }
    } catch (error) {
      console.error('Error applying AI edit:', error)
      alert('Failed to apply AI edit. Please try again.')
    } finally {
      setIsAiEditing(false)
    }
  }, [activeDraftId, aiInstruction, isAiEditing, onContentChange])

  // Keyboard shortcut: Ctrl+Enter to apply AI edit
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
        if (instructionInputRef.current && instructionInputRef.current === document.activeElement) {
          e.preventDefault()
          handleApplyAiEdit()
        } else if (editorRef.current && editorRef.current === document.activeElement) {
          e.preventDefault()
          instructionInputRef.current?.focus()
        }
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [handleApplyAiEdit])

  // Handle undo
  const handleUndo = () => {
    if (editHistory.length === 0 || !editorRef.current || !activeDraftId) return

    const previousContent = editHistory[editHistory.length - 1]
    const currentContent = editorRef.current.innerHTML || ''
    
    // Save current state before undoing
    setEditHistory(prev => [...prev.slice(0, -1), currentContent])
    
    editorRef.current.innerHTML = previousContent
    onContentChange(activeDraftId, previousContent)
    setHasChanges(false)
  }

  return (
    <div 
      className={`flex flex-col bg-background ${
        isMobile ? 'fixed inset-0 z-50 h-full' : 'h-full flex-shrink-0'
      }`}
      role="complementary"
      aria-label="Draft Document Panel"
    >
      {/* Fixed Header - ChatGPT Style */}
      <div className="sticky top-0 z-20 flex flex-col border-b border-border bg-background">
        {/* Top Row: Close button, Title, Actions */}
        <div className="flex items-center justify-between px-4 py-3">
          {/* Left: Close button */}
          <Button
            variant="ghost"
            size="icon"
            onClick={onClose}
            className="h-8 w-8 -ml-2"
            aria-label="Close draft panel"
          >
            <X className="h-4 w-4" />
          </Button>

          {/* Center: Auto-save indicator */}
          <div className="flex-1 flex items-center justify-center">
            {hasChanges ? (
              <span className="text-xs text-muted-foreground">Saving...</span>
            ) : (
              <span className="text-xs text-muted-foreground">Saved</span>
            )}
          </div>

          {/* Right: Upload and Download */}
          <div className="flex items-center gap-2">
            <Button
              variant="ghost"
              size="icon"
              className="h-8 w-8"
              aria-label="Upload file"
              title="Upload"
            >
              <Upload className="h-4 w-4" />
            </Button>
            <Button
              variant="ghost"
              size="icon"
              onClick={() => handleDownload('html')}
              className="h-8 w-8"
              aria-label="Download document"
              title="Download"
            >
              <Download className="h-4 w-4" />
            </Button>
          </div>
        </div>

        {/* Draft Tabs Bar */}
        <div className="flex items-center gap-1 px-2 pb-2 overflow-x-auto border-t border-border/50">
          {drafts.map((draft) => (
            <div
              key={draft.id}
              onClick={() => handleTabClick(draft.id)}
              onDoubleClick={(e) => handleTabDoubleClick(e, draft)}
              className={`
                flex items-center gap-2 px-3 py-1.5 rounded-md cursor-pointer transition-colors
                ${activeDraftId === draft.id
                  ? 'bg-primary text-primary-foreground'
                  : 'hover:bg-muted text-muted-foreground hover:text-foreground'
                }
                min-w-fit flex-shrink-0
              `}
            >
              {editingTitleId === draft.id ? (
                <input
                  type="text"
                  value={editingTitleValue}
                  onChange={(e) => setEditingTitleValue(e.target.value)}
                  onBlur={handleTitleBlur}
                  onKeyDown={handleTitleKeyDown}
                  className="bg-transparent border-none outline-none text-sm font-medium w-20"
                  autoFocus
                  onClick={(e) => e.stopPropagation()}
                />
              ) : (
                <>
                  <span className="text-sm font-medium whitespace-nowrap">{draft.title}</span>
                  {drafts.length > 1 && (
                    <button
                      onClick={(e) => handleDeleteDraft(e, draft.id)}
                      className="opacity-70 hover:opacity-100 transition-opacity"
                      aria-label={`Delete ${draft.title}`}
                    >
                      <X className="h-3 w-3" />
                    </button>
                  )}
                </>
              )}
            </div>
          ))}
          <button
            onClick={onCreateDraft}
            className="flex items-center gap-1 px-3 py-1.5 rounded-md hover:bg-muted text-muted-foreground hover:text-foreground transition-colors min-w-fit flex-shrink-0"
            aria-label="Create new draft"
          >
            <Plus className="h-4 w-4" />
            <span className="text-sm font-medium">New Draft</span>
          </button>
        </div>
      </div>

      {/* Editable Content Area - Independent Scroll with Smooth Behavior */}
      <div 
        className="flex-1 flex flex-col overflow-hidden"
        style={{ 
          scrollBehavior: 'smooth',
          height: 'calc(100vh - 48px - 48px)' // Viewport - Site Header - Draft Panel Header
        }}
      >
        <div 
          className="overflow-y-auto bg-muted/20 draft-scrollbar px-4 flex-1"
        >
          <div className="p-6 max-w-4xl mx-auto">
            <div
              ref={editorRef}
              contentEditable
              suppressContentEditableWarning
              onInput={handleInput}
              className="w-full outline-none prose prose-sm dark:prose-invert max-w-none
                         min-h-[200px] bg-background rounded-lg
                         [&_p]:mb-3 [&_p]:leading-relaxed
                         [&_ul]:list-disc [&_ul]:ml-6 [&_ul]:mb-3
                         [&_ol]:list-decimal [&_ol]:ml-6 [&_ol]:mb-3
                         [&_li]:mb-1
                         [&_h1]:text-2xl [&_h1]:font-bold [&_h1]:mb-4 [&_h1]:mt-6
                         [&_h2]:text-xl [&_h2]:font-semibold [&_h2]:mb-3 [&_h2]:mt-5
                         [&_h3]:text-lg [&_h3]:font-medium [&_h3]:mb-2 [&_h3]:mt-4
                         [&_table]:border-collapse [&_table]:border [&_table]:border-border [&_table]:my-4
                         [&_td]:border [&_td]:border-border [&_td]:p-2
                         [&_th]:border [&_th]:border-border [&_th]:p-2 [&_th]:bg-muted [&_th]:font-semibold
                         [&_code]:bg-muted [&_code]:px-1 [&_code]:py-0.5 [&_code]:rounded [&_code]:text-sm
                         [&_pre]:bg-muted [&_pre]:p-4 [&_pre]:rounded-lg [&_pre]:overflow-x-auto [&_pre]:my-4"
              style={{
                wordBreak: 'break-word',
                whiteSpace: 'pre-wrap'
              }}
              aria-label="Draft document editor"
              role="textbox"
              aria-multiline="true"
            />
          </div>
        </div>
      </div>
    </div>
  )
}

