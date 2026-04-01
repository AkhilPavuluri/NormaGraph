'use client'

import { useState, useEffect, useCallback } from 'react'

export interface Message {
  id: string
  content: string
  role: 'user' | 'assistant' | 'system'
  timestamp: Date
  response?: any
  queryMode?: any
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
  messages: Message[]
  drafts: Draft[]
  activeDraftId: string | null
  createdAt: Date
  updatedAt: Date
}

const STORAGE_KEYS = {
  CHATS: 'local-chats',
  CURRENT_CHAT_ID: 'local-current-chat-id'
}

// Helper to serialize/deserialize dates
const serializeChat = (chat: Chat): any => ({
  ...chat,
  createdAt: chat.createdAt.toISOString(),
  updatedAt: chat.updatedAt.toISOString(),
  messages: chat.messages.map(msg => ({
    ...msg,
    timestamp: msg.timestamp.toISOString()
  })),
  drafts: chat.drafts.map(draft => ({
    ...draft,
    createdAt: draft.createdAt.toISOString(),
    updatedAt: draft.updatedAt.toISOString()
  }))
})

const deserializeChat = (data: any): Chat => {
  // Migration: Convert old single draft string to new drafts array
  let drafts: Draft[] = []
  let activeDraftId: string | null = null

  if (data.drafts && Array.isArray(data.drafts)) {
    // New format: has drafts array
    drafts = data.drafts.map((draft: any) => ({
      ...draft,
      createdAt: new Date(draft.createdAt),
      updatedAt: new Date(draft.updatedAt)
    }))
    activeDraftId = data.activeDraftId || (drafts.length > 0 ? drafts[0].id : null)
  } else if (data.draft !== undefined) {
    // Old format: single draft string - migrate to new format
    const draftId = Date.now().toString()
    drafts = [{
      id: draftId,
      title: 'Draft 1',
      content: data.draft || '',
      createdAt: new Date(),
      updatedAt: new Date()
    }]
    activeDraftId = draftId
  } else {
    // No drafts - create default
    const draftId = Date.now().toString()
    drafts = [{
      id: draftId,
      title: 'Draft 1',
      content: '',
      createdAt: new Date(),
      updatedAt: new Date()
    }]
    activeDraftId = draftId
  }

  // Ensure at least one draft exists
  if (drafts.length === 0) {
    const draftId = Date.now().toString()
    drafts = [{
      id: draftId,
      title: 'Draft 1',
      content: '',
      createdAt: new Date(),
      updatedAt: new Date()
    }]
    activeDraftId = draftId
  }

  return {
    ...data,
    createdAt: new Date(data.createdAt),
    updatedAt: new Date(data.updatedAt),
    messages: data.messages.map((msg: any) => ({
      ...msg,
      timestamp: new Date(msg.timestamp)
    })),
    drafts,
    activeDraftId
  }
}

// Load chats from localStorage
const loadChats = (): Chat[] => {
  // Check if we're in a browser environment
  if (typeof window === 'undefined') return []
  try {
    const stored = localStorage.getItem(STORAGE_KEYS.CHATS)
    if (!stored) return []
    const parsed = JSON.parse(stored)
    return parsed.map(deserializeChat)
  } catch (error) {
    console.error('Error loading chats from localStorage:', error)
    return []
  }
}

// Save chats to localStorage
const saveChats = (chats: Chat[]): void => {
  // Check if we're in a browser environment
  if (typeof window === 'undefined') return
  try {
    const serialized = chats.map(serializeChat)
    localStorage.setItem(STORAGE_KEYS.CHATS, JSON.stringify(serialized))
  } catch (error) {
    if (error instanceof DOMException && error.name === 'QuotaExceededError') {
      console.warn('localStorage quota exceeded')
      alert('Storage quota exceeded. Please delete some chats to free up space.')
    } else {
      console.error('Error saving chats to localStorage:', error)
    }
  }
}

