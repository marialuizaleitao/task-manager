import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { GoogleCalendarPanel } from '../components/GoogleCalendarPanel'
import { TaskForm } from '../components/TaskForm'
import { TaskList } from '../components/TaskList'
import * as categoriesService from '../services/categories'
import type { Category } from '../services/categories'
import * as tasksService from '../services/tasks'
import type { Task, TaskFilters, TaskOrdering, TaskPayload } from '../services/tasks'

const EMPTY_FILTERS = {
  search: '',
  category: '',
  completed: '',
  ordering: '' as TaskOrdering | '',
  dueDateAfter: '',
  dueDateBefore: '',
  createdAfter: '',
  createdBefore: '',
}

type FilterState = typeof EMPTY_FILTERS

const ACTIVE_FILTER_LABELS: Record<keyof Omit<FilterState, 'ordering'>, string> = {
  search: 'Busca',
  category: 'Categoria',
  completed: 'Status',
  dueDateAfter: 'Vencimento a partir de',
  dueDateBefore: 'Vencimento até',
  createdAfter: 'Criada a partir de',
  createdBefore: 'Criada até',
}

export function TasksPage() {
  const [tasks, setTasks] = useState<Task[]>([])
  const [categories, setCategories] = useState<Category[]>([])
  const [nextPageUrl, setNextPageUrl] = useState<string | null>(null)
  const [previousPageUrl, setPreviousPageUrl] = useState<string | null>(null)
  const [filters, setFilters] = useState<FilterState>(EMPTY_FILTERS)
  const [editingTask, setEditingTask] = useState<Task | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  function buildApiFilters(state: FilterState): TaskFilters {
    const apiFilters: TaskFilters = {}
    if (state.search) apiFilters.search = state.search
    if (state.category) apiFilters.category = state.category
    if (state.completed) apiFilters.completed = state.completed === 'true'
    if (state.ordering) apiFilters.ordering = state.ordering
    if (state.dueDateAfter) apiFilters.due_date_after = state.dueDateAfter
    if (state.dueDateBefore) apiFilters.due_date_before = state.dueDateBefore
    if (state.createdAfter) apiFilters.created_after = state.createdAfter
    if (state.createdBefore) apiFilters.created_before = state.createdBefore
    return apiFilters
  }

  async function loadTasks(state: FilterState) {
    setIsLoading(true)
    setError(null)
    try {
      const data = await tasksService.listTasks(buildApiFilters(state))
      setTasks(data.results)
      setNextPageUrl(data.next)
      setPreviousPageUrl(data.previous)
    } catch {
      setError('Não foi possível carregar as tarefas.')
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    categoriesService.listCategories().then((data) => setCategories(data.results))
    loadTasks(EMPTY_FILTERS)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  function updateFilter<K extends keyof FilterState>(key: K, value: FilterState[K]) {
    setFilters((current) => ({ ...current, [key]: value }))
  }

  async function handleApplyFilters() {
    await loadTasks(filters)
  }

  async function handleClearFilters() {
    setFilters(EMPTY_FILTERS)
    await loadTasks(EMPTY_FILTERS)
  }

  async function handleRemoveFilter(key: keyof Omit<FilterState, 'ordering'>) {
    const next = { ...filters, [key]: '' }
    setFilters(next)
    await loadTasks(next)
  }

  async function handleGoToPage(url: string | null) {
    if (!url) return
    setIsLoading(true)
    try {
      const data = await tasksService.listTasksByUrl(url)
      setTasks(data.results)
      setNextPageUrl(data.next)
      setPreviousPageUrl(data.previous)
    } finally {
      setIsLoading(false)
    }
  }

  async function handleCreateOrUpdate(payload: TaskPayload) {
    if (editingTask) {
      const updated = await tasksService.updateTask(editingTask.id, payload)
      setTasks((current) => current.map((task) => (task.id === updated.id ? updated : task)))
      setEditingTask(null)
    } else {
      const created = await tasksService.createTask(payload)
      setTasks((current) => [created, ...current])
    }
  }

  async function handleToggleCompleted(task: Task) {
    const updated = await tasksService.updateTask(task.id, { completed: !task.completed })
    setTasks((current) => current.map((item) => (item.id === updated.id ? updated : item)))
  }

  async function handleDelete(task: Task) {
    const confirmed = window.confirm(`Excluir a tarefa "${task.title}"?`)
    if (!confirmed) return

    await tasksService.deleteTask(task.id)
    setTasks((current) => current.filter((item) => item.id !== task.id))
  }

  const activeFilterEntries = (Object.keys(ACTIVE_FILTER_LABELS) as Array<keyof typeof ACTIVE_FILTER_LABELS>)
    .filter((key) => filters[key])
    .map((key) => ({ key, label: ACTIVE_FILTER_LABELS[key], value: filters[key] }))

  return (
    <main className="tasks-page">
      <p>
        <Link to="/">Voltar</Link>
      </p>
      <h1>Tarefas</h1>

      <GoogleCalendarPanel />

      <TaskForm
        key={editingTask?.id ?? 'new'}
        initialValue={editingTask}
        categories={categories}
        onSubmit={handleCreateOrUpdate}
        onCancel={editingTask ? () => setEditingTask(null) : undefined}
      />

      <div className="filter-form">
        <label>
          Buscar
          <input
            type="text"
            placeholder="Título ou descrição"
            value={filters.search}
            onChange={(event) => updateFilter('search', event.target.value)}
          />
        </label>
        <label>
          Categoria
          <select value={filters.category} onChange={(event) => updateFilter('category', event.target.value)}>
            <option value="">Todas</option>
            <option value="none">Sem categoria</option>
            {categories.map((item) => (
              <option key={item.id} value={item.id}>
                {item.name}
              </option>
            ))}
          </select>
        </label>
        <label>
          Status
          <select value={filters.completed} onChange={(event) => updateFilter('completed', event.target.value)}>
            <option value="">Todas</option>
            <option value="true">Concluídas</option>
            <option value="false">Pendentes</option>
          </select>
        </label>
        <label>
          Ordenar por
          <select
            value={filters.ordering}
            onChange={(event) => updateFilter('ordering', event.target.value as TaskOrdering | '')}
          >
            <option value="">Mais recentes</option>
            <option value="title">Título (A-Z)</option>
            <option value="-title">Título (Z-A)</option>
            <option value="due_date">Vencimento (mais próximo)</option>
            <option value="-due_date">Vencimento (mais distante)</option>
            <option value="-updated_at">Atualizada recentemente</option>
          </select>
        </label>
      </div>

      <div className="filter-form">
        <label>
          Vencimento a partir de
          <input
            type="date"
            value={filters.dueDateAfter}
            onChange={(event) => updateFilter('dueDateAfter', event.target.value)}
          />
        </label>
        <label>
          Vencimento até
          <input
            type="date"
            value={filters.dueDateBefore}
            onChange={(event) => updateFilter('dueDateBefore', event.target.value)}
          />
        </label>
        <label>
          Criada a partir de
          <input
            type="date"
            value={filters.createdAfter}
            onChange={(event) => updateFilter('createdAfter', event.target.value)}
          />
        </label>
        <label>
          Criada até
          <input
            type="date"
            value={filters.createdBefore}
            onChange={(event) => updateFilter('createdBefore', event.target.value)}
          />
        </label>
        <button type="button" onClick={handleApplyFilters}>
          Filtrar
        </button>
        <button type="button" onClick={handleClearFilters}>
          Limpar filtros
        </button>
      </div>

      {activeFilterEntries.length > 0 && (
        <ul className="active-filters">
          {activeFilterEntries.map(({ key, label, value }) => (
            <li key={key}>
              <span>
                {label}: {value}
              </span>
              <button type="button" onClick={() => handleRemoveFilter(key)}>
                Remover
              </button>
            </li>
          ))}
        </ul>
      )}

      {error && <p className="error">{error}</p>}
      {isLoading ? (
        <p>Carregando...</p>
      ) : (
        <>
          <TaskList
            tasks={tasks}
            categories={categories}
            onToggleCompleted={handleToggleCompleted}
            onEdit={setEditingTask}
            onDelete={handleDelete}
          />
          <div className="pagination-nav">
            <button type="button" disabled={!previousPageUrl} onClick={() => handleGoToPage(previousPageUrl)}>
              Anterior
            </button>
            <button type="button" disabled={!nextPageUrl} onClick={() => handleGoToPage(nextPageUrl)}>
              Próxima
            </button>
          </div>
        </>
      )}
    </main>
  )
}
