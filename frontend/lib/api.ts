import { devLog } from './devLog'

export interface DraftContext {
  active_draft_id?: string | null
  active_draft_content?: string
  all_drafts?: Array<{ id: string; title: string; content: string }>
}

export interface QueryRequest {
  query: string
  simulate_failure?: boolean
  mode?: string
  internet_enabled?: boolean
  conversation_history?: Array<{ role: string; content: string }>
  draft_context?: DraftContext
  filters?: Record<string, unknown>
}

export interface Citation {
  docId: string
  page: number
  span: string
}

export interface RetrievalResult {
  dense: string[]
  sparse: string[]
}

export interface ProcessingTrace {
  language: string
  retrieval: RetrievalResult
  kg_traversal: string
  controller_iterations: number
}

export interface QueryResponse {
  answer: string
  citations: Citation[]
  processing_trace: ProcessingTrace
  risk_assessment: string
  source_hierarchy?: unknown
  confidence?: number
  reasoning?: unknown
  timeline?: unknown
  error?: {
    code: string
    message: string
    details?: any
  }
}

// Backend API integration
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export async function queryAPI(request: QueryRequest): Promise<QueryResponse> {
  devLog('QueryAPI called:', request)
  
  try {
    const response = await fetch(`${API_BASE_URL}/query`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        query: request.query,
        conversation_history: request.conversation_history,
        filters: request.filters
      }),
    })

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`)
    }

    const data = await response.json()
    
    // Convert backend response to frontend format
    return {
      answer: data.answer || '',
      citations: data.citations || [],
      processing_trace: data.processing_trace || {
        language: 'en',
        retrieval: { dense: [], sparse: [] },
        kg_traversal: '',
        controller_iterations: 0
      },
      risk_assessment: data.risk_assessment?.level || 'low',
      source_hierarchy: data.source_hierarchy,
      confidence: data.confidence,
      reasoning: data.reasoning,
      timeline: data.timeline
    }
  } catch (error) {
    console.error('Query API error:', error)
    throw error
  }
}


export async function getSystemStatus(): Promise<any> {
  try {
    const response = await fetch(`${API_BASE_URL}/health`)
    if (!response.ok) {
      return { status: 'offline', message: 'Backend API unavailable' }
    }
    return await response.json()
  } catch (error) {
    console.error('Health check error:', error)
    return { status: 'offline', message: 'Backend API unavailable' }
  }
}

export async function scrapeUrl(url: string, method: string = 'auto'): Promise<any> {
  devLog('scrapeUrl stub (not wired to backend):', url)
  return { success: false, message: 'URL scraping is not wired in this build' }
}

export async function getDocument(documentId: string): Promise<any> {
  devLog('getDocument stub (not wired to backend):', documentId)
  return { success: false, message: 'Document fetch is not wired in this build' }
}

export async function submitFeedback(
  query: string,
  response: string,
  rating: number,
  comments?: string
): Promise<any> {
  devLog('submitFeedback stub:', { query, rating, comments })
  return { success: true, message: 'Feedback not sent to server in this build' }
}

export async function queryModelDirect(request: QueryRequest): Promise<QueryResponse> {
  return queryAPI(request)
}


export async function queryWithFiles(
  query: string,
  files: File[],
  mode: string = 'qa',
  internet_enabled: boolean = false,
  conversation_history?: Array<{ role: string; content: string }>,
  draft_context?: DraftContext
): Promise<QueryResponse> {
  devLog('queryWithFiles stub:', { query, fileCount: files.length, mode, internet_enabled })

  return {
    answer: 'File upload to the policy backend is not wired in this build. Use the text query flow with the API running.',
    citations: [],
    processing_trace: {
      language: 'en',
      retrieval: { dense: [], sparse: [] },
      kg_traversal: '',
      controller_iterations: 0
    },
    risk_assessment: 'low'
  }
}

export interface AIEditDraftRequest {
  draft: string
  instruction: string
}

export interface AIEditDraftResponse {
  editedDraft: string
}

export async function aiEditDraft(request: AIEditDraftRequest): Promise<AIEditDraftResponse> {
  devLog('aiEditDraft stub:', { instruction: request.instruction, draftLength: request.draft.length })

  return {
    editedDraft: request.draft
  }
}

export async function generateChatTitle(question: string, response: string): Promise<string> {
  devLog('generateChatTitle (local fallback)')
  // Extract meaningful keywords from question as fallback
  const keywords = question.split(/\s+/).filter(w => w.length > 3).slice(0, 3)
  return keywords.length > 0 ? keywords.join(' ').replace(/[^\w\s]/g, '') : 'New analysis'
}