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

export interface TaskFilters {
  category?: string
  completed?: boolean
}

export async function listTasks(filters: TaskFilters = {}): Promise<PaginatedResponse<Task>> {
  const params: Record<string, string> = {}
  if (filters.category) params.category = filters.category
  if (filters.completed !== undefined) params.completed = String(filters.completed)

  const { data } = await api.get<PaginatedResponse<Task>>('/tasks/', { params })
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
