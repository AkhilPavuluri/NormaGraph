"use client"

import { usePathname } from "next/navigation"
import { SidebarTrigger } from "@/components/ui/sidebar"

export function SidebarTriggerWrapper() {
  const pathname = usePathname()
  const isDocumentationPage = pathname?.startsWith("/documentation")

  if (isDocumentationPage) {
    // Hide sidebar trigger completely on documentation pages
    return null
  }

  return <SidebarTrigger className="-ml-1" />
}

