import type { ApiErrorBody, ResumeUploadAnalysisResponse } from '../types'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8001'

export class ApiClientError extends Error {
  status: number
  body: ApiErrorBody

  constructor(status: number, body: ApiErrorBody) {
    super(body.message)
    this.name = 'ApiClientError'
    this.status = status
    this.body = body
  }
}

async function parseJsonBody(response: Response): Promise<ApiErrorBody | null> {
  try {
    return (await response.json()) as ApiErrorBody
  } catch {
    return null
  }
}

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const body = (await parseJsonBody(response)) ?? {
      code: 'UNKNOWN_ERROR',
      message: 'Something went wrong.',
      details: [],
      request_id: '',
    }

    if (response.status === 401) {
      throw new ApiClientError(response.status, body)
    }

    throw new ApiClientError(response.status, body)
  }

  return (await response.json()) as T
}

export async function apiRequest<T>(
  endpoint: string,
  options: RequestInit = {},
): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    ...options,
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
      ...(options.headers ?? {}),
    },
  })

  return handleResponse<T>(response)
}

export async function uploadAndAnalyzeResume(
  file: File,
): Promise<ResumeUploadAnalysisResponse> {
  const formData = new FormData()
  formData.append('file', file)
  const controller = new AbortController()
  const timeoutId = window.setTimeout(() => controller.abort(), 240_000)

  try {
    const response = await fetch(`${API_BASE_URL}/api/v1/resume-analysis/analyze`, {
      method: 'POST',
      body: formData,
      credentials: 'omit',
      signal: controller.signal,
    })
    return await handleResponse<ResumeUploadAnalysisResponse>(response)
  } catch (error) {
    if (error instanceof Error && error.name === 'AbortError') {
      throw new Error('Resume analysis timed out. Please try again.')
    }
    if (error instanceof TypeError) {
      throw new Error('Could not reach the analysis API. Make sure the backend is running.')
    }
    throw error
  } finally {
    window.clearTimeout(timeoutId)
  }
}

export function isUnauthorizedError(error: unknown): boolean {
  return error instanceof ApiClientError && error.status === 401
}

export function getErrorMessage(error: unknown): string {
  if (error instanceof ApiClientError) {
    return error.body.message
  }

  if (error instanceof Error) {
    return error.message
  }

  return 'Something went wrong.'
}

export { API_BASE_URL }
