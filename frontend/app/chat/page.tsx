'use client'

import { useState, useEffect } from 'react'
import { AppSidebar } from "@/components/app-sidebar"
import { SiteHeader } from "@/components/site-header"
import { SidebarInset, SidebarProvider } from "@/components/ui/sidebar"
import { ChatBot } from './ChatBot'
import { modelService } from '@/lib/modelService'
import { useChatStore } from '@/hooks/useChatStore'
import { ProtectedRoute } from '@/components/ProtectedRoute'

export default function ChatPage() {
  const { chats, deleteChat, loading } = useChatStore()
  const [activeChatId, setActiveChatId] = useState<string | undefined>()
  const [selectedModel, setSelectedModel] = useState<string>("")

  // Debug: Log chats and loading state
  useEffect(() => {
    console.log('Chats state:', { chatsCount: chats.length, loading, chats })
  }, [chats, loading])

  // Load available models and set default
  useEffect(() => {
    const loadDefaultModel = async () => {
      try {
        console.log('Loading available models for default selection...')
        const allModels = await modelService.refreshModels()
        console.log('Available models:', allModels)

        if (allModels.length > 0) {
          // Prefer cloud models first, then Ollama models
          const cloudModels = allModels.filter(m => m.category === 'cloud' && m.isAvailable)
          const ollamaModels = allModels.filter(m => m.category === 'ollama')

          const defaultModel = cloudModels.length > 0 ? cloudModels[0].id :
            ollamaModels.length > 0 ? ollamaModels[0].id :
              allModels[0].id
          console.log('Setting default model to:', defaultModel)
          setSelectedModel(defaultModel)
        } else {
          console.log('No models available, using fallback')
          setSelectedModel("backend-default")
        }
      } catch (error) {
        console.error('Error loading models:', error)
        setSelectedModel("backend-default")
      }
    }

    loadDefaultModel()
  }, [])

  const handleNewChat = () => {
    setActiveChatId(undefined)
  }

  const handleSelectChat = (chatId: string) => {
    setActiveChatId(chatId)
  }

  const handleDeleteChat = async (chatId: string) => {
    await deleteChat(chatId)
    if (activeChatId === chatId) {
      setActiveChatId(undefined)
    }
  }

  const handleChatCreated = (chatId: string) => {
    setActiveChatId(chatId)
  }

  const handleModelChange = (modelId: string) => {
    console.log('Model changed to:', modelId)
    setSelectedModel(modelId)
  }

  // Render the normal chat interface with sidebar and header
  return (
    <ProtectedRoute>
      <SidebarProvider>
        <AppSidebar
          variant="inset"
          chatHistory={chats}
          activeChatId={activeChatId}
          onNewChat={handleNewChat}
          onSelectChat={handleSelectChat}
          onDeleteChat={handleDeleteChat}
        />
        <SidebarInset>
          <SiteHeader
            selectedModel={selectedModel}
            onModelChange={handleModelChange}
          />

          <div className="flex-1 flex flex-col min-h-0 relative">
            {selectedModel ? (
              <ChatBot
                activeChatId={activeChatId}
                onChatCreated={handleChatCreated}
                selectedModel={selectedModel}
              />
            ) : (
              <div className="flex-1 flex items-center justify-center">
                <div className="text-center">
                  <p className="text-muted-foreground">Loading available models...</p>
                </div>
              </div>
            )}
          </div>
        </SidebarInset>
      </SidebarProvider>
    </ProtectedRoute>
  )
}