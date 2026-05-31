import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import toast from 'react-hot-toast'

import AdminUsers from '../AdminUsers'
import { renderWithRouter } from '../../test/renderWithRouter'

const mockListUsers  = vi.fn()
const mockDeleteUser = vi.fn()
const mockNavigate   = vi.fn()

vi.mock('../../api/auth', () => ({
  listUsers:  () => mockListUsers(),
  deleteUser: (id) => mockDeleteUser(id),
}))

vi.mock('react-router-dom', async (orig) => {
  const actual = await orig()
  return { ...actual, useNavigate: () => mockNavigate }
})

const MOCK_USERS = [
  { id: 'uid-1', username: 'admin1',  email: 'admin@test.ro',  roles: ['admin'],  club: null       },
  { id: 'uid-2', username: 'coach1',  email: 'coach@test.ro',  roles: ['coach'],  club: 'FC Demo'  },
  { id: 'uid-3', username: 'player1', email: 'player@test.ro', roles: ['player'], club: 'FC Demo'  },
  { id: 'uid-4', username: 'coach2',  email: 'coach2@test.ro', roles: ['coach'],  club: 'FC Rivals' },
]

describe('AdminUsers page', () => {
  beforeEach(() => {
    mockListUsers.mockReset()
    mockDeleteUser.mockReset()
    mockNavigate.mockReset()
    vi.spyOn(window, 'confirm').mockReturnValue(true)
    mockListUsers.mockResolvedValue({ data: MOCK_USERS })
  })

  it('renders loading state then user list', async () => {
    renderWithRouter(<AdminUsers />)
    expect(screen.getByText('Loading…')).toBeInTheDocument()
    await waitFor(() => {
      expect(screen.getByText('admin1')).toBeInTheDocument()
      expect(screen.getByText('coach1')).toBeInTheDocument()
      expect(screen.getByText('player1')).toBeInTheDocument()
    })
  })

  it('shows total user count in header', async () => {
    renderWithRouter(<AdminUsers />)
    await waitFor(() => {
      expect(screen.getByText(/4 accounts/)).toBeInTheDocument()
    })
  })

  it('shows role badges for each user', async () => {
    renderWithRouter(<AdminUsers />)
    await waitFor(() => {
      expect(screen.getByText('admin')).toBeInTheDocument()
      expect(screen.getAllByText('coach').length).toBeGreaterThan(0)
      expect(screen.getByText('player')).toBeInTheDocument()
    })
  })

  it('filters by role tab', async () => {
    renderWithRouter(<AdminUsers />)
    await waitFor(() => screen.getByText('coach1'))

    await userEvent.click(screen.getByRole('button', { name: /Coach/i }))
    expect(screen.getByText('coach1')).toBeInTheDocument()
    expect(screen.getByText('coach2')).toBeInTheDocument()
    expect(screen.queryByText('player1')).not.toBeInTheDocument()
    expect(screen.queryByText('admin1')).not.toBeInTheDocument()
  })

  it('filters by search input', async () => {
    renderWithRouter(<AdminUsers />)
    await waitFor(() => screen.getByText('coach1'))

    await userEvent.type(screen.getByPlaceholderText(/Search/i), 'rivals')
    expect(screen.getByText('coach2')).toBeInTheDocument()
    expect(screen.queryByText('coach1')).not.toBeInTheDocument()
    expect(screen.queryByText('player1')).not.toBeInTheDocument()
  })

  it('deletes a user after confirmation', async () => {
    mockDeleteUser.mockResolvedValueOnce({ data: { deleted: 'uid-3' } })
    renderWithRouter(<AdminUsers />)
    await waitFor(() => screen.getByText('player1'))

    const deleteButtons = screen.getAllByRole('button', { name: /Delete/i })
    await userEvent.click(deleteButtons[2]) // player1 is 3rd

    await waitFor(() => {
      expect(mockDeleteUser).toHaveBeenCalledWith('uid-3')
      expect(toast.success).toHaveBeenCalledWith('User "player1" deleted')
      expect(screen.queryByText('player1')).not.toBeInTheDocument()
    })
  })

  it('does not delete if confirmation is cancelled', async () => {
    vi.spyOn(window, 'confirm').mockReturnValue(false)
    renderWithRouter(<AdminUsers />)
    await waitFor(() => screen.getByText('player1'))

    const deleteButtons = screen.getAllByRole('button', { name: /Delete/i })
    await userEvent.click(deleteButtons[0])

    expect(mockDeleteUser).not.toHaveBeenCalled()
  })

  it('shows error toast when delete fails', async () => {
    mockDeleteUser.mockRejectedValueOnce({
      response: { data: { error: 'Cannot delete last admin' } },
    })
    renderWithRouter(<AdminUsers />)
    await waitFor(() => screen.getByText('admin1'))

    const deleteButtons = screen.getAllByRole('button', { name: /Delete/i })
    await userEvent.click(deleteButtons[0])

    await waitFor(() => {
      expect(toast.error).toHaveBeenCalledWith('Cannot delete last admin')
    })
  })

  it('shows empty state when no users match search', async () => {
    renderWithRouter(<AdminUsers />)
    await waitFor(() => screen.getByText('coach1'))

    await userEvent.type(screen.getByPlaceholderText(/Search/i), 'nonexistent')
    expect(screen.getByText('No users found.')).toBeInTheDocument()
  })

  it('navigate to create user on button click', async () => {
    renderWithRouter(<AdminUsers />)
    await waitFor(() => screen.getByText('admin1'))

    await userEvent.click(screen.getByRole('button', { name: /Create user/i }))
    expect(mockNavigate).toHaveBeenCalledWith('/admin/create-user')
  })

  it('shows error toast when list fetch fails', async () => {
    mockListUsers.mockRejectedValueOnce(new Error('Network error'))
    renderWithRouter(<AdminUsers />)
    await waitFor(() => {
      expect(toast.error).toHaveBeenCalledWith('Failed to load users')
    })
  })
})
