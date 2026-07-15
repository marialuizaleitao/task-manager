import { api } from './api'
import type { PaginatedResponse } from './pagination'

export interface Category {
  id: number
  name: string
  description: string
  color: string
  created_at: string
  updated_at: string
}

export interface CategoryPayload {
  name: string
  description?: string
  color: string
}

export async function listCategories(nameFilter?: string): Promise<PaginatedResponse<Category>> {
  const { data } = await api.get<PaginatedResponse<Category>>('/categories/', {
    params: nameFilter ? { name: nameFilter } : undefined,
  })
  return data
}

export async function listCategoriesByUrl(url: string): Promise<PaginatedResponse<Category>> {
  const { data } = await api.get<PaginatedResponse<Category>>(url)
  return data
}

export async function createCategory(payload: CategoryPayload): Promise<Category> {
  const { data } = await api.post<Category>('/categories/', payload)
  return data
}

export async function updateCategory(id: number, payload: CategoryPayload): Promise<Category> {
  const { data } = await api.patch<Category>(`/categories/${id}/`, payload)
  return data
}

export async function deleteCategory(id: number): Promise<void> {
  await api.delete(`/categories/${id}/`)
}
