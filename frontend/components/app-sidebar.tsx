"use client"

import * as React from "react"
import {
  MessageSquare,
  Plus,
  Trash2,
  FileEdit,
  MoreVertical,
  Share2,
  Pencil,
  Archive,
} from "lucide-react"

import { NavUser } from "@/components/nav-user"
import { useAuth } from "@/contexts/AuthContext"
import { Button } from "@/components/ui/button"
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { BrandMark } from "@/components/BrandMark"
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
} from "@/components/ui/sidebar"

interface ChatHistoryItem {
  id: string
  title: string
  preview: string
  timestamp: Date
  messageCount?: number
}

interface AppSidebarProps extends React.ComponentProps<typeof Sidebar> {
  chatHistory?: ChatHistoryItem[]
  activeChatId?: string
  onNewChat?: () => void
  onSelectChat?: (chatId: string) => void
  onDeleteChat?: (chatId: string) => void
  onShareChat?: (chatId: string) => void
  onRenameChat?: (chatId: string, newTitle: string) => void
}

// Component to show tooltip only when text is truncated
function TruncatedTooltip({ text }: { text: string }) {
  const [isTruncated, setIsTruncated] = React.useState(false)
  const textRef = React.useRef<HTMLDivElement>(null)

  React.useEffect(() => {
    const checkTruncation = () => {
      if (textRef.current) {
        setIsTruncated(textRef.current.scrollWidth > textRef.current.clientWidth)
      }
    }

    // Check after a brief delay to ensure DOM is ready
    const timeoutId = setTimeout(checkTruncation, 0)

    // Use ResizeObserver for better performance
    let resizeObserver: ResizeObserver | null = null
    if (textRef.current) {
      resizeObserver = new ResizeObserver(checkTruncation)
      resizeObserver.observe(textRef.current)
    }

    window.addEventListener('resize', checkTruncation)

    return () => {
      clearTimeout(timeoutId)
      if (resizeObserver) {
        resizeObserver.disconnect()
      }
      window.removeEventListener('resize', checkTruncation)
    }
  }, [text])

  const divElement = <div ref={textRef} className="text-sm font-medium truncate">{text}</div>

  if (!isTruncated) {
    return divElement
  }

  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <div ref={textRef} className="text-sm font-medium truncate">{text}</div>
      </TooltipTrigger>
      <TooltipContent>
        <p>{text}</p>
      </TooltipContent>
    </Tooltip>
  )
}

