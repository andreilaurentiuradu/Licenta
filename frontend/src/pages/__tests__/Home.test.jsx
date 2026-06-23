import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect, vi, beforeEach } from 'vitest'

import Home from '../Home'
import { renderWithRouter } from '../../test/renderWithRouter'
import * as flApi from '../../api/fl'

const mockUseAuth  = vi.fn()
const mockNavigate = vi.fn()

vi.mock('../../contexts/AuthContext', () => ({
  useAuth: () => mockUseAuth(),
}))

vi.mock('react-router-dom', async (orig) => {
  const actual = await orig()
  return { ...actual, useNavigate: () => mockNavigate }
})

vi.mock('../../api/fl', () => ({
  triggerFLRound: vi.fn(),
  getFlStatus:    vi.fn(),
  getFlClubs:     vi.fn(),
  getRiskRanking: vi.fn(),
}))


describe('Home page', () => {
  beforeEach(() => {
    mockNavigate.mockReset()
    flApi.triggerFLRound.mockResolvedValue({ data: { trained: false, warning: null } })
    flApi.getFlStatus.mockResolvedValue({ data: { ready: false } })
    flApi.getFlClubs.mockResolvedValue({ data: [] })
    flApi.getRiskRanking.mockResolvedValue({ data: [] })
  })

  it('shows coach badge and Players card for coach user', () => {
    mockUseAuth.mockReturnValue({
      user:   { username: 'coach_user', roles: ['coach'], club: 'FC Demo' },
      logout: vi.fn(),
    })
    renderWithRouter(<Home />)

    expect(screen.getByText('Coach')).toBeInTheDocument()
    expect(screen.getByText(/Profile/)).toBeInTheDocument()
    expect(screen.getByText(/Support/)).toBeInTheDocument()
    expect(screen.getByText(/Feedback/)).toBeInTheDocument()
    expect(screen.getByText(/Players/)).toBeInTheDocument()
    expect(screen.queryByText(/User Management/)).not.toBeInTheDocument()
    expect(screen.queryByText(/My Stats/)).not.toBeInTheDocument()
  })

  it('shows FL panel for coach', () => {
    mockUseAuth.mockReturnValue({
      user:   { username: 'coach_user', roles: ['coach'], club: 'FC Demo' },
      logout: vi.fn(),
    })
    renderWithRouter(<Home />)

    expect(screen.getByText('Federated Learning')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Start round/i })).toBeInTheDocument()
  })

  it('shows player badge and My Stats card for player user', () => {
    mockUseAuth.mockReturnValue({
      user:   { username: 'marian', roles: ['player'], sub: 'player-uuid-123' },
      logout: vi.fn(),
    })
    renderWithRouter(<Home />)

    expect(screen.getByText('Player')).toBeInTheDocument()
    expect(screen.getByText(/My Stats/)).toBeInTheDocument()
    expect(screen.queryByText(/User Management/)).not.toBeInTheDocument()
    expect(screen.queryByText(/^Players$/)).not.toBeInTheDocument()
    expect(screen.queryByText('Federated Learning')).not.toBeInTheDocument()
  })

  it('My Stats card navigates to /players/<sub>/biometrics', async () => {
    mockUseAuth.mockReturnValue({
      user:   { username: 'marian', roles: ['player'], sub: 'player-uuid-123' },
      logout: vi.fn(),
    })
    renderWithRouter(<Home />)

    await userEvent.click(screen.getByText(/My Stats/).closest('button'))
    expect(mockNavigate).toHaveBeenCalledWith('/players/player-uuid-123/biometrics')
  })

  it('shows admin badge with All Users, Create User and View Feedback cards', () => {
    mockUseAuth.mockReturnValue({
      user:   { username: 'admin_user', roles: ['admin'] },
      logout: vi.fn(),
    })
    renderWithRouter(<Home />)

    expect(screen.getByText('Admin')).toBeInTheDocument()
    expect(screen.getByText(/All Users/)).toBeInTheDocument()
    expect(screen.getByText(/Create User/)).toBeInTheDocument()
    expect(screen.getByText(/View Feedback/)).toBeInTheDocument()
    expect(screen.queryByText(/^Feedback$/)).not.toBeInTheDocument()
    expect(screen.queryByText(/^Players$/)).not.toBeInTheDocument()
    expect(screen.queryByText(/My Stats/)).not.toBeInTheDocument()
    expect(screen.queryByText('Federated Learning')).not.toBeInTheDocument()
  })

  it('View Feedback card navigates to /admin/feedback', async () => {
    mockUseAuth.mockReturnValue({
      user:   { username: 'admin_user', roles: ['admin'] },
      logout: vi.fn(),
    })
    renderWithRouter(<Home />)

    await userEvent.click(screen.getByText(/View Feedback/).closest('button'))
    expect(mockNavigate).toHaveBeenCalledWith('/admin/feedback')
  })

  it('prioritizes admin role when user has multiple roles', () => {
    mockUseAuth.mockReturnValue({
      user:   { username: 'multi', roles: ['coach', 'admin'] },
      logout: vi.fn(),
    })
    renderWithRouter(<Home />)

    expect(screen.getByText('Admin')).toBeInTheDocument()
    expect(screen.getByText(/All Users/)).toBeInTheDocument()
  })

  it('shows no club assigned when coach has no club', () => {
    mockUseAuth.mockReturnValue({
      user:   { username: 'coach_user', roles: ['coach'], club: null },
      logout: vi.fn(),
    })
    renderWithRouter(<Home />)

    expect(screen.getByText(/No club assigned/)).toBeInTheDocument()
  })
})
