import { useEffect, useState, type FormEvent } from 'react'
import type { Category } from '../services/categories'
import { extractFieldErrors } from '../services/api'
import type { Task, TaskPayload } from '../services/tasks'

interface TaskFormProps {
  initialValue?: Task | null
  categories: Category[]
  onSubmit: (payload: TaskPayload) => Promise<void>
  onCancel?: () => void
}

interface FieldErrors {
  title?: string
  non_field_errors?: string
}

function validateTitle(value: string): string | undefined {
  if (!value.trim()) return 'Informe um título para a tarefa.'
  return undefined
}

export function TaskForm({ initialValue, categories, onSubmit, onCancel }: TaskFormProps) {
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [category, setCategory] = useState('')
  const [dueDate, setDueDate] = useState('')
  const [fieldErrors, setFieldErrors] = useState<FieldErrors>({})
  const [isSubmitting, setIsSubmitting] = useState(false)

  useEffect(() => {
    setTitle(initialValue?.title ?? '')
    setDescription(initialValue?.description ?? '')
    setCategory(initialValue?.category ? String(initialValue.category) : '')
    setDueDate(initialValue?.due_date ?? '')
    setFieldErrors({})
  }, [initialValue])

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()

    const titleError = validateTitle(title)
    setFieldErrors({ title: titleError })
    if (titleError) return

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
    } catch (err) {
      setFieldErrors(extractFieldErrors(err))
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="task-form" noValidate>
      <label>
        Título <span className="required-marker">*</span>
        <input
          value={title}
          placeholder="Ex.: Preparar apresentação"
          onChange={(event) => setTitle(event.target.value)}
          onBlur={() => setFieldErrors((current) => ({ ...current, title: validateTitle(title) }))}
        />
        {fieldErrors.title && <span className="field-error">{fieldErrors.title}</span>}
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
      {fieldErrors.non_field_errors && <p className="error">{fieldErrors.non_field_errors}</p>}
      <div className="form-actions">
        <button type="submit" className={isSubmitting ? 'btn-loading' : undefined} disabled={isSubmitting}>
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
