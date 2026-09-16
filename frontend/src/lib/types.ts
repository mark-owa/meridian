// Mirrors backend/models/schemas.py. Keeping these hand-in-sync (rather than
// codegen'd) is a deliberate tradeoff for a project this size — revisit with
// openapi-typescript if the API surface grows much larger.

export type UserRole = 'admin' | 'user' | 'viewer'
export type DocumentStatus = 'pending' | 'processing' | 'ready' | 'failed'
export type DocumentType = 'invoice' | 'contract' | 'receipt' | 'general'
export type LeadStatus = 'new' | 'qualified' | 'contacted' | 'converted' | 'lost'
export type LeadAction = 'pursue' | 'nurture' | 'disqualify'
export type CompanySize = 'startup' | 'smb' | 'enterprise'
export type LeadSource = 'website' | 'referral' | 'cold_outreach' | 'trade_show' | 'social'

export interface User {
  id: string
  email: string
  full_name: string
  company: string | null
  role: UserRole
  is_active: boolean
  created_at: string
}

export interface TokenResponse {
  access_token: string
  token_type: string
  expires_in: number
}

export interface Document {
  id: string
  filename: string
  original_name: string
  file_type: string
  file_size_bytes: number
  status: DocumentStatus
  chunk_count: number
  error_message: string | null
  created_at: string
  processed_at: string | null
}

export interface DocumentListResponse {
  documents: Document[]
  total: number
}

export interface SourceChunk {
  document_id: string
  document_name: string
  chunk_text: string
  similarity_score: number
  chunk_index: number
}

export interface KnowledgeQueryResponse {
  query: string
  answer: string
  sources: SourceChunk[]
  tokens_used: number
  response_time_ms: number
}

export interface Extraction {
  id: string
  document_id: string
  document_type: string
  extracted_data: Record<string, unknown>
  confidence_score: number | null
  model_used: string | null
  created_at: string
}

export interface Lead {
  id: string
  company_name: string
  contact_name: string
  contact_email: string
  industry: string | null
  company_size: string | null
  budget_range: string | null
  pain_points: string | null
  source: string | null
  qualification_score: number | null
  qualification_reason: string | null
  recommended_action: LeadAction | null
  strengths: string[] | null
  concerns: string[] | null
  drafted_email: string | null
  email_subject: string | null
  status: LeadStatus
  created_at: string
  qualified_at: string | null
}

export interface LeadListResponse {
  leads: Lead[]
  total: number
  qualified_count: number
  avg_score: number | null
}

export interface DashboardStats {
  total_documents: number
  documents_ready: number
  total_queries: number
  avg_response_time_ms: number | null
  total_leads: number
  qualified_leads: number
  avg_lead_score: number | null
  total_extractions: number
}

export interface ApiErrorBody {
  error?: string
  detail?: string | { field: string; message: string }[]
}