// Load current chat ID
const loadCurrentChatId = (): string | null => {
  // Check if we're in a browser environment
  if (typeof window === 'undefined') return null
  try {
    return localStorage.getItem(STORAGE_KEYS.CURRENT_CHAT_ID)
  } catch (error) {
    console.error('Error loading current chat ID:', error)
    return null
  }
}

// Save current chat ID
const saveCurrentChatId = (chatId: string | null): void => {
  // Check if we're in a browser environment
  if (typeof window === 'undefined') return
  try {
    if (chatId) {
      localStorage.setItem(STORAGE_KEYS.CURRENT_CHAT_ID, chatId)
    } else {
      localStorage.removeItem(STORAGE_KEYS.CURRENT_CHAT_ID)
    }
  } catch (error) {
    console.error('Error saving current chat ID:', error)
  }
}

// Helper to create default draft
const createDefaultDraft = (): Draft => {
  const draftId = Date.now().toString()
  return {
    id: draftId,
    title: 'Draft 1',
    content: '',
    createdAt: new Date(),
    updatedAt: new Date()
  }
}

export function useLocalChatStore() {
  // Initialize with empty state to avoid hydration mismatch
  // Load from localStorage only on client side after mount
  const [chats, setChats] = useState<Chat[]>([])
  const [currentChatId, setCurrentChatId] = useState<string | null>(null)
  const [isHydrated, setIsHydrated] = useState(false)

  // Load from localStorage only on client side after mount
  useEffect(() => {
    const loaded = loadChats()
    if (loaded.length === 0) {
      // If no chats exist, create a default one with a default draft
      const defaultDraft = createDefaultDraft()
      const defaultChat: Chat = {
        id: Date.now().toString(),
        title: 'New analysis',
        messages: [],
        drafts: [defaultDraft],
        activeDraftId: defaultDraft.id,
        createdAt: new Date(),
        updatedAt: new Date()
      }
      saveChats([defaultChat])
      saveCurrentChatId(defaultChat.id)
      setChats([defaultChat])
      setCurrentChatId(defaultChat.id)
    } else {
      // Ensure all loaded chats have at least one draft
      const migratedChats = loaded.map(chat => {
        if (!chat.drafts || chat.drafts.length === 0) {
          const defaultDraft = createDefaultDraft()
          return {
            ...chat,
            drafts: [defaultDraft],
            activeDraftId: defaultDraft.id
          }
        }
        if (!chat.activeDraftId && chat.drafts.length > 0) {
          return {
            ...chat,
            activeDraftId: chat.drafts[0].id
          }
        }
        return chat
      })
      setChats(migratedChats)
      // Load current chat ID
      const saved = loadCurrentChatId()
      if (saved && migratedChats.some(c => c.id === saved)) {
        setCurrentChatId(saved)
      } else {
        setCurrentChatId(migratedChats.length > 0 ? migratedChats[0].id : null)
      }
    }
    setIsHydrated(true)
  }, [])

  // Persist chats to localStorage whenever they change (only after hydration)
  useEffect(() => {
    if (isHydrated) {
      saveChats(chats)
    }
  }, [chats, isHydrated])

  // Persist current chat ID whenever it changes (only after hydration)
  useEffect(() => {
    if (isHydrated) {
      saveCurrentChatId(currentChatId)
    }
  }, [currentChatId, isHydrated])

  // Create a new chat
  const createChat = useCallback((): string => {
    const defaultDraft = createDefaultDraft()
    const chatId = Date.now().toString()
    const newChat: Chat = {
      id: chatId,
      title: 'New analysis',
      messages: [],
      drafts: [defaultDraft],
      activeDraftId: defaultDraft.id,
      createdAt: new Date(),
      updatedAt: new Date()
    }
    
    // Set current chat ID first, then add chat to ensure messages getter works
    setCurrentChatId(chatId)
    setChats(prev => {
      // Check if chat already exists (shouldn't happen, but safety check)
      const exists = prev.find(c => c.id === chatId)
      if (exists) return prev
      return [newChat, ...prev]
    })
    
    return chatId
  }, [])

  // Delete a chat (prevent deletion if it's the last one)
  const deleteChat = useCallback((chatId: string): void => {
    setChats(prev => {
      if (prev.length <= 1) {
        alert('Cannot delete the last chat. Please create a new chat first.')
        return prev
      }
      
      const filtered = prev.filter(c => c.id !== chatId)
      
      // If deleting current chat, switch to first available
      if (currentChatId === chatId) {
        setCurrentChatId(filtered.length > 0 ? filtered[0].id : null)
      }
      
      return filtered
    })
  }, [currentChatId])

  // Update chat title
  const updateChatTitle = useCallback((chatId: string, title: string): void => {
    setChats(prev => prev.map(chat => 
      chat.id === chatId 
        ? { ...chat, title, updatedAt: new Date() }
        : chat
    ))
  }, [])

  // Add message to chat
  const addMessage = useCallback((chatId: string, message: Message): void => {
    console.log('🔵 addMessage called:', { chatId, messageRole: message.role, messageContent: message.content.substring(0, 50) })
    setChats(prev => {
      const chat = prev.find(c => c.id === chatId)
      if (!chat) {
        console.error(`❌ Chat ${chatId} not found when adding message. Available chats:`, prev.map(c => c.id))
        // If chat doesn't exist, create it (shouldn't happen, but safety)
        const defaultDraft = createDefaultDraft()
        const newChat: Chat = {
          id: chatId,
          title: 'New analysis',
          messages: [message],
          drafts: [defaultDraft],
          activeDraftId: defaultDraft.id,
          createdAt: new Date(),
          updatedAt: new Date()
        }
        return [newChat, ...prev]
      }
      
      // Auto-update title from first user message if still default
      let newTitle = chat.title
      if (message.role === 'user' && chat.title === 'New analysis') {
        newTitle = message.content.length > 30 
          ? message.content.substring(0, 30) + '...' 
          : message.content
      }
      
      const updatedChat = {
        ...chat,
        title: newTitle,
        messages: [...chat.messages, message],
        updatedAt: new Date()
      }
      console.log('✅ Updated chat:', { chatId, messageCount: updatedChat.messages.length, messages: updatedChat.messages.map(m => ({ id: m.id, role: m.role })) })
      
      return prev.map(c => c.id === chatId ? updatedChat : c)
    })
  }, [])

  // Create a new draft for a chat
  const createDraft = useCallback((chatId: string): string => {
    if (!chatId) {
      console.error('Cannot create draft: chatId is null')
      return ''
    }
    
    let newDraftId = ''
    setChats(prev => {
      const chat = prev.find(c => c.id === chatId)
      if (!chat) {
        console.error(`Cannot create draft: chat ${chatId} not found`)
        return prev
      }
      
      const draftCount = chat.drafts.length + 1
      const newDraft: Draft = {
        id: Date.now().toString(),
        title: `Draft ${draftCount}`,
        content: '',
        createdAt: new Date(),
        updatedAt: new Date()
      }
      newDraftId = newDraft.id
      
      return prev.map(c => 
        c.id === chatId
          ? {
              ...c,
              drafts: [...c.drafts, newDraft],
              activeDraftId: newDraft.id,
              updatedAt: new Date()
            }
          : c
      )
    })
    return newDraftId
  }, [])

  // Update draft content for a chat
  const updateDraftContent = useCallback((chatId: string, draftId: string, content: string): void => {
    setChats(prev => prev.map(chat => {
      if (chat.id === chatId) {
        return {
          ...chat,
          drafts: chat.drafts.map(draft =>
            draft.id === draftId
              ? { ...draft, content, updatedAt: new Date() }
              : draft
          ),
          updatedAt: new Date()
        }
      }
      return chat
    }))
  }, [])

  // Append content to active draft
  const appendToDraft = useCallback((chatId: string, content: string): void => {
    setChats(prev => prev.map(chat => {
      if (chat.id === chatId && chat.activeDraftId) {
        const activeDraft = chat.drafts.find(d => d.id === chat.activeDraftId)
        if (activeDraft) {
          const separator = activeDraft.content ? '\n\n---\n\n' : ''
          const newContent = `${activeDraft.content}${separator}${content}`
          return {
            ...chat,
            drafts: chat.drafts.map(draft =>
              draft.id === chat.activeDraftId
                ? { ...draft, content: newContent, updatedAt: new Date() }
                : draft
            ),
            updatedAt: new Date()
          }
        }
      }
      return chat
    }))
  }, [])

  // Set active draft
  const setActiveDraft = useCallback((chatId: string, draftId: string): void => {
    setChats(prev => prev.map(chat =>
      chat.id === chatId
        ? { ...chat, activeDraftId: draftId, updatedAt: new Date() }
        : chat
    ))
  }, [])

  // Rename a draft
  const renameDraft = useCallback((chatId: string, draftId: string, newTitle: string): void => {
    setChats(prev => prev.map(chat => {
      if (chat.id === chatId) {
        return {
          ...chat,
          drafts: chat.drafts.map(draft =>
            draft.id === draftId
              ? { ...draft, title: newTitle, updatedAt: new Date() }
              : draft
          ),
          updatedAt: new Date()
        }
      }
      return chat
    }))
  }, [])

  // Delete a draft (keep at least one)
  const deleteDraft = useCallback((chatId: string, draftId: string): void => {
    setChats(prev => prev.map(chat => {
      if (chat.id === chatId && chat.drafts.length > 1) {
        const filteredDrafts = chat.drafts.filter(d => d.id !== draftId)
        let newActiveDraftId = chat.activeDraftId
        
        // If deleting active draft, switch to first remaining draft
        if (chat.activeDraftId === draftId) {
          newActiveDraftId = filteredDrafts.length > 0 ? filteredDrafts[0].id : null
        }
        
        return {
          ...chat,
          drafts: filteredDrafts,
          activeDraftId: newActiveDraftId,
          updatedAt: new Date()
        }
      }
      return chat
    }))
  }, [])

  // Legacy: Update draft (for backward compatibility - updates active draft)
  const updateDraft = useCallback((chatId: string, draft: string): void => {
    setChats(prev => prev.map(chat => {
      if (chat.id === chatId && chat.activeDraftId) {
        return {
          ...chat,
          drafts: chat.drafts.map(d =>
            d.id === chat.activeDraftId
              ? { ...d, content: draft, updatedAt: new Date() }
              : d
          ),
          updatedAt: new Date()
        }
      }
      return chat
    }))
  }, [])

  // Copy all messages to active draft
  const copyMessagesToDraft = useCallback((chatId: string): void => {
    const chat = chats.find(c => c.id === chatId)
    if (!chat || !chat.activeDraftId) return

    const conversationText = chat.messages
      .filter(msg => msg.role === 'user' || msg.role === 'assistant')
      .map(msg => {
        const role = msg.role === 'user' ? 'User' : 'Assistant'
        return `${role}: ${msg.content}`
      })
      .join('\n\n')

    appendToDraft(chatId, conversationText)
  }, [chats, appendToDraft])

  // Get current chat
  const currentChat = chats.find(c => c.id === currentChatId) || null

  // Get messages for current chat
  const messages = currentChat?.messages || []

  // Get drafts for current chat
  const drafts = currentChat?.drafts || []

  // Get active draft for current chat
  const activeDraft = currentChat?.activeDraftId && currentChat.drafts
    ? currentChat.drafts.find(d => d.id === currentChat.activeDraftId)
    : (currentChat?.drafts && currentChat.drafts.length > 0 ? currentChat.drafts[0] : null)

  // Legacy: Get draft content (for backward compatibility)
  const draft = activeDraft?.content || ''

  return {
    chats,
    currentChatId,
    currentChat,
    messages,
    drafts,
    activeDraft,
    activeDraftId: currentChat?.activeDraftId || null,
    draft, // Legacy support
    createChat,
    deleteChat,
    updateChatTitle,
    addMessage,
    createDraft,
    updateDraftContent,
    appendToDraft,
    setActiveDraft,
    renameDraft,
    deleteDraft,
    updateDraft, // Legacy support
    copyMessagesToDraft,
    setCurrentChatId
  }
}

