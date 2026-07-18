import { api } from './api'
import type { PaginatedResponse } from './pagination'
import type { Task } from './tasks'

export type SharePermission = 'read' | 'edit'

export interface SharedUser {
  id: number
  email: string
  first_name: string
  last_name: string
}

export interface TaskShare {
  id: number
  shared_with: SharedUser
  permission: SharePermission
  created_at: string
}

export interface SharedTask extends Task {
  owner: SharedUser
  permission: SharePermission
}

export async function listTaskShares(taskId: number): Promise<TaskShare[]> {
  const { data } = await api.get<TaskShare[]>(`/tasks/${taskId}/shares/`)
  return data
}

export async function createTaskShare(
  taskId: number,
  email: string,
  permission: SharePermission,
): Promise<TaskShare> {
  const { data } = await api.post<TaskShare>(`/tasks/${taskId}/shares/`, { email, permission })
  return data
}

export async function deleteTaskShare(taskId: number, shareId: number): Promise<void> {
  await api.delete(`/tasks/${taskId}/shares/${shareId}/`)
}

export async function listSharedTasks(): Promise<PaginatedResponse<SharedTask>> {
  const { data } = await api.get<PaginatedResponse<SharedTask>>('/shared-tasks/')
  return data
}

export async function listSharedTasksByUrl(url: string): Promise<PaginatedResponse<SharedTask>> {
  const { data } = await api.get<PaginatedResponse<SharedTask>>(url)
  return data
}
