"use client"

import { useState, useEffect } from "react"
import { usePathname, useRouter } from "next/navigation"
import { ChevronDown, Layers, MoreHorizontal, Settings, HelpCircle, Search, Download, Share, Archive, Cloud, Server, Wifi, WifiOff, RefreshCw, ArrowLeft } from "lucide-react"
import { Separator } from "@/components/ui/separator"
import { SidebarTriggerWrapper } from "@/components/sidebar-trigger-wrapper"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
  DropdownMenuSeparator,
  DropdownMenuLabel,
} from "@/components/ui/dropdown-menu"
import { Button } from "@/components/ui/button"
import { AIModel, OllamaModel, CloudModel } from "@/lib/models"
import { modelService } from "@/lib/modelService"
import { ThemeToggle } from "@/components/ThemeToggle"
import { SettingsDialog } from "@/components/SettingsDialog"

interface SiteHeaderProps {
  selectedModel?: string
  onModelChange?: (model: string) => void
}

export function SiteHeader({ selectedModel = "backend-default", onModelChange }: SiteHeaderProps) {
  const pathname = usePathname()
  const router = useRouter()
  const isDocumentationPage = pathname?.startsWith("/documentation")
  const [models, setModels] = useState<AIModel[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [isOllamaConnected, setIsOllamaConnected] = useState(false)
  const [isRefreshing, setIsRefreshing] = useState(false)

  useEffect(() => {
    const loadModels = async () => {
      setIsLoading(true)
      try {
        const [allModels, ollamaConnected] = await Promise.all([
          modelService.getAllModels(),
          modelService.checkOllamaConnection()
        ])
        setModels(allModels)
        setIsOllamaConnected(ollamaConnected)
      } catch (error) {
        console.error('Error loading models:', error)
        try {
          const cloud = await modelService.getCloudModels()
          setModels(cloud)
        } catch {
          setModels([])
        }
      } finally {
        setIsLoading(false)
      }
    }

    loadModels()
  }, [])

  const refreshModels = async () => {
    setIsRefreshing(true)
    try {
      const [allModels, ollamaConnected] = await Promise.all([
        modelService.refreshModels(),
        modelService.checkOllamaConnection()
      ])
      setModels(allModels)
      setIsOllamaConnected(ollamaConnected)
    } catch (error) {
      console.error('Error refreshing models:', error)
      try {
        const cloud = await modelService.getCloudModels()
        setModels(cloud)
      } catch {
        setModels([])
      }
    } finally {
      setIsRefreshing(false)
    }
  }

  // Prioritize cloud models for default selection
  const currentModel = models.find(model => model.id === selectedModel) || 
    models.find(model => model.category === 'cloud' && model.isAvailable) ||
    models.find(model => model.isAvailable) || 
    models[0]

  return (
    <header className="site-header group-has-data-[collapsible=icon]/sidebar-wrapper:h-12 flex h-12 shrink-0 items-center gap-2 transition-[width,height] ease-linear sticky top-0 z-30 bg-background border-b border-border">
      <div className="flex w-full items-center justify-between gap-1 px-4 lg:gap-2 lg:px-6">
        {/* Left: sidebar, model selector, or back to analysis */}
        <div className="flex items-center gap-2">
          {!isDocumentationPage && <SidebarTriggerWrapper />}
          {!isDocumentationPage && (
            <Separator
              orientation="vertical"
              className="mx-2 data-[orientation=vertical]:h-4"
            />
          )}
          
          {isDocumentationPage ? (
            <Button
              variant="ghost"
              className="h-8 px-3 gap-2"
              onClick={() => router.push("/chat")}
            >
              <ArrowLeft className="h-4 w-4" />
              <span className="text-sm font-medium">Back to analysis</span>
            </Button>
          ) : (
            /* Model Selector */
            <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button
                variant="outline"
                className="h-9 gap-2 rounded-lg border-border/70 bg-background/90 px-2 pl-2 pr-2.5 shadow-sm transition-colors hover:border-primary/35 hover:bg-muted/45"
              >
                <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-md bg-gradient-to-br from-primary/18 to-primary/10 text-primary ring-1 ring-border/60 dark:from-primary/22 dark:to-primary/14">
                  <Layers className="h-4 w-4" aria-hidden />
                </span>
                <span className="min-w-0 max-w-[140px] truncate text-left text-sm font-medium sm:max-w-[220px]">
                  {isLoading ? 'Loading…' : currentModel?.name || 'Model'}
                </span>
                <ChevronDown className="h-3.5 w-3.5 shrink-0 opacity-45" aria-hidden />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="start" className="w-80 premium-scrollbar max-h-96">
              {/* Refresh Button */}
              <div className="px-3 py-2 border-b">
                <Button 
                  variant="outline" 
                  size="sm" 
                  onClick={refreshModels}
                  disabled={isRefreshing}
                  className="w-full"
                >
                  <RefreshCw className={`h-4 w-4 mr-2 ${isRefreshing ? 'animate-spin' : ''}`} />
                  {isRefreshing ? 'Refreshing...' : 'Refresh Models'}
                </Button>
              </div>
              
              {/* Cloud Models Section - Show first and prominently */}
              {models.filter(model => model.category === 'cloud').length > 0 && (
                <>
                  <DropdownMenuLabel className="flex items-center gap-2 px-3 py-2">
                    <Cloud className="h-4 w-4" />
                    <span>Cloud Models</span>
                    <span className="rounded bg-primary/12 px-2 py-0.5 text-xs font-medium text-primary">
                      Recommended
                    </span>
                  </DropdownMenuLabel>
                  {models
                    .filter((model): model is CloudModel => model.category === 'cloud')
                    .map((model) => (
                      <DropdownMenuItem
                        key={model.id}
                        onClick={() => onModelChange?.(model.id)}
                        className="flex flex-col items-start gap-1 p-3"
                      >
                        <div className="flex items-center gap-2 w-full">
                          <Cloud className="h-4 w-4" />
                          <span className="font-medium">{model.name}</span>
                          <span className="rounded bg-primary/12 px-2 py-0.5 text-xs font-medium text-primary">
                            Available
                          </span>
                        </div>
                        <div className="flex items-center gap-2 text-xs text-muted-foreground">
                          <span>{model.description}</span>
                          {model.pricing?.input && <span>• {model.pricing.input}</span>}
                        </div>
                      </DropdownMenuItem>
                    ))}
                </>
              )}

              {/* Ollama Models Section - Show after cloud models */}
              {models.filter(model => model.category === 'ollama').length > 0 && (
                <>
                  {models.filter(model => model.category === 'cloud').length > 0 && <DropdownMenuSeparator />}
                  <DropdownMenuLabel className="flex items-center gap-2 px-3 py-2">
                    <Server className="h-4 w-4" />
                    <span>Local Models (Ollama)</span>
                    {isOllamaConnected ? (
                      <Wifi className="h-3 w-3 text-primary" />
                    ) : (
                      <WifiOff className="h-3 w-3 text-muted-foreground" />
                    )}
                  </DropdownMenuLabel>
                  {models
                    .filter((model): model is OllamaModel => model.category === 'ollama')
                    .map((model) => (
                      <DropdownMenuItem
                        key={model.id}
                        onClick={() => onModelChange?.(model.id)}
                        className="flex flex-col items-start gap-1 p-3"
                      >
                        <div className="flex items-center gap-2 w-full">
                          <Server className="h-4 w-4" />
                          <span className="font-medium">{model.name}</span>
                          <span className="rounded bg-primary/12 px-2 py-0.5 text-xs font-medium text-primary">
                            Local
                          </span>
                        </div>
                        <div className="flex items-center gap-2 text-xs text-muted-foreground">
                          <span>{model.description}</span>
                          {model.size && <span>• {model.size}</span>}
                        </div>
                      </DropdownMenuItem>
                    ))}
                </>
              )}

              {/* No models available message */}
              {models.length === 0 && !isLoading && (
                <div className="px-3 py-4 text-center text-sm text-muted-foreground">
                  <p>No models available</p>
                  <p className="text-xs mt-1">
                    Configure API keys in Settings to use cloud models
                  </p>
                </div>
              )}
            </DropdownMenuContent>
          </DropdownMenu>
          )}
        </div>

        {/* Right side - Theme toggle, and 3-dot menu */}
        <div className="flex items-center gap-2">
          <ThemeToggle />
          <Separator
            orientation="vertical"
            className="mx-2 data-[orientation=vertical]:h-4"
          />
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" size="icon" className="h-8 w-8">
                <MoreHorizontal className="h-4 w-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-56 premium-scrollbar">
              <SettingsDialog>
                <DropdownMenuItem onSelect={(e) => e.preventDefault()}>
                  <Settings className="h-4 w-4 mr-2" />
                  Settings
                </DropdownMenuItem>
              </SettingsDialog>
              <DropdownMenuItem>
                <HelpCircle className="h-4 w-4 mr-2" />
                Get Help
              </DropdownMenuItem>
              <DropdownMenuItem>
                <Search className="h-4 w-4 mr-2" />
                Search
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem>
                <Download className="h-4 w-4 mr-2" />
                Export Chat
              </DropdownMenuItem>
              <DropdownMenuItem>
                <Share className="h-4 w-4 mr-2" />
                Share Chat
              </DropdownMenuItem>
              <DropdownMenuItem>
                <Archive className="h-4 w-4 mr-2" />
                Archive Chat
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </div>
    </header>
  )
}
