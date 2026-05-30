import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect, vi, beforeEach } from 'vitest'

import SportSelect from '../SportSelect'
import { renderWithRouter } from '../../test/renderWithRouter'

const mockNavigate = vi.fn()

vi.mock('react-router-dom', async (orig) => {
  const actual = await orig()
  return { ...actual, useNavigate: () => mockNavigate }
})


describe('SportSelect page', () => {
  beforeEach(() => {
    mockNavigate.mockReset()
  })

  it('renders football sport option', () => {
    renderWithRouter(<SportSelect />)
    expect(screen.getAllByText('Football').length).toBeGreaterThan(0)
    expect(screen.queryByText('Marathon')).toBeNull()
  })

  it('renders football subtitle', () => {
    renderWithRouter(<SportSelect />)
    expect(screen.getByText(/Injury risk/i)).toBeInTheDocument()
  })

  it('saves football choice to localStorage and navigates to /home', async () => {
    const { container } = renderWithRouter(<SportSelect />)
    const cards = container.querySelectorAll('.sport-card')
    expect(cards).toHaveLength(1)

    await userEvent.click(cards[0])
    expect(localStorage.getItem('selected_sport')).toBe('football')
    expect(mockNavigate).toHaveBeenCalledWith('/home')
  })
})
