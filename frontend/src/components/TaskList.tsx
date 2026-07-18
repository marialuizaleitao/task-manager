import { useState } from 'react'
import type { Category } from '../services/categories'
import type { Task } from '../services/tasks'
import { TaskShareManager } from './TaskShareManager'

interface TaskListProps {
  tasks: Task[]
  categories: Category[]
  onToggleCompleted: (task: Task) => void
  onEdit: (task: Task) => void
  onDelete: (task: Task) => void
}

export function TaskList({ tasks, categories, onToggleCompleted, onEdit, onDelete }: TaskListProps) {
  const [expandedShareTaskId, setExpandedShareTaskId] = useState<number | null>(null)

  if (tasks.length === 0) {
    return <p className="empty-state">Nenhuma tarefa cadastrada ainda.</p>
  }

  function categoryName(categoryId: number | null): string | null {
    if (!categoryId) return null
    return categories.find((item) => item.id === categoryId)?.name ?? null
  }

  function toggleShareManager(taskId: number) {
    setExpandedShareTaskId((current) => (current === taskId ? null : taskId))
  }

  return (
    <ul className="task-list">
      {tasks.map((task) => (
        <li key={task.id} className={`task-item ${task.completed ? 'task-item--completed' : ''}`}>
          <div className="task-item-row">
            <input type="checkbox" checked={task.completed} onChange={() => onToggleCompleted(task)} />
            <div className="task-info">
              <strong>{task.title}</strong>
              {task.completed && <span className="status status--online">Concluída</span>}
              {task.description && <p>{task.description}</p>}
              <p className="task-meta">
                {categoryName(task.category) && <span>{categoryName(task.category)}</span>}
                {task.due_date && <span>Vence em {task.due_date}</span>}
              </p>
            </div>
            <div className="task-actions">
              <button type="button" onClick={() => onEdit(task)}>
                Editar
              </button>
              <button type="button" onClick={() => toggleShareManager(task.id)}>
                Compartilhar
              </button>
              <button type="button" onClick={() => onDelete(task)}>
                Excluir
              </button>
            </div>
          </div>
          {expandedShareTaskId === task.id && <TaskShareManager taskId={task.id} />}
        </li>
      ))}
    </ul>
  )
}
