/** Logs only in development — keeps production builds quiet. */
export function devLog(...args: unknown[]): void {
  if (process.env.NODE_ENV === 'development') {
    console.log(...args)
  }
}
