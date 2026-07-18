import type { Category } from '../services/categories'

interface CategoryListProps {
  categories: Category[]
  onEdit: (category: Category) => void
  onDelete: (category: Category) => void
}

export function CategoryList({ categories, onEdit, onDelete }: CategoryListProps) {
  if (categories.length === 0) {
    return <p className="empty-state">Nenhuma categoria cadastrada ainda. Use o formulário acima para criar a primeira.</p>
  }

  return (
    <ul className="category-list">
      {categories.map((category) => (
        <li key={category.id} className="category-item">
          <span className="category-swatch" style={{ backgroundColor: category.color }} />
          <div className="category-info">
            <strong>{category.name}</strong>
            {category.description && <p>{category.description}</p>}
          </div>
          <div className="category-actions">
            <button type="button" onClick={() => onEdit(category)}>
              Editar
            </button>
            <button type="button" onClick={() => onDelete(category)}>
              Excluir
            </button>
          </div>
        </li>
      ))}
    </ul>
  )
}
