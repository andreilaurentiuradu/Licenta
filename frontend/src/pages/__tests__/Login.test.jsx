import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import toast from 'react-hot-toast'

import Login from '../Login'
import { renderWithRouter } from '../../test/renderWithRouter'

const mockLogin    = vi.fn()
const mockNavigate = vi.fn()

vi.mock('../../contexts/AuthContext', () => ({
  useAuth: () => ({ login: mockLogin }),
}))

vi.mock('react-router-dom', async (orig) => {
  const actual = await orig()
  return { ...actual, useNavigate: () => mockNavigate }
})


describe('Login page', () => {
  beforeEach(() => {
    mockLogin.mockReset()
    mockNavigate.mockReset()
  })

  it('renders sign in form with username, password, and submit button', () => {
    renderWithRouter(<Login />)
    expect(screen.getAllByText(/Sign in/i).length).toBeGreaterThan(0)
    expect(screen.getByLabelText(/Username/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/Password/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Sign in/i })).toBeInTheDocument()
  })

  it('uses default football theme when no sport is saved', () => {
    renderWithRouter(<Login />)
    expect(screen.getByText(/Football/i)).toBeInTheDocument()
  })

  it('uses marathon theme when selected in localStorage', () => {
    localStorage.setItem('selected_sport', 'marathon')
    renderWithRouter(<Login />)
    expect(screen.getByText(/Marathon/i)).toBeInTheDocument()
  })

  it('calls login and navigates to /home on success', async () => {
    mockLogin.mockResolvedValueOnce({ username: 'coach_user' })
    renderWithRouter(<Login />)

    await userEvent.type(screen.getByLabelText(/Username/i), 'coach_user')
    await userEvent.type(screen.getByLabelText(/Password/i), 'coach123')
    await userEvent.click(screen.getByRole('button', { name: /Sign in/i }))

    await waitFor(() => {
      expect(mockLogin).toHaveBeenCalledWith('coach_user', 'coach123')
      expect(mockNavigate).toHaveBeenCalledWith('/home')
    })
  })

  it('shows error toast with keycloak error description on failure', async () => {
    mockLogin.mockRejectedValueOnce({
      response: { data: { error_description: 'Account is not fully set up' } },
    })
    renderWithRouter(<Login />)

    await userEvent.type(screen.getByLabelText(/Username/i), 'bad')
    await userEvent.type(screen.getByLabelText(/Password/i), 'wrong')
    await userEvent.click(screen.getByRole('button', { name: /Sign in/i }))

    await waitFor(() => {
      expect(toast.error).toHaveBeenCalledWith('Account is not fully set up')
      expect(mockNavigate).not.toHaveBeenCalled()
    })
  })

  it('shows fallback error message when keycloak returns no description', async () => {
    mockLogin.mockRejectedValueOnce({})
    renderWithRouter(<Login />)

    await userEvent.type(screen.getByLabelText(/Username/i), 'x')
    await userEvent.type(screen.getByLabelText(/Password/i), 'y')
    await userEvent.click(screen.getByRole('button', { name: /Sign in/i }))

    await waitFor(() => {
      expect(toast.error).toHaveBeenCalledWith('Invalid username or password')
    })
  })
})
