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

  it('renders both sport options', () => {
    renderWithRouter(<SportSelect />)
    expect(screen.getAllByText('Football').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Marathon').length).toBeGreaterThan(0)
  })

  it('renders sport subtitles', () => {
    renderWithRouter(<SportSelect />)
    expect(screen.getByText(/Injury risk/i)).toBeInTheDocument()
    expect(screen.getByText(/Endurance metrics/i)).toBeInTheDocument()
  })

  it('saves football choice to localStorage and navigates to /login', async () => {
    const { container } = renderWithRouter(<SportSelect />)
    const cards = container.querySelectorAll('.sport-card')
    expect(cards).toHaveLength(2)

    await userEvent.click(cards[0])
    expect(localStorage.getItem('selected_sport')).toBe('football')
    expect(mockNavigate).toHaveBeenCalledWith('/home')
  })

  it('saves marathon choice to localStorage and navigates to /login', async () => {
    const { container } = renderWithRouter(<SportSelect />)
    const cards = container.querySelectorAll('.sport-card')

    await userEvent.click(cards[1])
    expect(localStorage.getItem('selected_sport')).toBe('marathon')
    expect(mockNavigate).toHaveBeenCalledWith('/home')
  })
})
