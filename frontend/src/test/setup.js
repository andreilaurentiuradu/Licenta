import '@testing-library/jest-dom'
import { cleanup } from '@testing-library/react'
import { afterEach, vi } from 'vitest'

afterEach(() => {
  cleanup()
  localStorage.clear()
  vi.restoreAllMocks()
})

vi.mock('react-hot-toast', () => ({
  default: {
    success: vi.fn(),
    error:   vi.fn(),
  },
  Toaster: () => null,
}))
