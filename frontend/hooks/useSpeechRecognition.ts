import { useState, useEffect, useRef, useCallback } from 'react'

export interface UseSpeechRecognitionReturn {
    isListening: boolean
    transcript: string
    interimTranscript: string
    startListening: () => void
    stopListening: () => void
    resetTranscript: () => void
    hasRecognition: boolean
    isSupported: boolean
    error: string | null
    isProcessing: boolean /* New state for backend processing */
}

export function useSpeechRecognition(): UseSpeechRecognitionReturn {
    const [isListening, setIsListening] = useState(false)
    const [transcript, setTranscript] = useState('')
    const [interimTranscript, setInterimTranscript] = useState('')
    const [error, setError] = useState<string | null>(null)
    const [isSupported, setIsSupported] = useState(false)
    const [isProcessing, setIsProcessing] = useState(false) /* Backend processing state */

    // Native Speech API refs
    const recognitionRef = useRef<any>(null)
    const retryTimeoutRef = useRef<NodeJS.Timeout | null>(null)
    const networkErrorCountRef = useRef(0)
    const maxNetworkRetries = 3

    // MediaRecorder fallback refs
    const mediaRecorderRef = useRef<MediaRecorder | null>(null)
    const audioChunksRef = useRef<Blob[]>([])

    // Detect browser support
    useEffect(() => {
        if (typeof window === 'undefined') return

        const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition

        if (SpeechRecognition) {
            setIsSupported(true)
            console.log('Speech Recognition API is supported') // Chrome/Edge
        } else if (navigator.mediaDevices) {
            // Fallback support via MediaRecorder
            setIsSupported(true)
            console.log('Speech Recognition API not found, falling back to MediaRecorder (Safari/Firefox)')
        } else {
            console.warn('No speech recognition or audio recording support found')
            setIsSupported(false)
        }

        // Cleanup function
        return () => {
            if (retryTimeoutRef.current) {
                clearTimeout(retryTimeoutRef.current)
            }
            if (recognitionRef.current) {
                recognitionRef.current.stop()
            }
            if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
                mediaRecorderRef.current.stop()
            }
        }
    }, [])

    // --- Strategy 1: Native Speech Recognition (Chrome/Edge) ---
    const startNativeListening = () => {
        const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition
        if (!SpeechRecognition) return false

        if (!recognitionRef.current) {
            try {
                const recognition = new SpeechRecognition()
                recognition.continuous = true
                recognition.interimResults = true
                recognition.lang = 'en-US'

                recognition.onstart = () => {
                    console.log('Native Speech recognition started')
                    setIsListening(true)
                    setError(null)
                    if (retryTimeoutRef.current) {
                        clearTimeout(retryTimeoutRef.current)
                        retryTimeoutRef.current = null
                    }
                }

                recognition.onend = () => {
                    console.log('Native Speech recognition ended')
                    // Only set isListening false if we didn't intend to stop (handled by stopListening)
                    // But for simplicity of this hook, we let existing logic handle it or just sync state
                    setIsListening(false)
                }

                recognition.onerror = (event: any) => {
                    console.error("Native Speech recognition error:", event.error)
                    const errorType = event.error
                    let errorMessage: string | null = null
                    let shouldStop = false

                    switch (errorType) {
                        case 'network':
                            errorMessage = 'Network error: Check connection.'
                            shouldStop = true
                            break
                        case 'no-speech':
                            errorMessage = null
                            shouldStop = false
                            break
                        case 'aborted':
                            errorMessage = null
                            shouldStop = false
                            break
                        case 'not-allowed':
                        case 'service-not-allowed':
                            errorMessage = 'Microphone permission denied.'
                            shouldStop = true
                            break
                        default:
                            errorMessage = `Error: ${errorType}`
                            shouldStop = false
                    }

                    if (errorMessage) setError(errorMessage)
                    if (shouldStop) {
                        setIsListening(false)
                        recognitionRef.current?.stop()
                    }
                }

                recognition.onresult = (event: any) => {
                    networkErrorCountRef.current = 0
                    let finalTranscriptChunk = ''
                    let currentInterim = ''

                    for (let i = event.resultIndex; i < event.results.length; ++i) {
                        if (event.results[i].isFinal) {
                            finalTranscriptChunk += event.results[i][0].transcript
                        } else {
                            currentInterim += event.results[i][0].transcript
                        }
                    }

                    if (finalTranscriptChunk) {
                        setTranscript(prev => prev + finalTranscriptChunk)
                    }
                    setInterimTranscript(currentInterim)
                }

                recognitionRef.current = recognition
            } catch (e) {
                console.error(e)
                return false
            }
        }

        try {
            recognitionRef.current.start()
            return true
        } catch (e) {
            console.error(e)
            return false
        }
    }

    const stopNativeListening = () => {
        if (recognitionRef.current) {
            recognitionRef.current.stop()
        }
    }

    // --- Strategy 2: MediaRecorder Fallback (Safari/Firefox) ---
    const startMediaRecording = async () => {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
            const mediaRecorder = new MediaRecorder(stream)
            mediaRecorderRef.current = mediaRecorder
            audioChunksRef.current = []

            mediaRecorder.ondataavailable = (event) => {
                if (event.data.size > 0) {
                    audioChunksRef.current.push(event.data)
                }
            }

            mediaRecorder.onstart = () => {
                console.log('MediaRecorder started')
                setIsListening(true)
                setError(null)
            }

            mediaRecorder.onstop = async () => {
                console.log('MediaRecorder stopped')
                setIsListening(false)

                // Process audio
                const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' })
                await sendAudioToBackend(audioBlob)

                // Stop all tracks to release mic
                stream.getTracks().forEach(track => track.stop())
            }

            mediaRecorder.start()
            return true
        } catch (e: any) {
            console.error("MediaRecorder error:", e)
            setError(e.message || "Failed to start recording")
            return false
        }
    }

    const stopMediaRecording = () => {
        if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
            mediaRecorderRef.current.stop()
        }
    }

    const sendAudioToBackend = async (audioBlob: Blob) => {
        setIsProcessing(true)
        try {
            const formData = new FormData()
            // Backend expects 'file'
            formData.append('file', audioBlob, 'recording.webm')

            const response = await fetch('http://localhost:8000/api/transcribe', {
                method: 'POST',
                body: formData,
            })

            if (!response.ok) {
                throw new Error(`Server error: ${response.status}`)
            }

            const data = await response.json()
            if (data.text) {
                setTranscript(prev => prev + (prev ? ' ' : '') + data.text)
            }
        } catch (e: any) {
            console.error("Transcription upload failed:", e)
            setError("Transcription failed. Please try again.")
        } finally {
            setIsProcessing(false)
        }
    }

    // --- Unified Interface ---

    const startListening = useCallback(async () => {
        if (isListening) return

        setError(null)
        setTranscript('')
        setInterimTranscript('')

        // Try Native first
        const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition
        if (SpeechRecognition) {
            const success = startNativeListening()
            if (success) return;
        }

        if (navigator.mediaDevices) {
            await startMediaRecording()
        } else {
            setError("Speech recognition not compatible with this browser.")
        }

    }, [isListening])

    const stopListening = useCallback(() => {
        if (!isListening) return

        // Stop whichever is active
        if (recognitionRef.current) {
            stopNativeListening()
        }
        if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
            stopMediaRecording()
        }
    }, [isListening])

    const resetTranscript = useCallback(() => {
        setTranscript('')
        setInterimTranscript('')
    }, [])

    return {
        isListening,
        transcript,
        interimTranscript,
        startListening,
        stopListening,
        resetTranscript,
        hasRecognition: isSupported,
        isSupported,
        error,
        isProcessing
    }
}
