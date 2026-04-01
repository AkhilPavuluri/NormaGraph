'use client'

import { useState, useEffect, useCallback } from 'react'
import { queryAPI, queryWithFiles, type QueryResponse } from '@/lib/api'
import { useAuth } from '@/contexts/AuthContext'

// Types
export interface Message {
  id: string
  content: string
  role: 'user' | 'assistant' | 'system'
  timestamp: Date
  response?: QueryResponse & { error?: { code: string; message: string; details?: any } }
  queryMode?: 'qa' | 'deep_think' | 'brainstorm'
  isThinking?: boolean
  currentStep?: string
  attachedFiles?: { name: string; size: number; type: string }[]
}

export interface Draft {
  id: string
  title: string
  content: string
  createdAt: Date
  updatedAt: Date
}

export interface Chat {
  id: string
  title: string
  createdAt: Date
  updatedAt: Date
  activeDraftId?: string | null
}

// Local storage helpers
const getChatStorageKey = (chatId: string) => `chat-${chatId}`
const getMessagesStorageKey = (chatId: string) => `chat-messages-${chatId}`
const getDraftsStorageKey = (chatId: string) => `chat-drafts-${chatId}`

const loadChat = (chatId: string): Chat | null => {
  if (typeof window === 'undefined') return null
  try {
    const stored = localStorage.getItem(getChatStorageKey(chatId))
    if (!stored) return null
    const data = JSON.parse(stored)
    return {
      ...data,
      createdAt: new Date(data.createdAt),
      updatedAt: new Date(data.updatedAt),
    }
  } catch (error) {
    console.error('Error loading chat:', error)
    return null
  }
}

const saveChat = (chat: Chat): void => {
  if (typeof window === 'undefined') return
  try {
    localStorage.setItem(getChatStorageKey(chat.id), JSON.stringify({
      ...chat,
      createdAt: chat.createdAt.toISOString(),
      updatedAt: chat.updatedAt.toISOString(),
    }))
  } catch (error) {
    console.error('Error saving chat:', error)
  }
}

const loadMessages = (chatId: string): Message[] => {
  if (typeof window === 'undefined') return []
  try {
    const stored = localStorage.getItem(getMessagesStorageKey(chatId))
    if (!stored) return []
    const data = JSON.parse(stored)
    return data.map((msg: any) => ({
      ...msg,
      timestamp: new Date(msg.timestamp),
    }))
  } catch (error) {
    console.error('Error loading messages:', error)
    return []
  }
}

const saveMessages = (chatId: string, messages: Message[]): void => {
  if (typeof window === 'undefined') return
  try {
    localStorage.setItem(getMessagesStorageKey(chatId), JSON.stringify(
      messages.map(msg => ({
        ...msg,
        timestamp: msg.timestamp.toISOString(),
      }))
    ))
  } catch (error) {
    console.error('Error saving messages:', error)
  }
}

const loadDrafts = (chatId: string): Draft[] => {
  if (typeof window === 'undefined') return []
  try {
    const stored = localStorage.getItem(getDraftsStorageKey(chatId))
    if (!stored) return []
    const data = JSON.parse(stored)
    return data.map((draft: any) => ({
      ...draft,
      createdAt: new Date(draft.createdAt),
      updatedAt: new Date(draft.updatedAt),
    }))
  } catch (error) {
    console.error('Error loading drafts:', error)
    return []
  }
}

const saveDrafts = (chatId: string, drafts: Draft[]): void => {
  if (typeof window === 'undefined') return
  try {
    localStorage.setItem(getDraftsStorageKey(chatId), JSON.stringify(
      drafts.map(draft => ({
        ...draft,
        createdAt: draft.createdAt.toISOString(),
        updatedAt: draft.updatedAt.toISOString(),
      }))
    ))
  } catch (error) {
    console.error('Error saving drafts:', error)
  }
}

