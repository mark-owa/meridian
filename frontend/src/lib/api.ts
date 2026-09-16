import axios, { AxiosError } from 'axios'
import type {
  DashboardStats,
  Document,
  DocumentListResponse,
  DocumentType,
  Extraction,
  KnowledgeQueryResponse,
  Lead,
  LeadListResponse,
  TokenResponse,
  User,
} from './types'

const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'
const TOKEN_KEY = 'meridian_token'

export const tokenStore = {
  get: () => localStorage.getItem(TOKEN_KEY),
  set: (token: string) => localStorage.setItem(TOKEN_KEY, token),
  clear: () => localStorage.removeItem(TOKEN_KEY),
}

export const api = axios.create({ baseURL: `${API_URL}/api/v1` })

api.interceptors.request.use((config) => {
  const token = tokenStore.get()
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

/** Turns the backend's error shapes (validation error list, or a plain
 * `detail` string from HTTPException) into one readable message. */
export function apiErrorMessage(err: unknown): string {
  if (axios.isAxiosError(err)) {
    const data = (err as AxiosError<{ detail?: unknown; error?: string }>).response?.data
    if (data?.detail) {
      if (Array.isArray(data.detail)) {
        return data.detail
          .map((d) => (typeof d === 'object' && d && 'message' in d ? String(d.message) : String(d)))
          .join(', ')
      }
      return String(data.detail)
    }
    if (data?.error) return data.error
    if (err.message === 'Network Error') return "Can't reach the Meridian API. Is the backend running?"
    return err.message
  }
  return 'Something unexpected went wrong.'
}

// Auth

export async function login(email: string, password: string) {
  const { data } = await api.post<TokenResponse>('/auth/login', { email, password })
  return data
}

export async function register(payload: {
  email: string
  full_name: string
  password: string
  company?: string
}) {
  const { data } = await api.post<User>('/auth/register', payload)
  return data
}

export async function getProfile() {
  const { data } = await api.get<User>('/auth/me')
  return data
}

// Documents

export async function listDocuments(skip = 0, limit = 20) {
  const { data } = await api.get<DocumentListResponse>('/documents', { params: { skip, limit } })
  return data
}

export async function uploadDocument(file: File) {
  const form = new FormData()
  form.append('file', file)
  const { data } = await api.post<Document>('/documents/upload', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return data
}

export async function getDocument(id: string) {
  const { data } = await api.get<Document>(`/documents/${id}`)
  return data
}

export async function deleteDocument(id: string) {
  await api.delete(`/documents/${id}`)
}

// Knowledge base

export async function queryKnowledgeBase(query: string, documentIds?: string[]) {
  const { data } = await api.post<KnowledgeQueryResponse>('/knowledge/query', {
    query,
    document_ids: documentIds,
  })
  return data
}

// Extraction

export async function runExtraction(documentId: string, documentType: DocumentType) {
  const { data } = await api.post<Extraction>('/extraction/run', {
    document_id: documentId,
    document_type: documentType,
  })
  return data
}

export async function listExtractionsForDocument(documentId: string) {
  const { data } = await api.get<Extraction[]>(`/extraction/document/${documentId}`)
  return data
}

// Leads

export async function listLeads(params?: { status?: string; min_score?: number }) {
  const { data } = await api.get<LeadListResponse>('/leads', { params })
  return data
}

export async function createLead(payload: {
  company_name: string
  contact_name: string
  contact_email: string
  industry?: string
  company_size?: string
  budget_range?: string
  pain_points?: string
  source?: string
}) {
  const { data } = await api.post<Lead>('/leads', payload)
  return data
}

export async function qualifyLead(id: string) {
  const { data } = await api.post<Lead>(`/leads/${id}/qualify`)
  return data
}

export async function updateLeadStatus(id: string, status: string) {
  const { data } = await api.patch<Lead>(`/leads/${id}/status`, null, { params: { status } })
  return data
}

export async function deleteLead(id: string) {
  await api.delete(`/leads/${id}`)
}

// Analytics

export async function getDashboardStats() {
  const { data } = await api.get<DashboardStats>('/analytics/dashboard')
  return data
}
