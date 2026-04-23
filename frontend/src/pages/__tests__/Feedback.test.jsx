import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect, vi, beforeEach } from 'vitest'

import Feedback from '../Feedback'
import { renderWithRouter } from '../../test/renderWithRouter'

const mockSubmit   = vi.fn()
const mockNavigate = vi.fn()

vi.mock('../../api/auth', () => ({
  submitFeedback: (ratings, message) => mockSubmit(ratings, message),
}))

vi.mock('react-router-dom', async (orig) => {
  const actual = await orig()
  return { ...actual, useNavigate: () => mockNavigate }
})


describe('Feedback page', () => {
  beforeEach(() => {
    mockSubmit.mockReset()
    mockNavigate.mockReset()
  })

  it('renders all four rating aspects', () => {
    renderWithRouter(<Feedback />)
    expect(screen.getByText(/Overall experience/i)).toBeInTheDocument()
    expect(screen.getByText(/UI & Design/i)).toBeInTheDocument()
    expect(screen.getByText(/Performance/i)).toBeInTheDocument()
    expect(screen.getByText(/Ease of use/i)).toBeInTheDocument()
  })

  it('renders 5 stars per aspect (20 total)', () => {
    renderWithRouter(<Feedback />)
    const stars = screen.getAllByRole('button').filter(b => b.textContent === '★')
    expect(stars).toHaveLength(20)
  })

  it('blocks submit when not all aspects are rated', async () => {
    renderWithRouter(<Feedback />)
    await userEvent.click(screen.getByRole('button', { name: /Submit feedback/i }))
    await waitFor(() => expect(mockSubmit).not.toHaveBeenCalled())
  })

  it('submits feedback with all ratings + message', async () => {
    mockSubmit.mockResolvedValueOnce({ data: { id: 1 } })
    renderWithRouter(<Feedback />)

    // Click 5th star for each aspect (20 star buttons, select every 5th)
    const stars = screen.getAllByRole('button').filter(b => b.textContent === '★')
    await userEvent.click(stars[4])   // aspect 1, star 5
    await userEvent.click(stars[9])   // aspect 2, star 5
    await userEvent.click(stars[14])  // aspect 3, star 5
    await userEvent.click(stars[19])  // aspect 4, star 5

    await userEvent.type(screen.getByPlaceholderText(/Tell us what you think/i), 'Great app!')
    await userEvent.click(screen.getByRole('button', { name: /Submit feedback/i }))

    await waitFor(() => {
      expect(mockSubmit).toHaveBeenCalledTimes(1)
      const [ratings, message] = mockSubmit.mock.calls[0]
      expect(Object.keys(ratings)).toHaveLength(4)
      expect(Object.values(ratings)).toEqual([5, 5, 5, 5])
      expect(message).toBe('Great app!')
    })
  })

  it('shows thank-you screen after successful submit', async () => {
    mockSubmit.mockResolvedValueOnce({ data: { id: 1 } })
    renderWithRouter(<Feedback />)

    const stars = screen.getAllByRole('button').filter(b => b.textContent === '★')
    await userEvent.click(stars[0])
    await userEvent.click(stars[5])
    await userEvent.click(stars[10])
    await userEvent.click(stars[15])

    await userEvent.click(screen.getByRole('button', { name: /Submit feedback/i }))

    await waitFor(() => {
      expect(screen.getByText(/Thanks for your feedback/i)).toBeInTheDocument()
    })
  })
})
