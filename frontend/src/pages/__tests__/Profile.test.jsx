import { screen } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'

import Profile from '../Profile'
import { renderWithRouter } from '../../test/renderWithRouter'

const mockUseAuth = vi.fn()

vi.mock('../../contexts/AuthContext', () => ({
  useAuth: () => mockUseAuth(),
}))

vi.mock('react-router-dom', async (orig) => {
  const actual = await orig()
  return { ...actual, useNavigate: () => vi.fn() }
})


describe('Profile page', () => {
  it('shows username, email, and coach role', () => {
    mockUseAuth.mockReturnValue({
      user:   { username: 'laur', email: 'laur@x.ro', roles: ['coach'] },
      logout: vi.fn(),
    })
    renderWithRouter(<Profile />)

    expect(screen.getAllByText('laur').length).toBeGreaterThan(0)
    expect(screen.getByText('laur@x.ro')).toBeInTheDocument()
    expect(screen.getAllByText('Coach').length).toBeGreaterThan(0)
  })

  it('shows admin badge when user has admin role', () => {
    mockUseAuth.mockReturnValue({
      user:   { username: 'admin_user', email: 'a@x.ro', roles: ['admin'] },
      logout: vi.fn(),
    })
    renderWithRouter(<Profile />)
    expect(screen.getAllByText('Admin').length).toBeGreaterThan(0)
  })

  it('shows player badge when user has player role', () => {
    mockUseAuth.mockReturnValue({
      user:   { username: 'marian', email: 'm@x.ro', roles: ['player'] },
      logout: vi.fn(),
    })
    renderWithRouter(<Profile />)
    expect(screen.getAllByText('Player').length).toBeGreaterThan(0)
  })

  it('displays initials from username', () => {
    mockUseAuth.mockReturnValue({
      user:   { username: 'laurentiu', email: 'l@x.ro', roles: ['coach'] },
      logout: vi.fn(),
    })
    renderWithRouter(<Profile />)
    expect(screen.getByText('LA')).toBeInTheDocument()
  })

  it('filters out Keycloak internal roles', () => {
    mockUseAuth.mockReturnValue({
      user: {
        username: 'laur',
        email:    'l@x.ro',
        roles:    ['coach', 'default-roles-lawranalyzer', 'offline_access'],
      },
      logout: vi.fn(),
    })
    renderWithRouter(<Profile />)
    expect(screen.getByText('coach')).toBeInTheDocument()
    expect(screen.queryByText('default-roles-lawranalyzer')).not.toBeInTheDocument()
    expect(screen.queryByText('offline_access')).not.toBeInTheDocument()
  })
})
