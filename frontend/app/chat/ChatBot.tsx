'use client'

import { useState, useRef, useEffect } from 'react'
import { ChatMessage } from '@/components/ChatMessage'
import { ChatInput } from '@/components/ChatInput'
import { DraftArea } from '@/components/DraftArea'
import { queryAPI, queryWithFiles, type QueryResponse } from '@/lib/api'
import { useChatMessages, useChatStore, Message } from '@/hooks/useChatStore'
import { Draft } from '@/hooks/useLocalChatStore'
import { devLog } from '@/lib/devLog'

interface ChatBotProps {
  selectedModel: string
  activeChatId?: string
  onChatCreated?: (chatId: string) => void
}

type QueryMode = 'qa' | 'deep_think' | 'brainstorm'

const THINKING_STEPS = [
  "Searching the web...",
  "Analysing information...",
  "Drafting response...",
  "Crafting answer...",
  "Refining details...",
  "Finalizing..."
]

export function ChatBot({ selectedModel, activeChatId, onChatCreated }: ChatBotProps) {
  const { messages: firestoreMessages, loadingMessages } = useChatMessages(activeChatId)
  const { createChat, addMessageToChat, updateChatPreview } = useChatStore()
  const newlyCreatedChatsRef = useRef<Set<string>>(new Set())

  // Local state for optimistic updates or just rely on Firestore (it's fast enough usually)
  // But for "Thinking..." state we need local state or a way to show pending message.
  // Let's use a local "pending" state.
  const [isSending, setIsSending] = useState(false)
  const [currentThinkingStep, setCurrentThinkingStep] = useState(THINKING_STEPS[0])

  const [queryMode, setQueryMode] = useState<QueryMode>('qa')
  const [internetEnabled, setInternetEnabled] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  // Draft state - stored per chat
  const [draftsByChat, setDraftsByChat] = useState<Record<string, Draft[]>>({})
  const [activeDraftIdByChat, setActiveDraftIdByChat] = useState<Record<string, string | null>>({})
  const [isDraftAreaVisible, setIsDraftAreaVisible] = useState(false)

  // Get drafts for current chat (uses default key for pre-chat drafts)
  const getDraftsForChat = (chatId: string | undefined): Draft[] => {
    const key = chatId || '__default__'
    return draftsByChat[key] || [{
      id: chatId ? `draft-${chatId}-1` : 'draft-1',
      title: 'Draft 1',
      content: '',
      createdAt: new Date(),
      updatedAt: new Date(),
    }]
  }

  // Get active draft ID for current chat (uses default key for pre-chat drafts)
  const getActiveDraftId = (chatId: string | undefined): string | null => {
    const key = chatId || '__default__'
    const drafts = getDraftsForChat(chatId)
    return activeDraftIdByChat[key] || (drafts.length > 0 ? drafts[0].id : null)
  }

  // Initialize drafts when chat changes or on mount
  useEffect(() => {
    const key = activeChatId || '__default__'
    if (!draftsByChat[key]) {
      const defaultDraft: Draft = {
        id: activeChatId ? `draft-${activeChatId}-1` : 'draft-1',
        title: 'Draft 1',
        content: '',
        createdAt: new Date(),
        updatedAt: new Date(),
      }
      setDraftsByChat(prev => ({
        ...prev,
        [key]: [defaultDraft]
      }))
      setActiveDraftIdByChat(prev => ({
        ...prev,
        [key]: defaultDraft.id
      }))
    }
  }, [activeChatId])

  const drafts = getDraftsForChat(activeChatId)
  const activeDraftId = getActiveDraftId(activeChatId)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [firestoreMessages, isSending, currentThinkingStep])

  // Simulated Thinking Process Effect
  useEffect(() => {
    let interval: NodeJS.Timeout
    if (isSending) {
      let stepIndex = 0
      // If we are just starting, set to initial step
      // If files are present, the first step might be "Analyzing uploaded file..." set by handleSendMessage
      // So only reset if not already set to that.
      if (currentThinkingStep !== "Analyzing uploaded file...") {
        setCurrentThinkingStep(THINKING_STEPS[0])
      }

      interval = setInterval(() => {
        // If we are at the "Analyzing..." step, move to "Understanding..."
        if (currentThinkingStep === "Analyzing uploaded file...") {
          setCurrentThinkingStep(THINKING_STEPS[0])
        } else {
          // Standard cycle
          const currentIndex = THINKING_STEPS.indexOf(currentThinkingStep)
          const nextIndex = (currentIndex + 1) % THINKING_STEPS.length
          setCurrentThinkingStep(THINKING_STEPS[nextIndex])
        }
      }, 2500) // Change step every 2.5 seconds
    }
    return () => clearInterval(interval)
  }, [isSending, currentThinkingStep])

  const handleQueryModeChange = (mode: QueryMode) => {
    setQueryMode(mode)
  }

  const handleInternetToggle = (enabled: boolean) => {
    setInternetEnabled(enabled)
  }

  // Draft handlers - per chat
  const handleDraftContentChange = (draftId: string, content: string, chatId?: string) => {
    // Use provided chatId or fall back to activeChatId, or use a default key for pre-chat drafts
    const targetChatId = chatId || activeChatId || '__default__'
    
    devLog('🔄 Updating draft state:', { draftId, contentLength: content.length, targetChatId, activeChatId })
    setDraftsByChat(prev => {
      const chatDrafts = prev[targetChatId] || []
      devLog('📋 Current drafts in chat:', chatDrafts.map(d => ({ id: d.id, title: d.title })))
      
      // Try to find draft by exact ID match first
      let foundDraft = chatDrafts.find(d => d.id === draftId)
      
      // If not found and draftId is 'draft-1' or starts with 'draft-', try to find the first draft (likely migrated)
      if (!foundDraft && (draftId === 'draft-1' || draftId.startsWith('draft-')) && chatDrafts.length > 0) {
        devLog('⚠️ Draft ID mismatch, using first draft as fallback')
        foundDraft = chatDrafts[0]
      }
      
      if (!foundDraft) {
        console.warn('❌ Draft not found:', { draftId, availableIds: chatDrafts.map(d => d.id) })
        return prev
      }
      
      const updated = chatDrafts.map((d) => 
        d.id === foundDraft!.id ? { ...d, content, updatedAt: new Date() } : d
      )
      
      const updatedDraft = updated.find(d => d.id === foundDraft!.id)
      devLog('✅ Draft state updated, new content for draft:', updatedDraft?.content?.substring(0, 100))
      
      return {
        ...prev,
        [targetChatId]: updated
      }
    })
  }

  const handleCreateDraft = () => {
    const key = activeChatId || '__default__'
    const chatDrafts = getDraftsForChat(activeChatId)
    const newDraft: Draft = {
      id: activeChatId ? `draft-${activeChatId}-${Date.now()}` : `draft-${Date.now()}`,
      title: `Draft ${chatDrafts.length + 1}`,
      content: '',
      createdAt: new Date(),
      updatedAt: new Date(),
    }
    setDraftsByChat(prev => ({
      ...prev,
      [key]: [...(prev[key] || []), newDraft]
    }))
    setActiveDraftIdByChat(prev => ({
      ...prev,
      [key]: newDraft.id
    }))
  }

  const handleSetActiveDraft = (draftId: string) => {
    const key = activeChatId || '__default__'
    setActiveDraftIdByChat(prev => ({
      ...prev,
      [key]: draftId
    }))
  }

  const handleRenameDraft = (draftId: string, newTitle: string) => {
    const key = activeChatId || '__default__'
    setDraftsByChat(prev => {
      const chatDrafts = prev[key] || []
      return {
        ...prev,
        [key]: chatDrafts.map((d) => 
          d.id === draftId ? { ...d, title: newTitle, updatedAt: new Date() } : d
        )
      }
    })
  }

  const handleDeleteDraft = (draftId: string) => {
    const key = activeChatId || '__default__'
    const chatDrafts = getDraftsForChat(activeChatId)
    if (chatDrafts.length <= 1) return
    
    setDraftsByChat(prev => {
      const updated = (prev[key] || []).filter((d) => d.id !== draftId)
      return {
        ...prev,
        [key]: updated
      }
    })
    
    if (activeDraftId === draftId) {
      const remaining = chatDrafts.filter((d) => d.id !== draftId)
      setActiveDraftIdByChat(prev => ({
        ...prev,
        [key]: remaining.length > 0 ? remaining[0].id : null
      }))
    }
  }

  const toggleDraftArea = () => {
    setIsDraftAreaVisible((prev) => !prev)
  }

  // Detect if user wants to edit draft vs send normal message
  const detectDraftIntent = (query: string): boolean => {
    const draftKeywords = [
      'edit draft', 'update draft', 'modify draft', 'change draft',
      'add to draft', 'write in draft', 'draft this', 'put in draft',
      'edit the draft', 'update the draft', 'modify the draft',
      'in the draft', 'to the draft', 'for the draft'
    ]
    const lowerQuery = query.toLowerCase()
    return draftKeywords.some(keyword => lowerQuery.includes(keyword))
  }

  // Prepare draft context for API
  const prepareDraftContext = () => {
    const activeDraft = activeDraftId ? drafts.find(d => d.id === activeDraftId) : null
    return {
      active_draft_id: activeDraftId || null,
      active_draft_content: activeDraft?.content || '',
      all_drafts: drafts.map(d => ({
        id: d.id,
        title: d.title,
        content: d.content
      }))
    }
  }

  // Parse draft editing response and update draft
  const handleDraftEditResponse = (responseContent: string, currentChatId: string, isDraftIntent: boolean = false) => {
    devLog('🔍 Checking for draft edit in response:', responseContent.substring(0, 200))
    
    // Use currentChatId if available, otherwise use activeChatId or default
    const targetChatId = currentChatId || activeChatId || '__default__'
    
    // Look for draft editing markers in response
    // Format: <draft_edit>...</draft_edit> or JSON structure
    const draftEditMatch = responseContent.match(/<draft_edit>(.*?)<\/draft_edit>/s)
    if (draftEditMatch) {
      const editedContent = draftEditMatch[1].trim()
      devLog('✅ Found draft_edit tags, content length:', editedContent.length)
      if (activeDraftId) {
        devLog('📝 Updating draft:', activeDraftId, 'with content length:', editedContent.length, 'for chat:', targetChatId)
        handleDraftContentChange(activeDraftId, editedContent, targetChatId)
        return true
      } else {
        console.warn('⚠️ Missing activeDraftId:', { activeDraftId, targetChatId })
      }
    }
    
    // Also check for JSON format: {"draft_edit": "..."}
    try {
      const jsonMatch = responseContent.match(/\{[\s\S]*"draft_edit"[\s\S]*\}/)
      if (jsonMatch) {
        const parsed = JSON.parse(jsonMatch[0])
        if (parsed.draft_edit && activeDraftId) {
          devLog('✅ Found draft_edit in JSON, updating draft')
          handleDraftContentChange(activeDraftId, parsed.draft_edit, targetChatId)
          return true
        }
      }
    } catch (e) {
      // Not JSON, continue
    }
    
    // If user asked to draft/edit but no tags found, check if entire response should be treated as draft content
    // This handles cases where AI doesn't wrap content in tags
    if (isDraftIntent && activeDraftId) {
      // Check if response looks like draft content (not just a confirmation message)
      const isConfirmationOnly = /^(I've updated|I've edited|Done|Updated)/i.test(responseContent.trim())
      if (!isConfirmationOnly && responseContent.length > 50) {
        devLog('📝 Treating entire response as draft content (no tags found)')
        handleDraftContentChange(activeDraftId, responseContent, targetChatId)
        return true
      }
    }
    
    devLog('❌ No draft edit detected')
    return false
  }

  const handleSendMessage = async (content: string, files?: File[]) => {
    setIsSending(true)

    // Create user message object
    const userMessage: Message = {
      id: Date.now().toString(),
      content,
      role: 'user',
      timestamp: new Date(),
    }

    // Only attach files if they exist and are not empty
    if (files && files.length > 0) {
      userMessage.attachedFiles = files.map(f => ({
        name: f.name,
        size: f.size,
        type: f.type
      }))
    }

    let currentChatId = activeChatId

    try {
      devLog(`ChatBot: Using query mode: ${queryMode}, Internet: ${internetEnabled}, Files attached: ${files?.length || 0}`)

      // If files are present, set initial thinking step
      if (files && files.length > 0) {
        setCurrentThinkingStep("Analyzing uploaded file...")
      }

      // If no active chat, we need to create one
      if (!currentChatId) {
        // Default title until AI/summary updates it
        const newChatId = await createChat(userMessage, "New analysis", '')
        currentChatId = newChatId
        // Mark this chat as newly created so we can generate title after first response
        newlyCreatedChatsRef.current.add(newChatId)
        onChatCreated?.(newChatId)
        
        // Migrate drafts from __default__ to the new chat if they exist
        setDraftsByChat(prev => {
          const defaultDrafts = prev['__default__']
          if (defaultDrafts && defaultDrafts.length > 0) {
            // Get the current active draft ID before migration
            const defaultActiveId = activeDraftIdByChat['__default__'] || (defaultDrafts[0]?.id)
            
            // Migrate drafts to the new chat, updating IDs if needed
            const migratedDrafts = defaultDrafts.map((d, idx) => {
              // If this is the active draft, use the standard pattern, otherwise generate unique ID
              const isActiveDraft = d.id === defaultActiveId
              const newId = isActiveDraft 
                ? `draft-${newChatId}-1` 
                : `draft-${newChatId}-${Date.now()}-${idx}`
              return {
                ...d,
                id: newId
              }
            })
            
            const newState = { ...prev }
            newState[newChatId] = migratedDrafts
            delete newState['__default__']
            
            // Also migrate active draft ID - use the migrated ID of the previously active draft
            if (defaultActiveId) {
              const oldDraftIndex = defaultDrafts.findIndex(d => d.id === defaultActiveId)
              const migratedDraft = migratedDrafts[oldDraftIndex >= 0 ? oldDraftIndex : 0]
              if (migratedDraft) {
                setActiveDraftIdByChat(prevIds => {
                  const newIds = { ...prevIds }
                  newIds[newChatId] = migratedDraft.id
                  delete newIds['__default__']
                  return newIds
                })
              }
            }
            
            return newState
          }
          return prev
        })
      } else {
        await addMessageToChat(currentChatId, userMessage)
      }

      let response: QueryResponse;

      // Build conversation history from previous messages (last 10 messages)
      const conversationHistory = firestoreMessages
        .filter(msg => msg.role === 'user' || msg.role === 'assistant')
        .slice(-10) // Last 10 messages
        .map(msg => ({
          role: msg.role,
          content: msg.content
        }))

      // Prepare draft context - only if draft area is visible
      const draftContext = isDraftAreaVisible ? prepareDraftContext() : undefined
      const isDraftEditIntent = isDraftAreaVisible && detectDraftIntent(content)

      if (files && files.length > 0) {
        // Use file upload endpoint with conversation history and draft context
        response = await queryWithFiles(
          content,
          files,
          queryMode,
          internetEnabled,
          conversationHistory,
          draftContext
        )
      } else {
        // Use standard endpoint with conversation history and draft context
        response = await queryAPI({
          query: content,
          simulate_failure: false,
          mode: queryMode,
          internet_enabled: internetEnabled,
          conversation_history: conversationHistory,
          draft_context: draftContext
        })
      }

      // Fallback if response.answer is empty or undefined
      let responseContent = response.answer || `I received your message "${content}" but couldn't generate a proper response. This might be due to API configuration issues.`

      // Check if response contains draft edit and handle it (only if draft area is visible)
      const wasDraftEdited = isDraftAreaVisible && handleDraftEditResponse(responseContent, currentChatId || '', isDraftEditIntent)
      
      // If draft was edited, remove the draft edit markers from the response for display
      if (wasDraftEdited) {
        // Remove draft_edit tags if present
        const originalContent = responseContent
        responseContent = responseContent.replace(/<draft_edit>.*?<\/draft_edit>/s, '')
        try {
          const jsonMatch = responseContent.match(/\{[\s\S]*"draft_edit"[\s\S]*\}/)
          if (jsonMatch) {
            responseContent = responseContent.replace(jsonMatch[0], '')
          }
        } catch (e) {
          // Ignore
        }
        
        // If the entire response was used as draft content (no tags), show confirmation
        // Otherwise, show the remaining content after removing tags
        if (originalContent === responseContent && isDraftEditIntent) {
          // Entire response was used as draft, show confirmation
          responseContent = `I've updated the draft "${drafts.find(d => d.id === activeDraftId)?.title || 'Draft'}" with your requested changes.`
        } else if (!responseContent.trim()) {
          // Tags were removed, nothing left, show confirmation
          responseContent = `I've updated the draft "${drafts.find(d => d.id === activeDraftId)?.title || 'Draft'}" with your requested changes.`
        } else {
          // Some content remains after removing tags
          responseContent = `I've updated the draft. ${responseContent}`
        }
      }

      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        content: responseContent,
        role: 'assistant',
        timestamp: new Date(),
        response: response,
        queryMode: queryMode,
      }

      if (currentChatId) {
        const chatIdForTitle = currentChatId
        await addMessageToChat(chatIdForTitle, assistantMessage)

        // Generate AI title from question + response if this is a newly created chat
        const isNewlyCreated = newlyCreatedChatsRef.current.has(chatIdForTitle)
        
        if (isNewlyCreated) {
          devLog('🆕 New chat detected, generating AI title from question and response')
          // Remove from set so we don't regenerate title for subsequent messages
          newlyCreatedChatsRef.current.delete(chatIdForTitle)
          
          // Generate title based on both question and response (understanding the meaning)
          const { generateChatTitle } = await import('@/lib/api')
          generateChatTitle(content, responseContent)
            .then((aiTitle) => {
              devLog('✅ Generated AI title:', aiTitle, 'for chat:', chatIdForTitle)
              return updateChatPreview(chatIdForTitle, aiTitle, '')
            })
            .then(() => {
              devLog('✅ Chat title updated in Firestore')
            })
            .catch(err => {
              console.error('❌ Error in title generation/update:', err)
              // Title will remain as default if update fails
            })
        }
      }

    } catch (error) {
      console.error('Chat error:', error)
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        content: `I apologize, but I encountered an error: ${error instanceof Error ? error.message : 'Unknown error occurred'}`,
        role: 'system',
        timestamp: new Date(),
      }
      // We might want to add this error message to the chat too
      if (currentChatId) {
        await addMessageToChat(currentChatId, errorMessage)
      }
    } finally {
      setIsSending(false)
    }
  }

  // Combine firestore messages with loading state
  const displayMessages = [...firestoreMessages]

  // Inject optimistic thinking message
  if (isSending) {
    displayMessages.push({
      id: 'thinking-placeholder',
      role: 'assistant',
      content: '', // Empty content, thinking UI handles it
      timestamp: new Date(),
      isThinking: true,
      currentStep: currentThinkingStep,
      queryMode: queryMode,
      internetEnabled: internetEnabled
    } as Message)
  }

  return (
    <div className="flex-1 flex flex-col h-full relative">
      {/* Main Content Area - Chat and Draft Side by Side */}
      <div className="flex flex-row h-[calc(100vh-48px)] overflow-hidden gap-0">
        {/* Chat Area - Takes remaining space */}
        <div className="flex flex-col flex-1 min-w-0 overflow-hidden">
          {!activeChatId && displayMessages.length === 0 ? (
            /* Initial Empty State - Properly Centered */
            <div className="flex-1 flex flex-col items-center justify-center px-6 py-12 h-[calc(100vh-48px)]">
              {/* Welcome Message */}
              <div className="text-center mb-12 max-w-lg space-y-3 mx-auto">
                <h1 className="text-lg font-medium tracking-tight text-foreground sm:text-xl">
                  Query your Decision Graph
                </h1>
                <p className="text-sm leading-relaxed text-muted-foreground">
                  Orchestrated retrieval and reasoning over your documents — built for policy text, not open-ended chat.
                </p>
              </div>

              {/* Centered Input Field */}
              <div className="w-full max-w-3xl">
                <ChatInput
                  onSendMessage={handleSendMessage}
                  isLoading={isSending}
                  placeholder="Query the Decision Graph — authorities, clauses, rules…"
                  onThinkingModeChange={handleQueryModeChange}
                  onInternetToggle={handleInternetToggle}
                  onDraftToggle={toggleDraftArea}
                  isDraftEnabled={isDraftAreaVisible}
                />
              </div>
            </div>
          ) : (
            /* Chat Messages State */
            <>
              {/* Messages Area - Independent Scroll with Smooth Behavior */}
              <div
                className="flex-1 overflow-y-auto premium-scrollbar px-4"
                style={{
                  scrollBehavior: 'smooth',
                }}
              >
                <div className="max-w-4xl mx-auto px-6 pt-8 pb-32 space-y-8">
                  {displayMessages.map((message) => (
                    <ChatMessage
                      key={message.id}
                      message={message}
                    />
                  ))}
                  {/* TypingIndicator removed in favor of Thinking Message */}
                  <div ref={messagesEndRef} />
                </div>
              </div>

              {/* Chat Input - Fixed at Bottom */}
              <div className="px-4 pb-2 flex-shrink-0">
                <div className="max-w-4xl mx-auto">
                  <ChatInput
                    onSendMessage={handleSendMessage}
                    isLoading={isSending}
                    placeholder="Query the Decision Graph — authorities, clauses, rules…"
                    onThinkingModeChange={handleQueryModeChange}
                    onInternetToggle={handleInternetToggle}
                    onDraftToggle={toggleDraftArea}
                    isDraftEnabled={isDraftAreaVisible}
                    activeDraftTitle={drafts.find(d => d.id === activeDraftId)?.title || 'Draft'}
                    isDraftNew={(() => {
                      const activeDraft = drafts.find(d => d.id === activeDraftId)
                      return activeDraft ? (
                        activeDraft.content.trim() === '' || 
                        (Date.now() - activeDraft.createdAt.getTime()) < 5 * 60 * 1000
                      ) : false
                    })()}
                  />
                </div>
              </div>
            </>
          )}
        </div>

        {/* Draft Area - Fixed width on the right, collapsible */}
        {isDraftAreaVisible && (
          <div className="w-[400px] flex-shrink-0">
            <DraftArea
              drafts={drafts}
              activeDraftId={activeDraftId}
              onContentChange={handleDraftContentChange}
              onCreateDraft={handleCreateDraft}
              onSetActiveDraft={handleSetActiveDraft}
              onRenameDraft={handleRenameDraft}
              onDeleteDraft={handleDeleteDraft}
            />
          </div>
        )}
      </div>
    </div>
  )
}
