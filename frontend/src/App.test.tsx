// @vitest-environment jsdom
import '@testing-library/jest-dom/vitest'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import App from './App'
import { ApiClientError, uploadAndAnalyzeResume } from './services/apiClient'

vi.mock('./services/apiClient', () => ({
  ApiClientError: class extends Error {
    status = 503
    body: { code: string; message: string }
    constructor(_status: number, body: { code: string; message: string }) {
      super(body.message)
      this.body = body
    }
  },
  uploadAndAnalyzeResume: vi.fn(),
}))

const uploadMock = vi.mocked(uploadAndAnalyzeResume)
const createConfigurationError = () => new ApiClientError(503, {
  code: 'AI_CONFIGURATION_ERROR',
  message: 'AI analysis is not configured.',
  details: [],
  request_id: '',
})
const analysisResult = {
  extracted_facts: {
    skills: ['React', 'TypeScript'],
    education: [],
    experience: ['Built web applications'],
    projects: [],
    certifications: [],
  },
  ai_observations: {
    summary: 'Built web applications with React and TypeScript.',
    summary_evidence: ['Built web applications with React and TypeScript.'],
    strengths: [{
      observation: 'Built web applications with React and TypeScript.',
      evidence: ['Built web applications with React and TypeScript.'],
    }],
    improvement_areas: [],
    skills_observations: [],
    experience_observations: [],
    education_observations: [],
    recommended_next_steps: [],
  },
}

describe('CareerAI dashboard actions', () => {
  afterEach(() => {
    cleanup()
    vi.resetAllMocks()
  })

  it('sends the uploaded PDF for AI analysis and shows the returned facts and observations', async () => {
    uploadMock.mockResolvedValue({
      filename: 'resume.pdf',
      page_count: 2,
      size_bytes: 1024,
      result: analysisResult,
    })
    render(<App />)

    const file = new File(['pdf bytes'], 'resume.pdf', { type: 'application/pdf' })
    fireEvent.change(screen.getByLabelText('Upload resume PDF'), {
      target: { files: [file] },
    })

    expect(await screen.findByRole('dialog', { name: /resume\.pdf/i })).toBeInTheDocument()
    expect(uploadMock).toHaveBeenCalledWith(file)
    expect(screen.getByText('TypeScript')).toBeInTheDocument()
    expect(screen.getAllByText('Built web applications with React and TypeScript.')).toHaveLength(2)
    expect(screen.getByText(/Each excerpt is copied directly from your resume/i)).toBeInTheDocument()
  })

  it('shows a useful error and leaves the resume list intact when AI is not configured', async () => {
    uploadMock.mockRejectedValue(createConfigurationError())
    render(<App />)

    const file = new File(['pdf bytes'], 'resume.pdf', { type: 'application/pdf' })
    fireEvent.change(screen.getByLabelText('Upload resume PDF'), {
      target: { files: [file] },
    })

    await waitFor(() => expect(screen.getByRole('status')).toHaveTextContent('AI is not configured'))
    expect(screen.getByRole('alert')).toHaveTextContent('Check the selected provider')
    fireEvent.click(screen.getByRole('button', { name: 'My resumes' }))
    expect(screen.getByText('Product Designer Resume.pdf')).toBeInTheDocument()
    expect(screen.queryByText('resume.pdf')).not.toBeInTheDocument()
  })
})
