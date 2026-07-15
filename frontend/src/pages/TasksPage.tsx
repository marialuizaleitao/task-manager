import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { TaskForm } from '../components/TaskForm'
import { TaskList } from '../components/TaskList'
import * as categoriesService from '../services/categories'
import type { Category } from '../services/categories'
import * as tasksService from '../services/tasks'
import type { Task, TaskFilters, TaskPayload } from '../services/tasks'

export function TasksPage() {
  const [tasks, setTasks] = useState<Task[]>([])
  const [categories, setCategories] = useState<Category[]>([])
  const [nextPageUrl, setNextPageUrl] = useState<string | null>(null)
  const [categoryFilter, setCategoryFilter] = useState('')
  const [completedFilter, setCompletedFilter] = useState('')
  const [editingTask, setEditingTask] = useState<Task | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  async function loadCategories() {
    const data = await categoriesService.listCategories()
    setCategories(data.results)
  }

  async function loadTasks(filters: TaskFilters) {
    setIsLoading(true)
    setError(null)
    try {
      const data = await tasksService.listTasks(filters)
      setTasks(data.results)
      setNextPageUrl(data.next)
    } catch {
      setError('Não foi possível carregar as tarefas.')
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    loadCategories()
    loadTasks({})
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  function buildFilters(): TaskFilters {
    const filters: TaskFilters = {}
    if (categoryFilter) filters.category = categoryFilter
    if (completedFilter) filters.completed = completedFilter === 'true'
    return filters
  }

  async function handleFilterChange() {
    await loadTasks(buildFilters())
  }

  async function handleLoadMore() {
    if (!nextPageUrl) return
    const data = await tasksService.listTasksByUrl(nextPageUrl)
    setTasks((current) => [...current, ...data.results])
    setNextPageUrl(data.next)
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

  return (
    <main className="tasks-page">
      <p>
        <Link to="/">Voltar</Link>
      </p>
      <h1>Tarefas</h1>

      <TaskForm
        key={editingTask?.id ?? 'new'}
        initialValue={editingTask}
        categories={categories}
        onSubmit={handleCreateOrUpdate}
        onCancel={editingTask ? () => setEditingTask(null) : undefined}
      />

      <div className="filters">
        <label>
          Categoria
          <select value={categoryFilter} onChange={(event) => setCategoryFilter(event.target.value)}>
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
          <select value={completedFilter} onChange={(event) => setCompletedFilter(event.target.value)}>
            <option value="">Todas</option>
            <option value="true">Concluídas</option>
            <option value="false">Pendentes</option>
          </select>
        </label>
        <button type="button" onClick={handleFilterChange}>
          Filtrar
        </button>
      </div>

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
          {nextPageUrl && (
            <button type="button" onClick={handleLoadMore}>
              Carregar mais
            </button>
          )}
        </>
      )}
    </main>
  )
}
