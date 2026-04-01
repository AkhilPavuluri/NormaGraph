/**
 * Streaming API client for the NormaGraph FastAPI backend
 * 
 * Implements Server-Sent Events (SSE) streaming for:
 * - Progressive status updates
 * - Token-by-token answer streaming
 * - Non-blocking UI updates
 */

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export interface StreamingQueryRequest {
  query: string
  conversation_history?: Array<{ role: string; content: string }>
  filters?: Record<string, any>
}

export interface StreamingEvent {
  type: 'status' | 'token' | 'metadata' | 'error' | 'done' | 'answer_chunk' | 'complete'
  stage?: 'classifying' | 'retrieving' | 'analyzing' | 'generating' | 'risk_analysis'
  message?: string
  content?: string
  data?: any
  error?: string
}

export interface StreamingCallbacks {
  onStatus?: (stage: string, message: string) => void
  onToken?: (token: string) => void
  onMetadata?: (metadata: {
    citations: any[]
    source_hierarchy: any
    risk_assessment: any
    confidence: number
  }) => void
  onError?: (error: string) => void
  onComplete?: () => void
}

/**
 * Stream query response from backend
 */
export async function streamQuery(
  request: StreamingQueryRequest,
  callbacks: StreamingCallbacks
): Promise<void> {
  // Try ADK streaming endpoint first, fallback to old endpoint
  const url = `${API_BASE_URL}/chat/stream`
  
  try {
    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(request),
    })

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`)
    }

    if (!response.body) {
      throw new Error('Response body is null')
    }

    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''

    while (true) {
      const { done, value } = await reader.read()

      if (done) {
        callbacks.onComplete?.()
        break
      }

      // Decode chunk and add to buffer
      buffer += decoder.decode(value, { stream: true })

      // Process complete SSE messages
      const lines = buffer.split('\n')
      buffer = lines.pop() || '' // Keep incomplete line in buffer

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          try {
            const data = JSON.parse(line.slice(6)) as StreamingEvent

            switch (data.type) {
              case 'status':
                if (data.message) {
                  callbacks.onStatus?.('generating', data.message)
                }
                break

              case 'answer_chunk':
                if (data.content) {
                  callbacks.onToken?.(data.content)
                }
                break

              case 'complete':
                if (data.data) {
                  callbacks.onMetadata?.({
                    citations: data.data.citations || [],
                    source_hierarchy: data.data.source_hierarchy || {},
                    risk_assessment: data.data.risk_assessment || {},
                    confidence: data.data.confidence || 0
                  })
                }
                callbacks.onComplete?.()
                break

              case 'error':
                callbacks.onError?.(data.message || data.error || 'Unknown error')
                break
            }
          } catch (e) {
            console.error('Error parsing SSE data:', e, line)
          }
        }
      }
    }
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : 'Unknown error'
    callbacks.onError?.(errorMessage)
    throw error
  }
}

/**
 * Non-streaming query (fallback)
 */
export async function queryAPI(request: StreamingQueryRequest): Promise<any> {
  // Try ADK endpoint first, fallback to old endpoint
  const url = `${API_BASE_URL}/chat`
  
  const response = await fetch(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(request),
  })

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`)
  }

  return response.json()
}

