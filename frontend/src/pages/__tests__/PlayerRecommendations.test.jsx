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
  getRecommendations:      vi.fn(),
  generateRecommendations: vi.fn(),
  acceptRecommendation:    vi.fn(),
  refuseRecommendation:    vi.fn(),
  completeRecommendation:  vi.fn(),
}))

const DATA = {
  injury_risk: 'high',
  fl_probability: 0.9,
  ai_enabled: false,
  active: [
    { id: 1, category: 'Injury Prevention', priority: 'high', text: 'Do warmups.', status: 'pending' },
    { id: 2, category: 'Wellness',           priority: 'low',  text: 'Sleep more.', status: 'pending' },
  ],
  completed: [],
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

  it('complete moves the recommendation to the completed history', async () => {
    api.completeRecommendation.mockResolvedValue({
      data: { ...DATA.active[0], status: 'completed', updated_at: '2026-06-20T10:00:00' },
    })
    renderWithRouter(<PlayerRecommendations />)
    await waitFor(() => screen.getByText('Do warmups.'))

    await userEvent.click(screen.getAllByRole('button', { name: /Mark complete/i })[0])
    await waitFor(() => {
      expect(api.completeRecommendation).toHaveBeenCalledWith('player-uid-1', 1)
      expect(screen.getByText(/Completed/i)).toBeInTheDocument()
    })
  })

  it('refuse replaces the recommendation with another of the same category', async () => {
    api.refuseRecommendation.mockResolvedValue({
      data: {
        refused: 1,
        replacement: { id: 3, category: 'Injury Prevention', priority: 'medium', text: 'New advice.', status: 'pending' },
      },
    })
    renderWithRouter(<PlayerRecommendations />)
    await waitFor(() => screen.getByText('Do warmups.'))

    await userEvent.click(screen.getAllByRole('button', { name: /Refuse$/i })[0])
    await waitFor(() => {
      expect(api.refuseRecommendation).toHaveBeenCalledWith('player-uid-1', 1)
      expect(screen.getByText('New advice.')).toBeInTheDocument()
      expect(screen.queryByText('Do warmups.')).not.toBeInTheDocument()
    })
  })

  it('regenerate re-rolls the refused recommendations', async () => {
    api.generateRecommendations.mockResolvedValue({
      data: {
        ...DATA, regenerated: 1,
        active: [{ id: 9, category: 'Recovery', priority: 'medium', text: 'Rest day.', status: 'pending' }],
      },
    })
    renderWithRouter(<PlayerRecommendations />)
    await waitFor(() => screen.getByText('Do warmups.'))

    await userEvent.click(screen.getByRole('button', { name: /Regenerate refused/i }))
    await waitFor(() => {
      expect(api.generateRecommendations).toHaveBeenCalledWith('player-uid-1')
      expect(screen.getByText('Rest day.')).toBeInTheDocument()
    })
  })

  it('shows the completed history when present', async () => {
    api.getRecommendations.mockResolvedValue({
      data: {
        ...DATA, active: [],
        completed: [{ id: 5, category: 'Nutrition', priority: 'low', text: 'Ate well.', status: 'completed', updated_at: '2026-06-19T08:00:00' }],
      },
    })
    renderWithRouter(<PlayerRecommendations />)
    await waitFor(() => expect(screen.getByText('Ate well.')).toBeInTheDocument())
    expect(screen.getByText(/Completed/i)).toBeInTheDocument()
  })
})
