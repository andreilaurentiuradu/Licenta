import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import toast from 'react-hot-toast'

import Register from '../Register'
import { renderWithRouter } from '../../test/renderWithRouter'

const mockRegister = vi.fn()
const mockNavigate = vi.fn()

vi.mock('../../api/auth', () => ({
  register: (data) => mockRegister(data),
}))

vi.mock('react-router-dom', async (orig) => {
  const actual = await orig()
  return { ...actual, useNavigate: () => mockNavigate }
})


describe('Register page', () => {
  beforeEach(() => {
    mockRegister.mockReset()
    mockNavigate.mockReset()
  })

  it('renders all form fields', () => {
    renderWithRouter(<Register />)
    expect(screen.getAllByText(/Create account/i).length).toBeGreaterThan(0)
    expect(screen.getByLabelText(/Username/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/Email/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/^Password$/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/Confirm/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/Role/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/Sport/i)).toBeInTheDocument()
  })

  it('public register only allows coach or player roles', () => {
    renderWithRouter(<Register />)
    const roleOptions = screen.getByLabelText(/Role/i).querySelectorAll('option')
    const roleValues  = [...roleOptions].map((o) => o.value)
    expect(roleValues).toContain('coach')
    expect(roleValues).toContain('player')
    expect(roleValues).not.toContain('admin')
  })

  it('sport dropdown contains football and marathon', () => {
    renderWithRouter(<Register />)
    const sportOptions = screen.getByLabelText(/Sport/i).querySelectorAll('option')
    const sportValues  = [...sportOptions].map((o) => o.value)
    expect(sportValues).toContain('football')
    expect(sportValues).toContain('marathon')
  })

  it('rejects submission when passwords do not match', async () => {
    renderWithRouter(<Register />)

    await userEvent.type(screen.getByLabelText(/Username/i),  'laur')
    await userEvent.type(screen.getByLabelText(/Email/i),     'laur@x.ro')
    await userEvent.type(screen.getByLabelText(/^Password$/i), 'secret123')
    await userEvent.type(screen.getByLabelText(/Confirm/i),    'different123')
    await userEvent.click(screen.getByRole('button', { name: /Create account/i }))

    await waitFor(() => {
      expect(toast.error).toHaveBeenCalledWith('Passwords do not match')
      expect(mockRegister).not.toHaveBeenCalled()
    })
  })

  it('successful register navigates to /login with success toast', async () => {
    mockRegister.mockResolvedValueOnce({ data: { message: 'ok' } })
    renderWithRouter(<Register />)

    await userEvent.type(screen.getByLabelText(/Username/i),  'laur')
    await userEvent.type(screen.getByLabelText(/Email/i),     'laur@x.ro')
    await userEvent.type(screen.getByLabelText(/^Password$/i), 'secret123')
    await userEvent.type(screen.getByLabelText(/Confirm/i),    'secret123')
    await userEvent.click(screen.getByRole('button', { name: /Create account/i }))

    await waitFor(() => {
      expect(mockRegister).toHaveBeenCalledWith({
        username: 'laur',
        email:    'laur@x.ro',
        password: 'secret123',
        role:     'coach',
      })
      expect(localStorage.getItem('selected_sport')).toBe('football')
      expect(toast.success).toHaveBeenCalledWith('Account created! Please sign in.')
      expect(mockNavigate).toHaveBeenCalledWith('/login')
    })
  })

  it('shows server error when register fails', async () => {
    mockRegister.mockRejectedValueOnce({
      response: { data: { error: 'Username or email already exists' } },
    })
    renderWithRouter(<Register />)

    await userEvent.type(screen.getByLabelText(/Username/i),  'laur')
    await userEvent.type(screen.getByLabelText(/Email/i),     'laur@x.ro')
    await userEvent.type(screen.getByLabelText(/^Password$/i), 'secret123')
    await userEvent.type(screen.getByLabelText(/Confirm/i),    'secret123')
    await userEvent.click(screen.getByRole('button', { name: /Create account/i }))

    await waitFor(() => {
      expect(toast.error).toHaveBeenCalledWith('Username or email already exists')
      expect(mockNavigate).not.toHaveBeenCalled()
    })
  })
})
