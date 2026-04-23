import { screen } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'

import Home from '../Home'
import { renderWithRouter } from '../../test/renderWithRouter'

const mockUseAuth = vi.fn()

vi.mock('../../contexts/AuthContext', () => ({
  useAuth: () => mockUseAuth(),
}))

vi.mock('react-router-dom', async (orig) => {
  const actual = await orig()
  return { ...actual, useNavigate: () => vi.fn() }
})


describe('Home page', () => {
  it('shows coach badge and base nav cards for coach user', () => {
    mockUseAuth.mockReturnValue({
      user:   { username: 'coach_user', roles: ['coach'] },
      logout: vi.fn(),
    })
    renderWithRouter(<Home />)

    expect(screen.getByText('Coach')).toBeInTheDocument()
    expect(screen.getByText(/Profile/)).toBeInTheDocument()
    expect(screen.getByText(/Support/)).toBeInTheDocument()
    expect(screen.getByText(/Feedback/)).toBeInTheDocument()
    expect(screen.queryByText(/User Management/)).not.toBeInTheDocument()
  })

  it('shows player badge for player user', () => {
    mockUseAuth.mockReturnValue({
      user:   { username: 'marian', roles: ['player'] },
      logout: vi.fn(),
    })
    renderWithRouter(<Home />)
    expect(screen.getByText('Player')).toBeInTheDocument()
    expect(screen.queryByText(/User Management/)).not.toBeInTheDocument()
  })

  it('shows admin badge and User Management card for admin', () => {
    mockUseAuth.mockReturnValue({
      user:   { username: 'admin_user', roles: ['admin'] },
      logout: vi.fn(),
    })
    renderWithRouter(<Home />)
    expect(screen.getByText('Admin')).toBeInTheDocument()
    expect(screen.getByText(/User Management/)).toBeInTheDocument()
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
