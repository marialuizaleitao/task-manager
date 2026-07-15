import { api } from './api'
import type { PaginatedResponse } from './pagination'

export interface Task {
  id: number
  title: string
  description: string
  completed: boolean
  category: number | null
  due_date: string | null
  created_at: string
  updated_at: string
}

export interface TaskPayload {
  title: string
  description?: string
  completed?: boolean
  category?: number | null
  due_date?: string | null
}

export type TaskOrdering = 'title' | '-title' | 'due_date' | '-due_date' | 'created_at' | '-created_at' | 'updated_at' | '-updated_at'

export interface TaskFilters {
  category?: string
  completed?: boolean
  search?: string
  ordering?: TaskOrdering
  due_date_before?: string
  due_date_after?: string
  created_before?: string
  created_after?: string
}

function buildParams(filters: TaskFilters): Record<string, string> {
  const params: Record<string, string> = {}
  if (filters.category) params.category = filters.category
  if (filters.completed !== undefined) params.completed = String(filters.completed)
  if (filters.search) params.search = filters.search
  if (filters.ordering) params.ordering = filters.ordering
  if (filters.due_date_before) params.due_date_before = filters.due_date_before
  if (filters.due_date_after) params.due_date_after = filters.due_date_after
  if (filters.created_before) params.created_before = filters.created_before
  if (filters.created_after) params.created_after = filters.created_after
  return params
}

export async function listTasks(filters: TaskFilters = {}): Promise<PaginatedResponse<Task>> {
  const { data } = await api.get<PaginatedResponse<Task>>('/tasks/', { params: buildParams(filters) })
  return data
}

export async function listTasksByUrl(url: string): Promise<PaginatedResponse<Task>> {
  const { data } = await api.get<PaginatedResponse<Task>>(url)
  return data
}

export async function createTask(payload: TaskPayload): Promise<Task> {
  const { data } = await api.post<Task>('/tasks/', payload)
  return data
}

export async function updateTask(id: number, payload: Partial<TaskPayload>): Promise<Task> {
  const { data } = await api.patch<Task>(`/tasks/${id}/`, payload)
  return data
}

export async function deleteTask(id: number): Promise<void> {
  await api.delete(`/tasks/${id}/`)
}
