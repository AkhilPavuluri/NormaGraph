'use client'

import * as React from "react"
import { Plus, MessageSquare, Trash2, Settings, User, Search, HelpCircle } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Avatar, AvatarFallback } from "@/components/ui/avatar"
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarSeparator,
} from "@/components/ui/sidebar"
import { SettingsDialog } from "@/components/SettingsDialog"

interface ChatHistoryItem {
  id: string
  title: string
  preview: string
  timestamp: Date
}

interface PremiumSidebarProps {
  chatHistory: ChatHistoryItem[]
  activeChatId?: string
  onNewChat: () => void
  onSelectChat: (chatId: string) => void
  onDeleteChat: (chatId: string) => void
}

export function PremiumSidebar({
  chatHistory,
  activeChatId,
  onNewChat,
  onSelectChat,
  onDeleteChat,
}: PremiumSidebarProps) {
  const formatTime = (date: Date) => {
    const now = new Date()
    const diff = now.getTime() - date.getTime()
    const days = Math.floor(diff / (1000 * 60 * 60 * 24))
    
    if (days === 0) {
      return 'Today'
    } else if (days === 1) {
      return 'Yesterday'
    } else if (days < 7) {
      return `${days} days ago`
    } else {
      return date.toLocaleDateString()
    }
  }

  return (
    <Sidebar collapsible="offcanvas" className="border-r border-gray-800">
      <SidebarHeader className="p-4">
        <SidebarMenu>
          <SidebarMenuItem>
            <SidebarMenuButton
              onClick={onNewChat}
              className="w-full justify-start gap-3 h-12 text-white bg-transparent hover:bg-gray-800 border border-gray-700 hover:border-gray-600"
            >
              <Plus className="h-4 w-4" />
              <span className="text-sm font-medium">New analysis</span>
            </SidebarMenuButton>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarHeader>

      <SidebarContent className="flex min-h-0 flex-1 flex-col px-2">
        <SidebarGroup className="flex min-h-0 flex-1 flex-col">
          <SidebarGroupLabel className="text-xs font-medium text-gray-500 uppercase tracking-wider">
            Recent analyses
          </SidebarGroupLabel>
          <SidebarGroupContent className="flex min-h-[12rem] flex-1 flex-col">
            <SidebarMenu className="flex flex-1 flex-col">
              {chatHistory.length === 0 ? (
                <div className="flex flex-1 flex-col items-center justify-center gap-2 px-4 py-10 text-center">
                  <MessageSquare className="h-8 w-8 shrink-0 text-gray-500" aria-hidden />
                  <p className="text-sm font-medium text-gray-300">No analyses yet</p>
                  <p className="max-w-[14rem] text-xs leading-relaxed text-gray-500">
                    Start a new analysis to see history here.
                  </p>
                </div>
              ) : (
                chatHistory.map((chat) => (
                  <SidebarMenuItem key={chat.id}>
                    <SidebarMenuButton
                      onClick={() => onSelectChat(chat.id)}
                      isActive={activeChatId === chat.id}
                      className="group relative w-full justify-start gap-3 h-auto py-3 px-3 text-gray-300 hover:text-white hover:bg-gray-800 data-[active=true]:bg-gray-800 data-[active=true]:text-white"
                    >
                      <MessageSquare className="h-4 w-4 text-gray-500 flex-shrink-0" />
                      <div className="flex-1 min-w-0">
                        <div className="text-sm font-medium truncate">
                          {chat.title}
                        </div>
                        <div className="text-xs text-gray-500 truncate mt-0.5">
                          {chat.preview}
                        </div>
                        <div className="text-xs text-gray-600 mt-1">
                          {formatTime(chat.timestamp)}
                        </div>
                      </div>
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-6 w-6 text-gray-500 hover:text-gray-300 hover:bg-gray-700 opacity-0 group-hover:opacity-100 transition-opacity"
                        onClick={(e) => {
                          e.stopPropagation()
                          onDeleteChat(chat.id)
                        }}
                      >
                        <Trash2 className="h-3 w-3" />
                      </Button>
                    </SidebarMenuButton>
                  </SidebarMenuItem>
                ))
              )}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>

        <SidebarSeparator className="my-4" />

        <SidebarGroup>
          <SidebarGroupLabel className="text-xs font-medium text-gray-500 uppercase tracking-wider">
            Tools
          </SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              <SidebarMenuItem>
                <SidebarMenuButton className="w-full justify-start gap-3 text-gray-300 hover:text-white hover:bg-gray-800">
                  <Search className="h-4 w-4" />
                  <span className="text-sm">Search</span>
                </SidebarMenuButton>
              </SidebarMenuItem>
              <SidebarMenuItem>
                <SettingsDialog>
                  <SidebarMenuButton className="w-full justify-start gap-3 text-gray-300 hover:text-white hover:bg-gray-800">
                    <Settings className="h-4 w-4" />
                    <span className="text-sm">Settings</span>
                  </SidebarMenuButton>
                </SettingsDialog>
              </SidebarMenuItem>
              <SidebarMenuItem>
                <SidebarMenuButton className="w-full justify-start gap-3 text-gray-300 hover:text-white hover:bg-gray-800">
                  <HelpCircle className="h-4 w-4" />
                  <span className="text-sm">Help</span>
                </SidebarMenuButton>
              </SidebarMenuItem>
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>

      <SidebarFooter className="p-4 border-t border-gray-800">
        <div className="flex items-center gap-3 px-3 py-2 rounded-lg hover:bg-gray-800 cursor-pointer transition-colors">
          <Avatar className="w-8 h-8 bg-primary">
            <AvatarFallback className="text-white text-sm font-medium bg-primary">
              N
            </AvatarFallback>
          </Avatar>
          <div className="flex-1 min-w-0">
            <div className="text-sm font-medium text-white truncate">
              nithin
            </div>
            <div className="text-xs text-gray-500">
              Free Plan
            </div>
          </div>
        </div>
      </SidebarFooter>
    </Sidebar>
  )
}
