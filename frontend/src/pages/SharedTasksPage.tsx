import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { TaskForm } from '../components/TaskForm'
import * as categoriesService from '../services/categories'
import type { Category } from '../services/categories'
import * as sharingService from '../services/sharing'
import type { SharedTask } from '../services/sharing'
import * as tasksService from '../services/tasks'
import type { TaskPayload } from '../services/tasks'

export function SharedTasksPage() {
  const [tasks, setTasks] = useState<SharedTask[]>([])
  const [categories, setCategories] = useState<Category[]>([])
  const [nextPageUrl, setNextPageUrl] = useState<string | null>(null)
  const [editingTaskId, setEditingTaskId] = useState<number | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  async function loadTasks() {
    setIsLoading(true)
    setError(null)
    try {
      const data = await sharingService.listSharedTasks()
      setTasks(data.results)
      setNextPageUrl(data.next)
    } catch {
      setError('Não foi possível carregar as tarefas compartilhadas.')
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    categoriesService.listCategories().then((data) => setCategories(data.results))
    loadTasks()
  }, [])

  async function handleLoadMore() {
    if (!nextPageUrl) return
    const data = await sharingService.listSharedTasksByUrl(nextPageUrl)
    setTasks((current) => [...current, ...data.results])
    setNextPageUrl(data.next)
  }

  async function handleToggleCompleted(task: SharedTask) {
    const updated = await tasksService.updateTask(task.id, { completed: !task.completed })
    setTasks((current) =>
      current.map((item) => (item.id === task.id ? { ...item, ...updated } : item)),
    )
  }

  async function handleUpdate(task: SharedTask, payload: TaskPayload) {
    const updated = await tasksService.updateTask(task.id, payload)
    setTasks((current) =>
      current.map((item) => (item.id === task.id ? { ...item, ...updated } : item)),
    )
    setEditingTaskId(null)
  }

  return (
    <main className="tasks-page">
      <p>
        <Link to="/">Voltar</Link>
      </p>
      <h1>Tarefas compartilhadas comigo</h1>

      {error && <p className="error">{error}</p>}
      {isLoading ? (
        <p>Carregando...</p>
      ) : tasks.length === 0 ? (
        <p>Nenhuma tarefa foi compartilhada com você ainda.</p>
      ) : (
        <>
          <ul className="task-list">
            {tasks.map((task) => (
              <li key={task.id} className={`task-item ${task.completed ? 'task-item--completed' : ''}`}>
                <div className="task-item-row">
                  <input
                    type="checkbox"
                    checked={task.completed}
                    disabled={task.permission !== 'edit'}
                    onChange={() => handleToggleCompleted(task)}
                  />
                  <div className="task-info">
                    <strong>{task.title}</strong>
                    {task.description && <p>{task.description}</p>}
                    <p className="task-meta">
                      <span>De: {task.owner.email}</span>
                      <span>{task.permission === 'edit' ? 'Edição' : 'Leitura'}</span>
                      {task.due_date && <span>Vence em {task.due_date}</span>}
                    </p>
                  </div>
                  {task.permission === 'edit' && (
                    <div className="task-actions">
                      <button
                        type="button"
                        onClick={() => setEditingTaskId((current) => (current === task.id ? null : task.id))}
                      >
                        Editar
                      </button>
                    </div>
                  )}
                </div>
                {editingTaskId === task.id && (
                  <TaskForm
                    initialValue={task}
                    categories={categories}
                    onSubmit={(payload) => handleUpdate(task, payload)}
                    onCancel={() => setEditingTaskId(null)}
                  />
                )}
              </li>
            ))}
          </ul>
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
