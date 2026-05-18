import { render, screen, act, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'

import { AuthProvider, useAuth } from '../AuthContext'

const mockApiLogin = vi.fn()
const mockGetMe    = vi.fn()

vi.mock('../../api/auth', () => ({
  login: (u, p) => mockApiLogin(u, p),
  getMe: () => mockGetMe(),
}))

function fakeJwt(payload) {
  const base64 = btoa(JSON.stringify(payload))
  return `header.${base64}.sig`
}

function TestConsumer() {
  const { user, loading, login, logout } = useAuth()
  return (
    <div>
      <div data-testid="loading">{loading ? 'loading' : 'ready'}</div>
      <div data-testid="user">{user ? user.username : 'anon'}</div>
      <div data-testid="sub">{user?.sub ?? 'none'}</div>
      <button onClick={() => login('u', 'p')}>login</button>
      <button onClick={logout}>logout</button>
    </div>
  )
}


describe('AuthContext', () => {
  beforeEach(() => {
    mockApiLogin.mockReset()
    mockGetMe.mockReset()
    localStorage.clear()
  })

  it('starts with no user when no token is stored', async () => {
    render(<AuthProvider><TestConsumer /></AuthProvider>)
    await waitFor(() => {
      expect(screen.getByTestId('loading')).toHaveTextContent('ready')
      expect(screen.getByTestId('user')).toHaveTextContent('anon')
    })
  })

  it('fetches user info when a token is already in storage', async () => {
    localStorage.setItem('access_token', 'existing-token')
    mockGetMe.mockResolvedValueOnce({ data: { sub: 'uid-1', username: 'coach_user', roles: ['coach'] } })

    render(<AuthProvider><TestConsumer /></AuthProvider>)
    await waitFor(() => {
      expect(screen.getByTestId('user')).toHaveTextContent('coach_user')
    })
  })

  it('clears storage if getMe fails (e.g. expired token)', async () => {
    localStorage.setItem('access_token', 'bad-token')
    mockGetMe.mockRejectedValueOnce(new Error('401'))

    render(<AuthProvider><TestConsumer /></AuthProvider>)
    await waitFor(() => {
      expect(screen.getByTestId('user')).toHaveTextContent('anon')
      expect(localStorage.getItem('access_token')).toBeNull()
    })
  })

  it('login stores tokens and parses username + sub from JWT', async () => {
    const token = fakeJwt({
      sub:                'uuid-1234',
      preferred_username: 'laur',
      email:              'laur@x.ro',
      realm_access:       { roles: ['coach'] },
    })
    mockApiLogin.mockResolvedValueOnce({
      data: { access_token: token, refresh_token: 'r-token' },
    })

    render(<AuthProvider><TestConsumer /></AuthProvider>)
    await waitFor(() => expect(screen.getByTestId('loading')).toHaveTextContent('ready'))

    await act(async () => {
      screen.getByText('login').click()
    })

    await waitFor(() => {
      expect(localStorage.getItem('access_token')).toBe(token)
      expect(localStorage.getItem('refresh_token')).toBe('r-token')
      expect(screen.getByTestId('user')).toHaveTextContent('laur')
      expect(screen.getByTestId('sub')).toHaveTextContent('uuid-1234')
    })
  })

  it('login parses player sub correctly for routing', async () => {
    const token = fakeJwt({
      sub:                'player-uuid-999',
      preferred_username: 'player1',
      email:              'player1@demo.ro',
      realm_access:       { roles: ['player'] },
    })
    mockApiLogin.mockResolvedValueOnce({
      data: { access_token: token, refresh_token: 'r-token' },
    })

    render(<AuthProvider><TestConsumer /></AuthProvider>)
    await waitFor(() => expect(screen.getByTestId('loading')).toHaveTextContent('ready'))

    await act(async () => {
      screen.getByText('login').click()
    })

    await waitFor(() => {
      expect(screen.getByTestId('sub')).toHaveTextContent('player-uuid-999')
    })
  })

  it('logout clears storage and user', async () => {
    localStorage.setItem('access_token', 'existing-token')
    mockGetMe.mockResolvedValueOnce({ data: { sub: 'uid-1', username: 'laur', roles: ['coach'] } })

    render(<AuthProvider><TestConsumer /></AuthProvider>)
    await waitFor(() => expect(screen.getByTestId('user')).toHaveTextContent('laur'))

    await act(async () => {
      screen.getByText('logout').click()
    })

    expect(screen.getByTestId('user')).toHaveTextContent('anon')
    expect(localStorage.getItem('access_token')).toBeNull()
  })
})
