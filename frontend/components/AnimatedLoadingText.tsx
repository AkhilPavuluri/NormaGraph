'use client'

import { useEffect, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'

interface AnimatedLoadingTextProps {
  steps: string[]
  interval?: number
  className?: string
}

export function AnimatedLoadingText({ 
  steps, 
  interval = 1800,
  className = '' 
}: AnimatedLoadingTextProps) {
  const [currentStepIndex, setCurrentStepIndex] = useState(0)
  const [displayText, setDisplayText] = useState(steps[0] || '')
  const [isAnimating, setIsAnimating] = useState(false)
  const [glowDirection, setGlowDirection] = useState<'left' | 'right'>('right')

  useEffect(() => {
    if (steps.length === 0) return

    let stepIndex = 0
    const stepInterval = setInterval(() => {
      setIsAnimating(true)
      
      // Fade out and slide up current text
      setTimeout(() => {
        stepIndex = (stepIndex + 1) % steps.length
        setCurrentStepIndex(stepIndex)
        setDisplayText(steps[stepIndex])
        setIsAnimating(false)
        // Alternate glow direction
        setGlowDirection(prev => prev === 'right' ? 'left' : 'right')
      }, 400) // Transition duration
    }, interval)

    return () => clearInterval(stepInterval)
  }, [steps, interval])

  return (
    <div className={`relative ${className}`}>
      <div className="flex items-center gap-3">
        {/* Premium Framer Motion Spinner */}
        <div className="relative flex-shrink-0 w-6 h-6 flex items-center justify-center">
          <motion.div
            className="absolute inset-0 rounded-full border-2 border-primary/30"
            animate={{
              rotate: 360,
            }}
            transition={{
              duration: 1.5,
              repeat: Infinity,
              ease: "linear"
            }}
          />
          <motion.div
            className="absolute inset-0 rounded-full border-2 border-transparent border-t-primary"
            animate={{
              rotate: 360,
            }}
            transition={{
              duration: 1,
              repeat: Infinity,
              ease: "linear"
            }}
          />
          <motion.div
            className="absolute w-2 h-2 rounded-full bg-primary"
            animate={{
              scale: [1, 1.2, 1],
              opacity: [0.6, 1, 0.6],
            }}
            transition={{
              duration: 1.5,
              repeat: Infinity,
              ease: "easeInOut"
            }}
          />
        </div>
        
        {/* Shiny animated text with Framer Motion transitions */}
        <div className="relative overflow-hidden min-h-[1.5rem] flex items-center">
          <AnimatePresence mode="wait">
            <motion.span
              key={displayText}
              initial={{ opacity: 0, y: 10, scale: 0.95 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: -10, scale: 0.95 }}
              transition={{
                duration: 0.4,
                ease: [0.4, 0, 0.2, 1]
              }}
              className={`shiny-text-controlled inline-block`}
              data-direction={glowDirection}
            >
              {displayText}
            </motion.span>
          </AnimatePresence>
        </div>
      </div>
    </div>
  )
}
