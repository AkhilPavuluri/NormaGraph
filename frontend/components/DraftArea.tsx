'use client'

import { useState, useEffect, useRef } from 'react'
import { FileEdit, Plus, Trash2, X } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Draft } from '@/hooks/useLocalChatStore'
import { MarkdownRenderer } from '@/components/MarkdownRenderer'
import TurndownService from 'turndown'
import { createRoot, Root } from 'react-dom/client'

interface DraftAreaProps {
  drafts: Draft[]
  activeDraftId: string | null
  onContentChange: (draftId: string, content: string) => void
  onCreateDraft: () => void
  onSetActiveDraft: (draftId: string) => void
  onRenameDraft: (draftId: string, newTitle: string) => void
  onDeleteDraft: (draftId: string) => void
}

// Initialize Turndown service for HTML to Markdown conversion
const turndownService = new TurndownService({
  headingStyle: 'atx',
  codeBlockStyle: 'fenced',
  bulletListMarker: '-',
  emDelimiter: '*',
  strongDelimiter: '**',
})

export function DraftArea({
  drafts,
  activeDraftId,
  onContentChange,
  onCreateDraft,
  onSetActiveDraft,
  onRenameDraft,
  onDeleteDraft,
}: DraftAreaProps) {
  const editorRef = useRef<HTMLDivElement>(null)
  const renderContainerRef = useRef<HTMLDivElement | null>(null)
  const rootRef = useRef<Root | null>(null)
  const isMountedRef = useRef(true)
  const timeoutRef = useRef<NodeJS.Timeout | null>(null)
  const [hasChanges, setHasChanges] = useState(false)
  const [editingTitleId, setEditingTitleId] = useState<string | null>(null)
  const [editingTitleValue, setEditingTitleValue] = useState('')
  const [isRendering, setIsRendering] = useState(false)

  // Get active draft
  const activeDraft = activeDraftId 
    ? drafts.find(d => d.id === activeDraftId) 
    : (drafts.length > 0 ? drafts[0] : null)
  const activeContent = activeDraft?.content || ''

  // Render markdown to HTML using a hidden container
  const renderMarkdownToHtml = (markdown: string) => {
    // Early return if not mounted, no markdown, or already rendering
    if (!isMountedRef.current || !markdown || isRendering) return

    // Create hidden container if it doesn't exist
    if (!renderContainerRef.current) {
      renderContainerRef.current = document.createElement('div')
      renderContainerRef.current.style.position = 'absolute'
      renderContainerRef.current.style.visibility = 'hidden'
      renderContainerRef.current.style.pointerEvents = 'none'
      renderContainerRef.current.style.top = '-9999px'
      document.body.appendChild(renderContainerRef.current)
    }

    // Create root if it doesn't exist
    // Note: Once a root is unmounted, it cannot be reused, so we recreate it
    if (!rootRef.current) {
      rootRef.current = createRoot(renderContainerRef.current)
    }

    setIsRendering(true)
    
    try {
      // Render markdown
      rootRef.current.render(<MarkdownRenderer content={markdown} />)
    } catch (error) {
      // If root was unmounted, recreate it and try again
      if (isMountedRef.current && renderContainerRef.current) {
        try {
          rootRef.current = createRoot(renderContainerRef.current)
          rootRef.current.render(<MarkdownRenderer content={markdown} />)
        } catch (retryError) {
          // If retry also fails, cleanup and return
          setIsRendering(false)
          return
        }
      } else {
        setIsRendering(false)
        return
      }
    }

    // Clear any existing timeout
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current)
    }

    // Wait for React to render, then extract HTML
    timeoutRef.current = setTimeout(() => {
      timeoutRef.current = null
      
      // Check if component is still mounted and refs are valid
      if (!isMountedRef.current) {
        setIsRendering(false)
        return
      }
      
      if (renderContainerRef.current && editorRef.current && rootRef.current) {
        const html = renderContainerRef.current.innerHTML
        // Extract content from the prose wrapper
        const tempDiv = document.createElement('div')
        tempDiv.innerHTML = html
        const proseContent = tempDiv.querySelector('.prose')?.innerHTML || html
        
        if (proseContent && editorRef.current.innerHTML !== proseContent) {
          editorRef.current.innerHTML = proseContent
          
          // Restore cursor position at end
          const range = document.createRange()
          const selection = window.getSelection()
          if (selection && editorRef.current) {
            range.selectNodeContents(editorRef.current)
            range.collapse(false)
            selection.removeAllRanges()
            selection.addRange(range)
          }
        }
        setIsRendering(false)
      } else {
        setIsRendering(false)
      }
    }, 10)
  }

  // Auto-save to store (debounced 500ms)
  useEffect(() => {
    if (!hasChanges || !activeDraftId || isRendering) return

    const timer = setTimeout(() => {
      if (editorRef.current) {
        // Convert HTML content back to markdown
        const htmlContent = editorRef.current.innerHTML
        const markdownContent = turndownService.turndown(htmlContent)
        onContentChange(activeDraftId, markdownContent)
        setHasChanges(false)
      }
    }, 500)

    return () => clearTimeout(timer)
  }, [hasChanges, activeDraftId, isRendering, onContentChange])

  // Sync contentEditable with active draft content
  useEffect(() => {
    if (editorRef.current && activeDraft && !isRendering && !hasChanges) {
      const currentHtml = editorRef.current.innerHTML || ''
      const markdownContent = activeDraft.content || ''
      
      // Only update if content actually changed
      if (markdownContent && currentHtml !== markdownContent) {
        renderMarkdownToHtml(markdownContent)
      } else if (!markdownContent && currentHtml) {
        editorRef.current.innerHTML = ''
      }
    }
  }, [activeDraft?.id, activeDraft?.content])

  const handleInput = () => {
    if (!isRendering) {
      setHasChanges(true)
    }
  }

  const handleBlur = () => {
    // Save immediately on blur
    if (editorRef.current && activeDraftId && hasChanges && !isRendering) {
      const htmlContent = editorRef.current.innerHTML
      const markdownContent = turndownService.turndown(htmlContent)
      onContentChange(activeDraftId, markdownContent)
      setHasChanges(false)
    }
  }

  const handleTabClick = (draftId: string) => {
    // Save current draft before switching
    if (editorRef.current && activeDraftId && hasChanges && !isRendering) {
      const htmlContent = editorRef.current.innerHTML
      const markdownContent = turndownService.turndown(htmlContent)
      onContentChange(activeDraftId, markdownContent)
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

  // Handle paste events to preserve plain text
  const handlePaste = (e: React.ClipboardEvent) => {
    e.preventDefault()
    const text = e.clipboardData.getData('text/plain')
    document.execCommand('insertText', false, text)
  }

  // Set mounted flag on mount
  useEffect(() => {
    isMountedRef.current = true
    return () => {
      isMountedRef.current = false
    }
  }, [])

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      isMountedRef.current = false
      
      // Clear any pending timeout
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current)
        timeoutRef.current = null
      }
      
      // Cleanup React root and container
      if (rootRef.current) {
        try {
          rootRef.current.unmount()
        } catch (error) {
          // Root may already be unmounted, ignore error
        }
        rootRef.current = null
      }
      
      if (renderContainerRef.current) {
        if (renderContainerRef.current.parentNode) {
          document.body.removeChild(renderContainerRef.current)
        }
        renderContainerRef.current = null
      }
    }
  }, [])

  if (drafts.length === 0) {
    return (
      <div className="flex flex-col h-full bg-background border-l border-border">
        <div className="flex items-center justify-between p-4 border-b border-border">
          <div className="flex items-center gap-2">
            <FileEdit className="h-4 w-4" />
            <h2 className="font-semibold text-sm">Drafts</h2>
          </div>
          <Button
            variant="ghost"
            size="sm"
            onClick={onCreateDraft}
            className="h-7"
          >
            <Plus className="h-4 w-4" />
          </Button>
        </div>
        <div className="flex-1 flex items-center justify-center p-8">
          <div className="text-center">
            <FileEdit className="h-12 w-12 mx-auto mb-4 text-muted-foreground opacity-50" />
            <p className="text-sm text-muted-foreground mb-4">No drafts yet</p>
            <Button onClick={onCreateDraft} size="sm">
              <Plus className="h-4 w-4 mr-2" />
              Create Draft
            </Button>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="flex flex-col h-[calc(100vh-48px)] bg-background border-l border-border">
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-border">
        <div className="flex items-center gap-2">
          <FileEdit className="h-4 w-4" />
          <h2 className="font-semibold text-sm">Drafts</h2>
        </div>
        <Button
          variant="ghost"
          size="sm"
          onClick={onCreateDraft}
          className="h-7"
        >
          <Plus className="h-4 w-4" />
        </Button>
      </div>

      {/* Draft Tabs */}
      <div className="flex gap-1 p-2 border-b border-border overflow-x-auto">
        {drafts.map((draft) => (
          <div
            key={draft.id}
            className={`group relative flex items-center gap-2 px-3 py-2 rounded-md cursor-pointer transition-colors min-w-0 ${
              activeDraftId === draft.id
                ? 'bg-primary text-primary-foreground'
                : 'hover:bg-muted'
            }`}
            onClick={() => handleTabClick(draft.id)}
            onDoubleClick={(e) => handleTabDoubleClick(e, draft)}
          >
            {editingTitleId === draft.id ? (
              <input
                type="text"
                value={editingTitleValue}
                onChange={(e) => setEditingTitleValue(e.target.value)}
                onBlur={handleTitleBlur}
                onKeyDown={handleTitleKeyDown}
                className="bg-transparent border-none outline-none text-sm font-medium flex-1 min-w-0"
                autoFocus
              />
            ) : (
              <>
                <span className="text-xs font-medium truncate flex-1 min-w-0">
                  {draft.title}
                </span>
                {drafts.length > 1 && (
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-5 w-5 opacity-0 group-hover:opacity-100 transition-opacity"
                    onClick={(e) => {
                      e.stopPropagation()
                      onDeleteDraft(draft.id)
                    }}
                  >
                    <X className="h-3 w-3" />
                  </Button>
                )}
              </>
            )}
          </div>
        ))}
      </div>

      {/* WYSIWYG Editor - Directly editable rendered markdown */}
      <div className="flex-1 flex flex-col overflow-hidden relative">
        <div
          ref={editorRef}
          contentEditable
          onInput={handleInput}
          onBlur={handleBlur}
          onPaste={handlePaste}
          className="flex-1 p-4 overflow-y-auto premium-scrollbar outline-none focus:ring-0 prose prose-sm max-w-none dark:prose-invert"
          style={{
            minHeight: 0,
          }}
          suppressContentEditableWarning
        />
        {!activeContent && !isRendering && (
          <div className="absolute top-4 left-4 text-muted-foreground pointer-events-none text-sm">
            Start writing... (Markdown formatting is supported)
          </div>
        )}
      </div>
    </div>
  )
}
