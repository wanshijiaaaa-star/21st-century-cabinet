export interface Tag {
  id: string
  name: string
  cover?: string | null
  intro?: string | null
  status: number
  created_at: string
  updated_at: string
}

export interface TagCreate {
  name: string
  cover?: string | null
  intro?: string | null
  status?: number
}