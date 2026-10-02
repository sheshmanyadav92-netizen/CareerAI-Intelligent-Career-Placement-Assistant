// @vitest-environment jsdom
import '@testing-library/jest-dom/vitest'
import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'

import { ResumeAnalysisView } from './ResumeAnalysisView'
import type { ResumeAnalysisResult } from '../types'

const result: ResumeAnalysisResult = {
  extracted_facts: {
    skills: ['Python'],
    education: [],
    experience: [],
    projects: [],
    certifications: [],
  },
  ai_observations: {
    summary: 'Built a Python web application.',
    summary_evidence: ['Built a Python web application.'],
    strengths: [
      {
        observation: 'Built a Python web application.',
        evidence: ['Built a Python web application.'],
      },
    ],
    improvement_areas: [],
    skills_observations: [],
    experience_observations: [],
    education_observations: [],
    recommended_next_steps: [],
  },
}

describe('ResumeAnalysisView', () => {
  afterEach(cleanup)

  it('separates extracted facts from labeled AI observations', () => {
    render(<ResumeAnalysisView state={{ status: 'ready', result }} />)

    expect(screen.getByRole('heading', { name: 'Extracted Facts' })).toBeInTheDocument()
    expect(screen.getByText('Information extracted from your resume')).toBeInTheDocument()
    expect(screen.getByText('Python')).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'AI-selected resume highlights' })).toBeInTheDocument()
    expect(screen.getAllByText('Built a Python web application.')).toHaveLength(2)
    expect(screen.getByText(/Each excerpt is copied directly from your resume/i)).toBeInTheDocument()
  })

  it('shows an accessible loading state', () => {
    render(<ResumeAnalysisView state={{ status: 'loading' }} />)

    expect(screen.getByRole('status')).toHaveTextContent('Analyzing your resume...')
  })

  it.each([
    ['AI_CONFIGURATION_ERROR', 'Check the selected provider and its required settings'],
    ['AI_PROVIDER_TIMEOUT', 'Resume analysis took too long. Please try again.'],
    ['AI_PROVIDER_ERROR', 'Resume analysis is temporarily unavailable. Please try again later.'],
    ['AI_INVALID_OUTPUT', "We couldn't complete the analysis. Please try again."],
  ])('maps %s to a safe user message', (code, message) => {
    render(<ResumeAnalysisView state={{ status: 'error', code }} />)

    expect(screen.getByRole('alert')).toHaveTextContent(message)
  })
})