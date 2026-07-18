import { useEffect, useState, type FormEvent } from 'react'
import { extractFieldErrors } from '../services/api'
import type { Category, CategoryPayload } from '../services/categories'

interface CategoryFormProps {
  initialValue?: Category | null
  onSubmit: (payload: CategoryPayload) => Promise<void>
  onCancel?: () => void
}

interface FieldErrors {
  name?: string
  non_field_errors?: string
}

function validateName(value: string): string | undefined {
  if (!value.trim()) return 'Informe um nome para a categoria.'
  return undefined
}

export function CategoryForm({ initialValue, onSubmit, onCancel }: CategoryFormProps) {
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [color, setColor] = useState('#1a73e8')
  const [fieldErrors, setFieldErrors] = useState<FieldErrors>({})
  const [successMessage, setSuccessMessage] = useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)

  useEffect(() => {
    setName(initialValue?.name ?? '')
    setDescription(initialValue?.description ?? '')
    setColor(initialValue?.color ?? '#1a73e8')
    setFieldErrors({})
    setSuccessMessage(null)
  }, [initialValue])

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()

    const nameError = validateName(name)
    setFieldErrors({ name: nameError })
    if (nameError) return

    setSuccessMessage(null)
    setIsSubmitting(true)
    try {
      await onSubmit({ name, description, color })
      setSuccessMessage(initialValue ? 'Categoria atualizada.' : 'Categoria criada.')
      if (!initialValue) {
        setName('')
        setDescription('')
        setColor('#1a73e8')
      }
    } catch (err) {
      setFieldErrors(extractFieldErrors(err))
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="category-form" noValidate>
      <label>
        Nome <span className="required-marker">*</span>
        <input
          value={name}
          placeholder="Ex.: Trabalho"
          onChange={(event) => setName(event.target.value)}
          onBlur={() => setFieldErrors((current) => ({ ...current, name: validateName(name) }))}
        />
        {fieldErrors.name && <span className="field-error">{fieldErrors.name}</span>}
      </label>
      <label>
        Descrição
        <input value={description} onChange={(event) => setDescription(event.target.value)} />
      </label>
      <label>
        Cor <span className="required-marker">*</span>
        <input
          type="color"
          value={color}
          onChange={(event) => setColor(event.target.value)}
          required
        />
      </label>
      {fieldErrors.non_field_errors && <p className="error">{fieldErrors.non_field_errors}</p>}
      {successMessage && <p className="field-success">{successMessage}</p>}
      <div className="form-actions">
        <button type="submit" className={isSubmitting ? 'btn-loading' : undefined} disabled={isSubmitting}>
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
