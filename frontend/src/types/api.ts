export type ApiErrorBody = {
  code: string
  message: string
  details: Array<{ field: string; message: string }>
  request_id: string
}

export type ApiError = {
  status: number
  body: ApiErrorBody
}

export type User = {
  id: number
  email: string
  is_active: boolean
}

export type Profile = {
  user_id: number
  name: string
  education: string | null
  degree: string | null
  branch: string | null
  graduation_year: number | null
  skills: string[]
  preferred_roles: string[]
  experience_level: 'entry' | 'mid' | 'senior' | 'lead' | null
}

export type AuthResponse = {
  user: User
}

export type ResumeObservation = {
  observation: string
  evidence: string[]
}

export type ResumeAIAnalysis = {
  summary: string | null
  summary_evidence: string[]
  strengths: ResumeObservation[]
  improvement_areas: ResumeObservation[]
  skills_observations: ResumeObservation[]
  experience_observations: ResumeObservation[]
  education_observations: ResumeObservation[]
  recommended_next_steps: ResumeObservation[]
}

export type ExtractedResumeFacts = {
  skills: string[]
  education: string[]
  experience: string[]
  projects: string[]
  certifications: string[]
}

export type ResumeAnalysisResult = {
  extracted_facts: ExtractedResumeFacts
  ai_observations: ResumeAIAnalysis
}

export type ResumeUploadAnalysisResponse = {
  filename: string
  page_count: number
  size_bytes: number
  result: ResumeAnalysisResult
}
