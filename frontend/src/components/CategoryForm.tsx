import { useEffect, useState, type FormEvent } from 'react'
import type { Category, CategoryPayload } from '../services/categories'

interface CategoryFormProps {
  initialValue?: Category | null
  onSubmit: (payload: CategoryPayload) => Promise<void>
  onCancel?: () => void
}

export function CategoryForm({ initialValue, onSubmit, onCancel }: CategoryFormProps) {
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [color, setColor] = useState('#1a73e8')
  const [error, setError] = useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)

  useEffect(() => {
    setName(initialValue?.name ?? '')
    setDescription(initialValue?.description ?? '')
    setColor(initialValue?.color ?? '#1a73e8')
  }, [initialValue])

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    setError(null)
    setIsSubmitting(true)

    try {
      await onSubmit({ name, description, color })
      if (!initialValue) {
        setName('')
        setDescription('')
        setColor('#1a73e8')
      }
    } catch {
      setError('Não foi possível salvar a categoria. Verifique os dados informados.')
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="category-form">
      <label>
        Nome
        <input value={name} onChange={(event) => setName(event.target.value)} required />
      </label>
      <label>
        Descrição
        <input value={description} onChange={(event) => setDescription(event.target.value)} />
      </label>
      <label>
        Cor
        <input
          type="color"
          value={color}
          onChange={(event) => setColor(event.target.value)}
          required
        />
      </label>
      {error && <p className="error">{error}</p>}
      <div className="form-actions">
        <button type="submit" disabled={isSubmitting}>
          {initialValue ? 'Salvar' : 'Criar categoria'}
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
