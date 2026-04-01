/**
 * PDF Viewer API Service
 *
 * Intended endpoints: signed GCS URL and snippet location. This build returns
 * stubs unless you implement the corresponding routes on the API.
 */

import { devLog } from './devLog'

export interface PdfUrlResponse {
  signedUrl: string
  expiresAt: string
  doc_id: string
  pdf_filename: string
}

export interface LocateSnippetRequest {
  doc_id: string
  snippet: string
}

export interface LocateSnippetResponse {
  page: number | null
  found: boolean
  normalizedSnippet: string
  matchConfidence: 'exact' | 'none'
  totalPages: number
  error?: string
}

/** Stub: wire to your backend for real signed URLs. */
export async function getPdfUrl(
  docId: string,
  expirationMinutes: number = 60,
  sourceHint?: string
): Promise<PdfUrlResponse> {
  devLog('getPdfUrl stub:', docId)

  return {
    signedUrl: '',
    expiresAt: new Date(Date.now() + expirationMinutes * 60 * 1000).toISOString(),
    doc_id: docId,
    pdf_filename: 'document.pdf'
  }
}

/** Stub: wire to your backend for real snippet search. */
export async function locateSnippet(
  docId: string,
  snippet: string
): Promise<LocateSnippetResponse> {
  devLog('locateSnippet stub:', { docId, snippet })

  return {
    page: null,
    found: false,
    normalizedSnippet: snippet,
    matchConfidence: 'none',
    totalPages: 0,
    error: 'PDF endpoints not wired in this build'
  }
}

/**
 * Combined function to get PDF URL and locate snippet in one call
 * Useful for opening a PDF directly to a specific page with highlighting
 */
export async function openPdfAtSnippet(
  docId: string,
  snippet: string
): Promise<{
  pdfUrl: string
  page: number | null
  found: boolean
  expiresAt: string
}> {
  const [pdfUrlData, snippetData] = await Promise.all([
    getPdfUrl(docId),
    locateSnippet(docId, snippet),
  ])

  return {
    pdfUrl: pdfUrlData.signedUrl,
    page: snippetData.page,
    found: snippetData.found,
    expiresAt: pdfUrlData.expiresAt,
  }
}