export function useFirestoreChat() {
  const [currentChatId, setCurrentChatId] = useState<string | null>(null)
  const [messages, setMessages] = useState<Message[]>([])
  const [drafts, setDrafts] = useState<Draft[]>([])
  const [activeDraftId, setActiveDraftId] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [sending, setSending] = useState(false)
  const { user } = useAuth()

  // Helper to sanitize message data (remove undefined fields)
  const sanitizeMessage = (msg: Partial<Message>): any => {
    const clean: any = {}
    Object.keys(msg).forEach(key => {
      const value = msg[key as keyof Message]
      if (value !== undefined && value !== null) {
        clean[key] = value
      }
    })
    return clean
  }

  // Load data when chat changes
  useEffect(() => {
    if (!currentChatId) {
      setMessages([])
      setDrafts([])
      setActiveDraftId(null)
      setLoading(false)
      return
    }

    setLoading(true)

    // Load chat, messages, and drafts
    const chat = loadChat(currentChatId)
    const loadedMessages = loadMessages(currentChatId)
    const loadedDrafts = loadDrafts(currentChatId)

    setMessages(loadedMessages.sort((a, b) => a.timestamp.getTime() - b.timestamp.getTime()))
    setDrafts(loadedDrafts.sort((a, b) => a.createdAt.getTime() - b.createdAt.getTime()))

    // Set active draft
    if (chat?.activeDraftId) {
      setActiveDraftId(chat.activeDraftId)
    } else if (loadedDrafts.length > 0) {
      setActiveDraftId(loadedDrafts[0].id)
    } else {
      setActiveDraftId(null)
    }

    setLoading(false)
  }, [currentChatId])

  // Persist messages when they change
  useEffect(() => {
    if (currentChatId && messages.length > 0) {
      saveMessages(currentChatId, messages)
    }
  }, [messages, currentChatId])

  // Persist drafts when they change
  useEffect(() => {
    if (currentChatId && drafts.length > 0) {
      saveDrafts(currentChatId, drafts)
    }
  }, [drafts, currentChatId])

  // Create a new chat
  const createChat = useCallback(async (): Promise<string> => {
    const chatId = `chat-${Date.now()}`
    const now = new Date()
    
    // Create default draft
    const defaultDraft: Draft = {
      id: `draft-${Date.now()}`,
      title: 'Draft 1',
      content: '',
      createdAt: now,
      updatedAt: now
    }
    
    const newChat: Chat = {
      id: chatId,
      title: 'New analysis',
      createdAt: now,
      updatedAt: now,
      activeDraftId: defaultDraft.id
    }
    
    saveChat(newChat)
    saveDrafts(chatId, [defaultDraft])
    saveMessages(chatId, [])
    
    setCurrentChatId(chatId)
    setDrafts([defaultDraft])
    setActiveDraftId(defaultDraft.id)
    setMessages([])
    
    return chatId
  }, [])

  // Send a message (user message + get assistant response)
  const sendMessage = useCallback(async (
    content: string,
    files?: File[],
    queryMode: 'qa' | 'deep_think' | 'brainstorm' = 'qa',
    internetEnabled: boolean = false
  ): Promise<void> => {
    if (!currentChatId) {
      // Create chat if none exists
      const newChatId = await createChat()
      setCurrentChatId(newChatId)
      // Recursively call with new chat ID
      return sendMessage(content, files, queryMode, internetEnabled)
    }

    setSending(true)

    try {
      // 1. Save user message
      const userMessage: Message = {
        id: `msg-${Date.now()}`,
        content,
        role: 'user',
        timestamp: new Date(),
        queryMode,
        attachedFiles: files?.map(f => ({
          name: f.name,
          size: f.size,
          type: f.type
        }))
      }

      const updatedMessages = [...messages, userMessage]
      setMessages(updatedMessages)
      saveMessages(currentChatId, updatedMessages)

      // Update chat title from first user message
      const chat = loadChat(currentChatId)
      if (chat && chat.title === 'New analysis') {
        const newTitle = content.length > 30 ? content.substring(0, 30) + '...' : content
        const updatedChat = { ...chat, title: newTitle, updatedAt: new Date() }
        saveChat(updatedChat)
      }

      // 2. Call backend API (disabled - will return mock response)
      let response: QueryResponse
      const conversationHistory = updatedMessages
        .filter(msg => msg.role === 'user' || msg.role === 'assistant')
        .slice(-10)
        .map(msg => ({
          role: msg.role,
          content: msg.content
        }))

      try {
        if (files && files.length > 0) {
          response = await queryWithFiles(
            content,
            files,
            queryMode,
            internetEnabled,
            conversationHistory
          )
        } else {
          response = await queryAPI({
            query: content,
            simulate_failure: false,
            mode: queryMode,
            internet_enabled: internetEnabled,
            conversation_history: conversationHistory
          })
        }
      } catch (apiError) {
        // Handle API errors properly
        const errorResponse: QueryResponse & { error?: { code: string; message: string; details?: any } } = {
          answer: '',
          citations: [],
          processing_trace: {
            language: 'en',
            retrieval: { dense: [], sparse: [] },
            kg_traversal: '',
            controller_iterations: 0
          },
          risk_assessment: 'high',
          error: {
            code: 'API_ERROR',
            message: apiError instanceof Error ? apiError.message : 'Unknown API error',
            details: apiError
          }
        }
        response = errorResponse
      }

      // 3. Save assistant message
      const assistantMessage: Message = {
        id: `msg-${Date.now()}`,
        content: response.answer || (response as any).error?.message || 'No response generated',
        role: 'assistant',
        timestamp: new Date(),
        response: response,
        queryMode
      }

      const finalMessages = [...updatedMessages, assistantMessage]
      setMessages(finalMessages)
      saveMessages(currentChatId, finalMessages)

      // Update chat updatedAt
      const chatForUpdate = loadChat(currentChatId)
      if (chatForUpdate) {
        const updatedChat = { ...chatForUpdate, updatedAt: new Date() }
        saveChat(updatedChat)
      }

    } catch (error) {
      console.error('Error sending message:', error)
      
      // Save error message
      const errorMessage: Message = {
        id: `msg-${Date.now()}`,
        content: `I apologize, but I encountered an error: ${error instanceof Error ? error.message : 'Unknown error occurred'}`,
        role: 'system',
        timestamp: new Date(),
        response: {
          answer: '',
          citations: [],
          processing_trace: {
            language: 'en',
            retrieval: { dense: [], sparse: [] },
            kg_traversal: '',
            controller_iterations: 0
          },
          risk_assessment: 'high',
          error: {
            code: 'SYSTEM_ERROR',
            message: error instanceof Error ? error.message : 'Unknown error',
            details: error
          }
        }
      }
      
      const finalMessages = [...messages, errorMessage]
      setMessages(finalMessages)
      saveMessages(currentChatId, finalMessages)
    } finally {
      setSending(false)
    }
  }, [currentChatId, messages, createChat])

  // Draft management
  const createDraft = useCallback(async (): Promise<string> => {
    if (!currentChatId) {
      const newChatId = await createChat()
      setCurrentChatId(newChatId)
      return createDraft()
    }

    const draftCount = drafts.length + 1
    const draftId = `draft-${Date.now()}`
    const now = new Date()

    const newDraft: Draft = {
      id: draftId,
      title: `Draft ${draftCount}`,
      content: '',
      createdAt: now,
      updatedAt: now
    }

    const updatedDrafts = [...drafts, newDraft]
    setDrafts(updatedDrafts)
    saveDrafts(currentChatId, updatedDrafts)

    // Set as active draft
    setActiveDraftId(draftId)
    const chat = loadChat(currentChatId)
    if (chat) {
      const updatedChat = { ...chat, activeDraftId: draftId, updatedAt: now }
      saveChat(updatedChat)
    }

    return draftId
  }, [currentChatId, drafts, createChat])

  const updateDraftContent = useCallback(async (draftId: string, content: string): Promise<void> => {
    if (!currentChatId) return

    const updatedDrafts = drafts.map(draft =>
      draft.id === draftId
        ? { ...draft, content, updatedAt: new Date() }
        : draft
    )
    setDrafts(updatedDrafts)
    saveDrafts(currentChatId, updatedDrafts)
  }, [currentChatId, drafts])

  const appendToDraft = useCallback(async (content: string): Promise<void> => {
    if (!currentChatId || !activeDraftId) return

    const activeDraft = drafts.find(d => d.id === activeDraftId)
    if (activeDraft) {
      const separator = activeDraft.content ? '\n\n---\n\n' : ''
      const newContent = `${activeDraft.content}${separator}${content}`
      
      const updatedDrafts = drafts.map(draft =>
        draft.id === activeDraftId
          ? { ...draft, content: newContent, updatedAt: new Date() }
          : draft
      )
      setDrafts(updatedDrafts)
      saveDrafts(currentChatId, updatedDrafts)
    }
  }, [currentChatId, activeDraftId, drafts])

  const setActiveDraft = useCallback(async (draftId: string): Promise<void> => {
    if (!currentChatId) return

    setActiveDraftId(draftId)
    const chat = loadChat(currentChatId)
    if (chat) {
      const updatedChat = { ...chat, activeDraftId: draftId, updatedAt: new Date() }
      saveChat(updatedChat)
    }
  }, [currentChatId])

  const renameDraft = useCallback(async (draftId: string, newTitle: string): Promise<void> => {
    if (!currentChatId) return

    const updatedDrafts = drafts.map(draft =>
      draft.id === draftId
        ? { ...draft, title: newTitle, updatedAt: new Date() }
        : draft
    )
    setDrafts(updatedDrafts)
    saveDrafts(currentChatId, updatedDrafts)
  }, [currentChatId, drafts])

  const deleteDraft = useCallback(async (draftId: string): Promise<void> => {
    if (!currentChatId || drafts.length <= 1) {
      alert('Cannot delete the last draft. At least one draft must exist.')
      return
    }

    const updatedDrafts = drafts.filter(d => d.id !== draftId)
    setDrafts(updatedDrafts)
    saveDrafts(currentChatId, updatedDrafts)

    // If deleting active draft, switch to first remaining draft
    if (activeDraftId === draftId && updatedDrafts.length > 0) {
      setActiveDraftId(updatedDrafts[0].id)
      const chat = loadChat(currentChatId)
      if (chat) {
        const updatedChat = { ...chat, activeDraftId: updatedDrafts[0].id, updatedAt: new Date() }
        saveChat(updatedChat)
      }
    }
  }, [currentChatId, drafts, activeDraftId])

  // Get active draft
  const activeDraft = drafts.find(d => d.id === activeDraftId) || drafts[0] || null

  return {
    // State
    currentChatId,
    messages,
    drafts,
    activeDraft,
    activeDraftId,
    loading,
    sending,
    
    // Actions
    setCurrentChatId,
    createChat,
    sendMessage,
    createDraft,
    updateDraftContent,
    appendToDraft,
    setActiveDraft,
    renameDraft,
    deleteDraft
  }
}
