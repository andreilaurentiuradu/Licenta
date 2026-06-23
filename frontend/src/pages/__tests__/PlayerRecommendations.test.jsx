import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect, vi, beforeEach } from 'vitest'

import PlayerRecommendations from '../PlayerRecommendations'
import { renderWithRouter } from '../../test/renderWithRouter'
import * as api from '../../api/players'

vi.mock('react-router-dom', async (orig) => {
  const actual = await orig()
  return { ...actual, useParams: () => ({ id: 'player-uid-1' }) }
})

vi.mock('../../api/players', () => ({
  getRecommendations:     vi.fn(),
  acceptRecommendation:   vi.fn(),
  refuseRecommendation:   vi.fn(),
  completeRecommendation: vi.fn(),
  restoreRecommendation:  vi.fn(),
}))

const DATA = {
  injury_risk: 'high',
  fl_probability: 0.9,
  ai_enabled: false,
  active: [
    { id: 1, category: 'Injury Prevention', priority: 'high', text: 'Do warmups.', status: 'pending' },
    { id: 2, category: 'Wellness',           priority: 'low',  text: 'Sleep more.', status: 'pending' },
  ],
  history: [],
}

describe('PlayerRecommendations page', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    api.getRecommendations.mockResolvedValue({ data: DATA })
  })

  it('renders active recommendations and the FL risk label', async () => {
    renderWithRouter(<PlayerRecommendations />)
    await waitFor(() => expect(screen.getByText('Do warmups.')).toBeInTheDocument())
    expect(screen.getByText('Sleep more.')).toBeInTheDocument()
    expect(screen.getByText(/High risk/i)).toBeInTheDocument()
  })

  it('accept marks the recommendation as accepted', async () => {
    api.acceptRecommendation.mockResolvedValue({ data: { ...DATA.active[0], status: 'accepted' } })
    renderWithRouter(<PlayerRecommendations />)
    await waitFor(() => screen.getByText('Do warmups.'))

    await userEvent.click(screen.getAllByRole('button', { name: /Accept/i })[0])
    await waitFor(() => {
      expect(api.acceptRecommendation).toHaveBeenCalledWith('player-uid-1', 1)
      expect(screen.getByText(/Accepted/i)).toBeInTheDocument()
    })
  })

  it('complete moves the item to history and adds a same-category replacement', async () => {
    api.completeRecommendation.mockResolvedValue({
      data: {
        item: { ...DATA.active[0], status: 'completed', updated_at: '2026-06-20T10:00:00' },
        replacement: { id: 7, category: 'Injury Prevention', priority: 'medium', text: 'Stretch daily.', status: 'pending' },
      },
    })
    renderWithRouter(<PlayerRecommendations />)
    await waitFor(() => screen.getByText('Do warmups.'))

    await userEvent.click(screen.getAllByRole('button', { name: /Mark complete/i })[0])
    await waitFor(() => {
      expect(api.completeRecommendation).toHaveBeenCalledWith('player-uid-1', 1)
      expect(screen.getByText('Stretch daily.')).toBeInTheDocument()  // replacement in active
      expect(screen.getByText(/History/i)).toBeInTheDocument()
    })
  })

  it('refuse moves the item to history and adds a same-category replacement', async () => {
    api.refuseRecommendation.mockResolvedValue({
      data: {
        item: { ...DATA.active[0], status: 'refused' },
        replacement: { id: 3, category: 'Injury Prevention', priority: 'medium', text: 'New advice.', status: 'pending' },
      },
    })
    renderWithRouter(<PlayerRecommendations />)
    await waitFor(() => screen.getByText('Do warmups.'))

    await userEvent.click(screen.getAllByRole('button', { name: /Refuse$/i })[0])
    await waitFor(() => {
      expect(api.refuseRecommendation).toHaveBeenCalledWith('player-uid-1', 1)
      expect(screen.getByText('New advice.')).toBeInTheDocument()   // replacement in active
      expect(screen.getByText(/History/i)).toBeInTheDocument()      // refused item moved to history
    })
  })

  it('polls the server on an interval to stay in sync', async () => {
    vi.useFakeTimers()
    try {
      renderWithRouter(<PlayerRecommendations />)
      await vi.advanceTimersByTimeAsync(0)          // flush the initial load
      expect(api.getRecommendations).toHaveBeenCalledTimes(1)

      await vi.advanceTimersByTimeAsync(15000)      // one poll tick
      expect(api.getRecommendations).toHaveBeenCalledTimes(2)
    } finally {
      vi.useRealTimers()
    }
  })

  it('separates Completed/Refused into collapsible sections and restores an item', async () => {
    api.getRecommendations.mockResolvedValue({
      data: {
        ...DATA, active: [],
        history: [
          { id: 5, category: 'Nutrition', priority: 'low', text: 'Ate well.',  status: 'completed', updated_at: '2026-06-19T08:00:00' },
          { id: 6, category: 'Recovery',  priority: 'low', text: 'Skipped it.', status: 'refused',   updated_at: '2026-06-18T08:00:00' },
        ],
      },
    })
    api.restoreRecommendation.mockResolvedValue({
      data: { id: 5, category: 'Nutrition', priority: 'low', text: 'Ate well.', status: 'pending' },
    })
    renderWithRouter(<PlayerRecommendations />)

    // both section headers render; items are collapsed (hidden) by default
    await waitFor(() => screen.getByRole('button', { name: /Completed/i }))
    expect(screen.getByRole('button', { name: /Refused/i })).toBeInTheDocument()
    expect(screen.queryByText('Ate well.')).not.toBeInTheDocument()

    // expand Completed → item shows, then restore it
    await userEvent.click(screen.getByRole('button', { name: /Completed/i }))
    expect(screen.getByText('Ate well.')).toBeInTheDocument()

    await userEvent.click(screen.getByRole('button', { name: /Restore/i }))
    await waitFor(() => {
      expect(api.restoreRecommendation).toHaveBeenCalledWith('player-uid-1', 5)
      expect(screen.getByText('Ate well.')).toBeInTheDocument()  // now back in active
    })
  })
})