export function AppSidebar({
  chatHistory = [],
  activeChatId,
  onNewChat,
  onSelectChat,
  onDeleteChat,
  onShareChat,
  onRenameChat,
  ...props
}: AppSidebarProps) {
  const [editingChatId, setEditingChatId] = React.useState<string | null>(null)
  const [editingTitle, setEditingTitle] = React.useState<string>('')

  const getDayLabel = (date: Date): string => {
    const now = new Date()
    const today = new Date(now.getFullYear(), now.getMonth(), now.getDate())
    const chatDate = new Date(date.getFullYear(), date.getMonth(), date.getDate())
    const diff = Math.floor((today.getTime() - chatDate.getTime()) / (1000 * 60 * 60 * 24))

    if (diff === 0) {
      return 'Today'
    } else if (diff === 1) {
      return 'Yesterday'
    } else if (diff < 7) {
      return date.toLocaleDateString('en-US', { weekday: 'long' })
    } else {
      return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: date.getFullYear() !== now.getFullYear() ? 'numeric' : undefined })
    }
  }

  // Group chats by day
  const groupChatsByDay = () => {
    const groups: Record<string, ChatHistoryItem[]> = {}

    chatHistory.forEach((chat) => {
      const dayLabel = getDayLabel(chat.timestamp)
      if (!groups[dayLabel]) {
        groups[dayLabel] = []
      }
      groups[dayLabel].push(chat)
    })

    // Sort groups by date (most recent first)
    const sortedDays = Object.keys(groups).sort((a, b) => {
      const now = new Date()
      const today = new Date(now.getFullYear(), now.getMonth(), now.getDate())

      const getDayValue = (label: string): number => {
        if (label === 'Today') return 0
        if (label === 'Yesterday') return 1
        // For other days, use the timestamp of the first chat in that group
        const firstChat = groups[label][0]
        return Math.floor((today.getTime() - firstChat.timestamp.getTime()) / (1000 * 60 * 60 * 24))
      }

      return getDayValue(a) - getDayValue(b)
    })

    return sortedDays.map(day => ({ day, chats: groups[day] }))
  }

  const dayGroups = groupChatsByDay()

  // Handle rename
  const handleRenameStart = (chatId: string, currentTitle: string) => {
    setEditingChatId(chatId)
    setEditingTitle(currentTitle)
  }

  const handleRenameSubmit = (chatId: string) => {
    if (editingTitle.trim() && onRenameChat) {
      onRenameChat(chatId, editingTitle.trim())
    }
    setEditingChatId(null)
    setEditingTitle('')
  }

  const handleRenameCancel = () => {
    setEditingChatId(null)
    setEditingTitle('')
  }

  const handleRenameKeyDown = (e: React.KeyboardEvent, chatId: string) => {
    if (e.key === 'Enter') {
      e.preventDefault()
      handleRenameSubmit(chatId)
    } else if (e.key === 'Escape') {
      handleRenameCancel()
    }
  }

  // Handle share as PDF
  const handleShareAsPdf = async (chatId: string) => {
    if (onShareChat) {
      onShareChat(chatId)
    } else {
      // Fallback: Create a simple text export
      const chat = chatHistory.find(c => c.id === chatId)
      if (chat) {
        const content = `Analysis: ${chat.title}\n\n${chat.preview}`
        const blob = new Blob([content], { type: 'text/plain' })
        const url = URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = `${chat.title.replace(/[^a-z0-9]/gi, '_')}.txt`
        document.body.appendChild(a)
        a.click()
        document.body.removeChild(a)
        URL.revokeObjectURL(url)
      }
    }
  }

  // Get authenticated user
  const { user } = useAuth()

  // Map Firebase user to NavUser format
  const userData = React.useMemo(() => {
    if (user) {
      return {
        name: user.displayName || user.email?.split('@')[0] || 'User',
        email: user.email || 'No email',
        avatar: user.photoURL || '',
      }
    }
    // Fallback to default if no user
    return {
      name: 'User',
      email: 'user@gmail.com',
      avatar: '',
    }
  }, [user])

  return (
    <Sidebar collapsible="offcanvas" {...props} className="flex flex-col">
      <SidebarHeader className="flex-shrink-0">
        <SidebarMenu>
          <SidebarMenuItem>
            <SidebarMenuButton
              asChild
              className="data-[slot=sidebar-menu-button]:!p-1.5"
            >
              <a href="/" className="flex min-w-0 items-center gap-2.5">
                <BrandMark className="h-9 w-9 shrink-0 p-1.5" iconClassName="h-5 w-5 sm:h-5 sm:w-5 md:h-5 md:w-5" />
                <span className="truncate text-base font-semibold tracking-tight">
                  NormaGraph
                </span>
              </a>
            </SidebarMenuButton>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarHeader>

      {/* Scrollable Chat History Section */}
      <SidebarContent className="flex-1 flex flex-col min-h-0">
        {/* New analysis */}
        {onNewChat && (
          <div className="px-2 py-2 flex-shrink-0">
            <Button
              variant="ghost"
              className="w-full justify-center gap-2 text-foreground bg-primary/10 hover:bg-primary/20"
              onClick={onNewChat}
            >
              <FileEdit className="h-4 w-4" />
              New analysis
            </Button>
          </div>
        )}
        {/* Scrollable Chat History */}
        <SidebarGroup className="flex flex-col flex-1 min-h-0 pr-0">
          <SidebarGroupContent className="flex min-h-0 flex-1 flex-col overflow-y-auto sidebar-scrollbar pr-0">
            <TooltipProvider delayDuration={1500}>
              {chatHistory.length === 0 ? (
                <div className="flex flex-1 flex-col items-center justify-center gap-2 px-4 py-8 text-center text-sm text-muted-foreground">
                  <MessageSquare className="h-8 w-8 shrink-0 opacity-45" aria-hidden />
                  <p className="font-medium text-foreground/85">No analyses yet</p>
                  <p className="max-w-[14rem] text-xs leading-relaxed text-muted-foreground">
                    Start a new analysis to see history here.
                  </p>
                </div>
              ) : (
                dayGroups.map(({ day, chats }) => (
                  <div key={day} className="mb-3">
                    <div className="px-3 py-2 text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                      {day}
                    </div>
                    <SidebarMenu className="space-y-0.5">
                      {chats.map((chat) => (
                        <SidebarMenuItem key={chat.id} className="group/chat relative px-2">
                          <SidebarMenuButton
                            onClick={() => onSelectChat?.(chat.id)}
                            isActive={activeChatId === chat.id}
                            className="w-full justify-start gap-3 h-auto py-1.5 pl-3 pr-10"
                          >
                            <div className="flex-1 min-w-0">
                              {editingChatId === chat.id ? (
                                <input
                                  type="text"
                                  value={editingTitle}
                                  onChange={(e) => setEditingTitle(e.target.value)}
                                  onBlur={() => handleRenameSubmit(chat.id)}
                                  onKeyDown={(e) => handleRenameKeyDown(e, chat.id)}
                                  className="text-sm font-medium bg-transparent border border-primary rounded px-1 w-full"
                                  autoFocus
                                  onClick={(e) => e.stopPropagation()}
                                />
                              ) : (
                                <TruncatedTooltip text={chat.title} />
                              )}
                            </div>
                          </SidebarMenuButton>
                          <div className="absolute right-2 top-1/2 -translate-y-1/2 z-10">
                            <DropdownMenu>
                              <DropdownMenuTrigger asChild>
                                <Button
                                  variant="ghost"
                                  size="icon"
                                  className="h-6 w-6 opacity-0 group-hover/chat:opacity-100 transition-opacity"
                                  onClick={(e) => e.stopPropagation()}
                                >
                                  <MoreVertical className="h-4 w-4" />
                                </Button>
                              </DropdownMenuTrigger>
                              <DropdownMenuContent align="end" onClick={(e) => e.stopPropagation()}>
                                <DropdownMenuItem
                                  onClick={(e) => {
                                    e.stopPropagation()
                                    handleShareAsPdf(chat.id)
                                  }}
                                >
                                  <Share2 className="h-4 w-4 mr-2" />
                                  Share as PDF
                                </DropdownMenuItem>
                                <DropdownMenuItem
                                  onClick={(e) => {
                                    e.stopPropagation()
                                    handleRenameStart(chat.id, chat.title)
                                  }}
                                >
                                  <Pencil className="h-4 w-4 mr-2" />
                                  Rename
                                </DropdownMenuItem>
                                <DropdownMenuSeparator />
                                <DropdownMenuItem>
                                  <Archive className="h-4 w-4 mr-2" />
                                  Archive
                                </DropdownMenuItem>
                                <DropdownMenuSeparator />
                                {onDeleteChat && (
                                  <DropdownMenuItem
                                    className="text-destructive focus:text-destructive"
                                    onClick={(e) => {
                                      e.stopPropagation()
                                      onDeleteChat(chat.id)
                                    }}
                                  >
                                    <Trash2 className="h-4 w-4 mr-2" />
                                    Delete
                                  </DropdownMenuItem>
                                )}
                              </DropdownMenuContent>
                            </DropdownMenu>
                          </div>
                        </SidebarMenuItem>
                      ))}
                    </SidebarMenu>
                  </div>
                ))
              )}
            </TooltipProvider>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>

      {/* Fixed Bottom Section */}
      <SidebarFooter className="flex-shrink-0 flex flex-col gap-0 border-t border-border mt-auto">
        <NavUser
          user={userData}
        />
      </SidebarFooter>
    </Sidebar>
  )
}
