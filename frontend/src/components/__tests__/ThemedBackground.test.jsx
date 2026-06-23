import { render, screen } from '@testing-library/react'
import { describe, it, expect } from 'vitest'

import ThemedBackground from '../ThemedBackground'

describe('ThemedBackground', () => {
  it('exposes the requested variant', () => {
    render(<ThemedBackground variant="strength" />)
    expect(screen.getByTestId('themed-bg')).toHaveAttribute('data-variant', 'strength')
  })

  it('falls back gracefully for an unknown variant', () => {
    render(<ThemedBackground variant="does-not-exist" />)
    const bg = screen.getByTestId('themed-bg')
    expect(bg).toBeInTheDocument()
    // unknown variant still renders the default glyph set
    expect(bg.querySelectorAll('svg').length).toBeGreaterThan(1)
  })

  it('is decorative and non-interactive', () => {
    render(<ThemedBackground variant="wellness" />)
    const bg = screen.getByTestId('themed-bg')
    expect(bg).toHaveAttribute('aria-hidden', 'true')
    expect(bg.className).toContain('pointer-events-none')
    // 1 watermark + 7 floating slots
    expect(bg.querySelectorAll('svg').length).toBe(8)
  })
})
