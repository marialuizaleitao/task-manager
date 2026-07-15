import { useEffect, useState, type FormEvent } from 'react'
import type { Category } from '../services/categories'
import type { Task, TaskPayload } from '../services/tasks'

interface TaskFormProps {
  initialValue?: Task | null
  categories: Category[]
  onSubmit: (payload: TaskPayload) => Promise<void>
  onCancel?: () => void
}

export function TaskForm({ initialValue, categories, onSubmit, onCancel }: TaskFormProps) {
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [category, setCategory] = useState('')
  const [dueDate, setDueDate] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)

  useEffect(() => {
    setTitle(initialValue?.title ?? '')
    setDescription(initialValue?.description ?? '')
    setCategory(initialValue?.category ? String(initialValue.category) : '')
    setDueDate(initialValue?.due_date ?? '')
  }, [initialValue])

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    setError(null)
    setIsSubmitting(true)

    try {
      await onSubmit({
        title,
        description,
        category: category ? Number(category) : null,
        due_date: dueDate || null,
      })
      if (!initialValue) {
        setTitle('')
        setDescription('')
        setCategory('')
        setDueDate('')
      }
    } catch {
      setError('Não foi possível salvar a tarefa. Verifique os dados informados.')
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="task-form">
      <label>
        Título
        <input value={title} onChange={(event) => setTitle(event.target.value)} required />
      </label>
      <label>
        Descrição
        <input value={description} onChange={(event) => setDescription(event.target.value)} />
      </label>
      <label>
        Categoria
        <select value={category} onChange={(event) => setCategory(event.target.value)}>
          <option value="">Sem categoria</option>
          {categories.map((item) => (
            <option key={item.id} value={item.id}>
              {item.name}
            </option>
          ))}
        </select>
      </label>
      <label>
        Data de vencimento
        <input type="date" value={dueDate} onChange={(event) => setDueDate(event.target.value)} />
      </label>
      {error && <p className="error">{error}</p>}
      <div className="form-actions">
        <button type="submit" disabled={isSubmitting}>
          {initialValue ? 'Salvar' : 'Criar tarefa'}
        </button>
        {onCancel && (
          <button type="button" onClick={onCancel}>
            Cancelar
          </button>
        )}
      </div>
    </form>
  )
}
