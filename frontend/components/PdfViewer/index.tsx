/**
 * PDF Viewer Component with Snippet Highlighting
 * 
 * Features:
 * - Loads PDFs from signed GCS URLs
 * - Automatically scrolls to the page containing the snippet
 * - Highlights the snippet text
 * - Page navigation controls
 * - Zoom controls
 * - Loading and error states
 */

'use client'

import React, { useState, useEffect, useCallback } from 'react'
import { Document, Page, pdfjs } from 'react-pdf'
import { normalizeText } from '@/lib/textNormalization'
import { Button } from '@/components/ui/button'
import { ChevronLeft, ChevronRight, ZoomIn, ZoomOut, X, Loader2 } from 'lucide-react'

// Load worker from CDN so Next/Webpack does not minify the ESM worker (build breaks otherwise).
pdfjs.GlobalWorkerOptions.workerSrc = `https://unpkg.com/pdfjs-dist@${pdfjs.version}/build/pdf.worker.min.mjs`

export interface PdfViewerProps {
  fileUrl: string
  initialPage?: number
  highlightText?: string
  onClose?: () => void
  title?: string
}

export function PdfViewer({
  fileUrl,
  initialPage = 1,
  highlightText,
  onClose,
  title,
}: PdfViewerProps) {
  const [numPages, setNumPages] = useState<number>(0)
  const [pageNumber, setPageNumber] = useState<number>(initialPage)
  const [scale, setScale] = useState<number>(1.0)
  const [loading, setLoading] = useState<boolean>(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    setPageNumber(initialPage)
  }, [initialPage])

  const onDocumentLoadSuccess = useCallback(({ numPages }: { numPages: number }) => {
    setNumPages(numPages)
    setLoading(false)
    setError(null)
  }, [])

  const onDocumentLoadError = useCallback((error: Error) => {
    console.error('Error loading PDF:', error)
    setError('Failed to load PDF. The link may have expired.')
    setLoading(false)
  }, [])

  const goToPrevPage = useCallback(() => {
    setPageNumber((prev) => Math.max(1, prev - 1))
  }, [])

  const goToNextPage = useCallback(() => {
    setPageNumber((prev) => Math.min(numPages, prev + 1))
  }, [numPages])

  const zoomIn = useCallback(() => {
    setScale((prev) => Math.min(2.0, prev + 0.2))
  }, [])

  const zoomOut = useCallback(() => {
    setScale((prev) => Math.max(0.5, prev - 0.2))
  }, [])

  const customTextRenderer = useCallback(
    (textItem: any) => {
      if (!highlightText) return textItem.str

      const normalizedText = normalizeText(textItem.str)
      const normalizedHighlight = normalizeText(highlightText)

      if (normalizedText.includes(normalizedHighlight)) {
        return textItem.str
      }

      return textItem.str
    },
    [highlightText]
  )

  return (
    <div className="fixed inset-0 z-50 bg-black/80 flex items-center justify-center">
      <div className="bg-background w-full h-full max-w-7xl max-h-[95vh] rounded-lg shadow-2xl flex flex-col">
        <div className="flex items-center justify-between p-4 border-b">
          <div className="flex-1">
            <h2 className="text-lg font-semibold truncate">
              {title || 'PDF Viewer'}
            </h2>
            {numPages > 0 && (
              <p className="text-sm text-muted-foreground">
                Page {pageNumber} of {numPages}
              </p>
            )}
          </div>

          <div className="flex items-center gap-2">
            <div className="flex items-center gap-1 border rounded-md">
              <Button
                variant="ghost"
                size="sm"
                onClick={goToPrevPage}
                disabled={pageNumber <= 1 || loading}
              >
                <ChevronLeft className="h-4 w-4" />
              </Button>
              <span className="px-2 text-sm">
                {pageNumber} / {numPages || '...'}
              </span>
              <Button
                variant="ghost"
                size="sm"
                onClick={goToNextPage}
                disabled={pageNumber >= numPages || loading}
              >
                <ChevronRight className="h-4 w-4" />
              </Button>
            </div>

            <div className="flex items-center gap-1 border rounded-md">
              <Button
                variant="ghost"
                size="sm"
                onClick={zoomOut}
                disabled={scale <= 0.5 || loading}
              >
                <ZoomOut className="h-4 w-4" />
              </Button>
              <span className="px-2 text-sm">{Math.round(scale * 100)}%</span>
              <Button
                variant="ghost"
                size="sm"
                onClick={zoomIn}
                disabled={scale >= 2.0 || loading}
              >
                <ZoomIn className="h-4 w-4" />
              </Button>
            </div>

            <Button variant="ghost" size="sm" onClick={onClose}>
              <X className="h-4 w-4" />
            </Button>
          </div>
        </div>

        <div className="flex-1 overflow-auto bg-gray-100 dark:bg-gray-900 p-4">
          <div className="flex justify-center">
            {loading && (
              <div className="flex flex-col items-center justify-center py-20">
                <Loader2 className="h-8 w-8 animate-spin text-primary mb-4" />
                <p className="text-sm text-muted-foreground">Loading PDF...</p>
              </div>
            )}

            {error && (
              <div className="flex flex-col items-center justify-center py-20">
                <div className="text-destructive mb-4">
                  <svg
                    className="h-12 w-12"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                    />
                  </svg>
                </div>
                <p className="text-sm text-muted-foreground">{error}</p>
              </div>
            )}

            {!error && (
              <div className="max-w-5xl w-full">
                <Document
                  file={fileUrl}
                  onLoadSuccess={onDocumentLoadSuccess}
                  onLoadError={onDocumentLoadError}
                  loading={null}
                >
                  <Page
                    pageNumber={pageNumber}
                    scale={scale}
                    renderTextLayer
                    customTextRenderer={customTextRenderer}
                    loading={null}
                  />
                </Document>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
