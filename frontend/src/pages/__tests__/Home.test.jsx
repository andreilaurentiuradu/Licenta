import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect, vi } from 'vitest'

import Home from '../Home'
import { renderWithRouter } from '../../test/renderWithRouter'

const mockUseAuth = vi.fn()
const mockNavigate = vi.fn()

vi.mock('../../contexts/AuthContext', () => ({
  useAuth: () => mockUseAuth(),
}))

vi.mock('react-router-dom', async (orig) => {
  const actual = await orig()
  return { ...actual, useNavigate: () => mockNavigate }
})


describe('Home page', () => {
  it('shows coach badge and Players card for coach user', () => {
    mockUseAuth.mockReturnValue({
      user:   { username: 'coach_user', roles: ['coach'] },
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
  })

  it('My Stats card navigates to /players/<sub>/biometrics', async () => {
    mockNavigate.mockReset()
    mockUseAuth.mockReturnValue({
      user:   { username: 'marian', roles: ['player'], sub: 'player-uuid-123' },
      logout: vi.fn(),
    })
    renderWithRouter(<Home />)

    await userEvent.click(screen.getByText(/My Stats/).closest('button'))
    expect(mockNavigate).toHaveBeenCalledWith('/players/player-uuid-123/biometrics')
  })

  it('shows admin badge and User Management card for admin', () => {
    mockUseAuth.mockReturnValue({
      user:   { username: 'admin_user', roles: ['admin'] },
      logout: vi.fn(),
    })
    renderWithRouter(<Home />)

    expect(screen.getByText('Admin')).toBeInTheDocument()
    expect(screen.getByText(/User Management/)).toBeInTheDocument()
    expect(screen.queryByText(/^Players$/)).not.toBeInTheDocument()
    expect(screen.queryByText(/My Stats/)).not.toBeInTheDocument()
  })

  it('prioritizes admin role when user has multiple roles', () => {
    mockUseAuth.mockReturnValue({
      user:   { username: 'multi', roles: ['coach', 'admin'] },
      logout: vi.fn(),
    })
    renderWithRouter(<Home />)

    expect(screen.getByText('Admin')).toBeInTheDocument()
    expect(screen.getByText(/User Management/)).toBeInTheDocument()
  })
})
