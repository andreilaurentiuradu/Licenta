import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import toast from 'react-hot-toast'

import UserManagement from '../UserManagement'
import { renderWithRouter } from '../../test/renderWithRouter'

const mockCreate   = vi.fn()
const mockNavigate = vi.fn()

vi.mock('../../api/auth', () => ({
  adminCreateUser: (data) => mockCreate(data),
}))

vi.mock('react-router-dom', async (orig) => {
  const actual = await orig()
  return { ...actual, useNavigate: () => mockNavigate }
})


describe('UserManagement page', () => {
  beforeEach(() => {
    mockCreate.mockReset()
    mockNavigate.mockReset()
  })

  it('shows role dropdown with admin, coach, and player', () => {
    renderWithRouter(<UserManagement />)
    const options = screen.getAllByRole('option').map(o => o.value)
    expect(options).toEqual(expect.arrayContaining(['admin', 'coach', 'player']))
  })

  it('rejects mismatched passwords', async () => {
    renderWithRouter(<UserManagement />)

    await userEvent.type(screen.getByLabelText(/Username/i),  'newadmin')
    await userEvent.type(screen.getByLabelText(/Email/i),     'a@x.ro')
    await userEvent.type(screen.getByLabelText(/^Password$/i), 'secret123')
    await userEvent.type(screen.getByLabelText(/Confirm/i),    'different')
    await userEvent.click(screen.getByRole('button', { name: /Create user/i }))

    await waitFor(() => {
      expect(toast.error).toHaveBeenCalledWith('Passwords do not match')
      expect(mockCreate).not.toHaveBeenCalled()
    })
  })

  it('admin can create another admin user', async () => {
    mockCreate.mockResolvedValueOnce({ data: { message: 'ok' } })
    renderWithRouter(<UserManagement />)

    await userEvent.type(screen.getByLabelText(/Username/i),  'newadmin')
    await userEvent.type(screen.getByLabelText(/Email/i),     'a@x.ro')
    await userEvent.type(screen.getByLabelText(/^Password$/i), 'secret123')
    await userEvent.type(screen.getByLabelText(/Confirm/i),    'secret123')
    await userEvent.selectOptions(screen.getByLabelText(/Role/i), 'admin')
    await userEvent.click(screen.getByRole('button', { name: /Create user/i }))

    await waitFor(() => {
      expect(mockCreate).toHaveBeenCalledWith({
        username: 'newadmin',
        email:    'a@x.ro',
        password: 'secret123',
        role:     'admin',
      })
      expect(toast.success).toHaveBeenCalled()
    })
  })

  it('resets form after successful creation', async () => {
    mockCreate.mockResolvedValueOnce({ data: { message: 'ok' } })
    renderWithRouter(<UserManagement />)

    const username = screen.getByLabelText(/Username/i)
    await userEvent.type(username, 'newcoach')
    await userEvent.type(screen.getByLabelText(/Email/i),     'c@x.ro')
    await userEvent.type(screen.getByLabelText(/^Password$/i), 'secret123')
    await userEvent.type(screen.getByLabelText(/Confirm/i),    'secret123')
    await userEvent.click(screen.getByRole('button', { name: /Create user/i }))

    await waitFor(() => expect(username.value).toBe(''))
  })

  it('shows error when admin create fails', async () => {
    mockCreate.mockRejectedValueOnce({
      response: { data: { error: 'Username or email already exists' } },
    })
    renderWithRouter(<UserManagement />)

    await userEvent.type(screen.getByLabelText(/Username/i),  'dupe')
    await userEvent.type(screen.getByLabelText(/Email/i),     'd@x.ro')
    await userEvent.type(screen.getByLabelText(/^Password$/i), 'secret123')
    await userEvent.type(screen.getByLabelText(/Confirm/i),    'secret123')
    await userEvent.click(screen.getByRole('button', { name: /Create user/i }))

    await waitFor(() => {
      expect(toast.error).toHaveBeenCalledWith('Username or email already exists')
    })
  })
})
