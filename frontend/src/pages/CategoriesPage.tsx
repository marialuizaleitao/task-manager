import { useEffect, useState, type FormEvent } from 'react'
import { CategoryForm } from '../components/CategoryForm'
import { CategoryList } from '../components/CategoryList'
import { NavBar } from '../components/NavBar'
import * as categoriesService from '../services/categories'
import type { Category, CategoryPayload } from '../services/categories'

export function CategoriesPage() {
  const [categories, setCategories] = useState<Category[]>([])
  const [nextPageUrl, setNextPageUrl] = useState<string | null>(null)
  const [nameFilter, setNameFilter] = useState('')
  const [editingCategory, setEditingCategory] = useState<Category | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  async function loadCategories(filter: string) {
    setIsLoading(true)
    setError(null)
    try {
      const data = await categoriesService.listCategories(filter || undefined)
      setCategories(data.results)
      setNextPageUrl(data.next)
    } catch {
      setError('Não foi possível carregar as categorias.')
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    loadCategories('')
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  async function handleLoadMore() {
    if (!nextPageUrl) return
    const data = await categoriesService.listCategoriesByUrl(nextPageUrl)
    setCategories((current) => [...current, ...data.results])
    setNextPageUrl(data.next)
  }

  async function handleFilterSubmit(event: FormEvent) {
    event.preventDefault()
    await loadCategories(nameFilter)
  }

  async function handleCreateOrUpdate(payload: CategoryPayload) {
    if (editingCategory) {
      const updated = await categoriesService.updateCategory(editingCategory.id, payload)
      setCategories((current) => current.map((category) => (category.id === updated.id ? updated : category)))
      setEditingCategory(null)
    } else {
      const created = await categoriesService.createCategory(payload)
      setCategories((current) => [created, ...current])
    }
  }

  async function handleDelete(category: Category) {
    const confirmed = window.confirm(`Excluir a categoria "${category.name}"?`)
    if (!confirmed) return

    await categoriesService.deleteCategory(category.id)
    setCategories((current) => current.filter((item) => item.id !== category.id))
  }

  return (
    <>
      <NavBar />
      <main className="categories-page">
        <h1>Categorias</h1>

        <CategoryForm
          key={editingCategory?.id ?? 'new'}
          initialValue={editingCategory}
          onSubmit={handleCreateOrUpdate}
          onCancel={editingCategory ? () => setEditingCategory(null) : undefined}
        />

        <form onSubmit={handleFilterSubmit} className="filter-form">
          <input
            placeholder="Filtrar por nome"
            value={nameFilter}
            onChange={(event) => setNameFilter(event.target.value)}
          />
          <button type="submit">Filtrar</button>
        </form>

        {error && <p className="error">{error}</p>}
        {isLoading ? (
          <p className="loading-state">Carregando...</p>
        ) : (
          <>
            <CategoryList categories={categories} onEdit={setEditingCategory} onDelete={handleDelete} />
            {nextPageUrl && (
              <button type="button" onClick={handleLoadMore}>
                Carregar mais
              </button>
            )}
          </>
        )}
      </main>
    </>
  )
}
