import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect, vi, beforeEach } from 'vitest'

import Support from '../Support'
import { renderWithRouter } from '../../test/renderWithRouter'

const mockNavigate = vi.fn()

vi.mock('react-router-dom', async (orig) => {
  const actual = await orig()
  return { ...actual, useNavigate: () => mockNavigate }
})

describe('Support page', () => {
  beforeEach(() => {
    mockNavigate.mockReset()
  })

  it('renders the header and contact details', () => {
    renderWithRouter(<Support />)
    expect(screen.getByRole('heading', { name: 'Support' })).toBeInTheDocument()
    expect(screen.getByText('support@lawranalyzer.io')).toBeInTheDocument()
  })

  it('lists the FAQ entries, including the new recommendation & history items', () => {
    renderWithRouter(<Support />)
    expect(screen.getByText('What is LawrAnalyzer?')).toBeInTheDocument()
    expect(screen.getByText('Can I accept, refuse or complete a recommendation?')).toBeInTheDocument()
    expect(screen.getByText('How is the metric history organised?')).toBeInTheDocument()
  })

  it('expands an FAQ when clicked', async () => {
    renderWithRouter(<Support />)
    await userEvent.click(screen.getByText('Can I accept, refuse or complete a recommendation?'))
    expect(screen.getByText(/Regenerate refused/)).toBeInTheDocument()
  })

  it('navigates back home', async () => {
    renderWithRouter(<Support />)
    await userEvent.click(screen.getByText('← Back'))
    expect(mockNavigate).toHaveBeenCalledWith('/home')
  })
})
