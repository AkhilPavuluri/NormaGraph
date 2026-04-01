/**
 * Text normalization utilities for PDF snippet matching
 *
 * These functions mirror the backend normalization logic to ensure
 * consistent text matching between Qdrant chunks and PDF content.
 */

/**
 * Normalize text for snippet matching
 *
 * Applies the same transformations as the backend:
 * 1. Remove line-break hyphens (e.g., "govern-\nment" → "government")
 * 2. Collapse whitespace (including newlines) to single spaces
 * 3. Unicode normalization (NFC)
 * 4. Lowercase
 * 5. Trim
 */
export function normalizeText(text: string): string {
  if (!text) return ''

  let normalized = text

  // 1. Remove line-break hyphens
  normalized = normalized.replace(/-\s*\n\s*/g, '')

  // 2. Collapse all whitespace (including newlines) to single spaces
  normalized = normalized.replace(/\s+/g, ' ')

  // 3. Unicode normalization (NFC - Canonical Composition)
  normalized = normalized.normalize('NFC')

  // 4. Lowercase
  normalized = normalized.toLowerCase()

  // 5. Trim
  normalized = normalized.trim()

  return normalized
}

/**
 * Find the position of a normalized snippet within normalized text
 * Returns the character index, or -1 if not found
 */
export function findNormalizedSnippet(
  fullText: string,
  snippet: string
): number {
  const normalizedText = normalizeText(fullText)
  const normalizedSnippet = normalizeText(snippet)

  return normalizedText.indexOf(normalizedSnippet)
}

/**
 * Check if a normalized snippet exists in normalized text
 */
export function containsNormalizedSnippet(
  fullText: string,
  snippet: string
): boolean {
  return findNormalizedSnippet(fullText, snippet) !== -1
}

/**
 * Extract the original text segment that matches a normalized snippet
 * This is useful for highlighting the exact original text
 */
export function extractMatchingSegment(
  fullText: string,
  snippet: string
): { start: number; end: number; text: string } | null {
  const normalizedText = normalizeText(fullText)
  const normalizedSnippet = normalizeText(snippet)

  const index = normalizedText.indexOf(normalizedSnippet)
  if (index === -1) return null

  // This is a simplified approach - in practice, you'd need to map
  // normalized positions back to original positions accounting for
  // removed characters. For now, we return approximate positions.
  return {
    start: index,
    end: index + normalizedSnippet.length,
    text: fullText.slice(index, index + snippet.length),
  }
}

