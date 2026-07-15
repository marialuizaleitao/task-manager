import { Link } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'
import { useHealthCheck } from '../hooks/useHealthCheck'

const statusLabel = {
  checking: 'Verificando conexão com a API...',
  online: 'API conectada',
  offline: 'API indisponível',
}

export function HomePage() {
  const { user, logout } = useAuth()
  const connectionState = useHealthCheck()

  return (
    <main className="app">
      <h1>Task Manager</h1>
      <p>Bem-vindo, {user?.first_name || user?.email}.</p>
      <p className={`status status--${connectionState}`}>{statusLabel[connectionState]}</p>
      <p>
        <Link to="/tasks">Minhas tarefas</Link>
      </p>
      <p>
        <Link to="/categories">Gerenciar categorias</Link>
      </p>
      <button type="button" onClick={() => logout()}>
        Sair
      </button>
    </main>
  )
}
