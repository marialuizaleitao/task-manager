import { Link, useLocation } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'

const LINKS = [
  { to: '/', label: 'Início' },
  { to: '/tasks', label: 'Tarefas' },
  { to: '/shared-tasks', label: 'Compartilhadas' },
  { to: '/categories', label: 'Categorias' },
]

export function NavBar() {
  const { logout } = useAuth()
  const { pathname } = useLocation()

  return (
    <header className="nav-bar">
      <span className="nav-bar__brand">Task Manager</span>
      <nav className="nav-bar__links">
        {LINKS.map((link) => (
          <Link
            key={link.to}
            to={link.to}
            className={pathname === link.to ? 'nav-bar__link nav-bar__link--active' : 'nav-bar__link'}
          >
            {link.label}
          </Link>
        ))}
      </nav>
      <button type="button" className="nav-bar__logout" onClick={() => logout()}>
        Sair
      </button>
    </header>
  )
}
