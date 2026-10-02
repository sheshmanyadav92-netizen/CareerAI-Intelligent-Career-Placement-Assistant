import type { ResumeAnalysisResult, ResumeObservation } from '../types'

type ResumeAnalysisViewState =
  | { status: 'loading' }
  | { status: 'error'; code: string }
  | { status: 'ready'; result: ResumeAnalysisResult }

type ResumeAnalysisViewProps = {
  state: ResumeAnalysisViewState
}

const factSections = [
  ['Skills', 'skills'],
  ['Education', 'education'],
  ['Experience', 'experience'],
  ['Projects', 'projects'],
  ['Certifications', 'certifications'],
] as const

const observationSections = [
  ['Strengths', 'strengths'],
  ['Improvement areas', 'improvement_areas'],
  ['Skills observations', 'skills_observations'],
  ['Experience observations', 'experience_observations'],
  ['Education observations', 'education_observations'],
  ['Recommended next steps', 'recommended_next_steps'],
] as const

function ObservationList({ items }: { items: ResumeObservation[] }) {
  if (items.length === 0) return null

  return (
    <ul className="mt-3 space-y-3">
      {items.map((item, index) => (
        <ObservationItem key={`${item.observation}-${index}`} item={item} />
      ))}
    </ul>
  )
}

function ObservationItem({ item }: { item: ResumeObservation }) {
  const supportingEvidence = item.evidence.filter((quote) => quote !== item.observation)

  return (
    <li className="border-l-2 border-emerald-700 pl-4">
      <p className="font-medium text-slate-900">{item.observation}</p>
      {supportingEvidence.length > 0 && (
        <p className="mt-1 text-sm text-slate-600">
          Evidence: {supportingEvidence.map((quote) => `“${quote}”`).join(' · ')}
        </p>
      )}
    </li>
  )
}

function errorMessage(code: string): string {
  if (code === 'AI_CONFIGURATION_ERROR') {
    return 'AI is not configured. Check the selected provider and its required settings in the project .env, then restart the API.'
  }
  if (code === 'AI_PROVIDER_TIMEOUT') {
    return 'Resume analysis took too long. Please try again.'
  }
  if (code === 'AI_PROVIDER_ERROR' || code === 'AI_CONFIGURATION_ERROR') {
    return 'Resume analysis is temporarily unavailable. Please try again later.'
  }
  if (code === 'AI_INVALID_OUTPUT') {
    return "We couldn't complete the analysis. Please try again."
  }
  if (code === 'INVALID_RESUME_TEXT') {
    return 'No selectable text was found. Scanned resumes need OCR before analysis.'
  }
  if (code === 'RESUME_TEXT_TOO_LONG') {
    return 'This resume is too long to analyze. Please use a shorter PDF.'
  }
  return 'Something went wrong. Please try again.'
}

export function ResumeAnalysisView({ state }: ResumeAnalysisViewProps) {
  if (state.status === 'loading') {
    return <p role="status" className="p-6 text-slate-700">Analyzing your resume...</p>
  }

  if (state.status === 'error') {
    return (
      <p role="alert" className="p-6 text-red-800">
        {errorMessage(state.code)}
      </p>
    )
  }

  const { extracted_facts: facts, ai_observations: observations } = state.result
  const visibleFacts = factSections.filter(([, key]) => facts[key].length > 0)

  return (
    <main className="mx-auto max-w-4xl px-5 py-8 text-slate-900 sm:px-8">
      <h1 className="text-2xl font-semibold">Resume analysis</h1>

      <section aria-labelledby="facts-heading" className="mt-8 border-t border-slate-200 pt-6">
        <h2 id="facts-heading" className="text-xl font-semibold">Extracted Facts</h2>
        <p className="mt-1 text-sm text-slate-600">Information extracted from your resume</p>
        {visibleFacts.length === 0 ? (
          <p className="mt-4 text-slate-600">No extracted facts are available.</p>
        ) : (
          <dl className="mt-5 space-y-5">
            {visibleFacts.map(([label, key]) => (
              <div key={key}>
                <dt className="font-medium">{label}</dt>
                <dd>
                  <ul className="mt-2 list-disc space-y-1 pl-5 text-slate-700">
                    {facts[key].map((fact, index) => <li key={`${fact}-${index}`}>{fact}</li>)}
                  </ul>
                </dd>
              </div>
            ))}
          </dl>
        )}
      </section>

      <section aria-labelledby="observations-heading" className="mt-9 border-t border-slate-200 pt-6">
        <h2 id="observations-heading" className="text-xl font-semibold">AI-selected resume highlights</h2>
        <p className="mt-1 text-sm text-slate-600">Verbatim excerpts selected and grouped by AI</p>
        <p className="mt-3 border-l-2 border-amber-500 bg-amber-50 px-4 py-3 text-sm text-amber-950">
          Each excerpt is copied directly from your resume. AI-selected categories may not always fit; review them against the original.
        </p>

        {observations.summary && (
          <div className="mt-6">
            <h3 className="font-semibold">Summary</h3>
            <p className="mt-2 text-slate-700">{observations.summary}</p>
            {observations.summary_evidence.some((quote) => quote !== observations.summary) && (
              <p className="mt-2 text-sm text-slate-600">
                Evidence: {observations.summary_evidence.filter((quote) => quote !== observations.summary).map((quote) => `“${quote}”`).join(' · ')}
              </p>
            )}
          </div>
        )}

        <div className="mt-6 space-y-6">
          {observationSections.map(([label, key]) => {
            const items = observations[key]
            if (items.length === 0) return null
            return (
              <section key={key} aria-label={label}>
                <h3 className="font-semibold">{label}</h3>
                <ObservationList items={items} />
              </section>
            )
          })}
        </div>
      </section>
    </main>
  )
}