import { Link } from 'react-router-dom'
import { NavBar } from '../components/NavBar'
import { useAuth } from '../hooks/useAuth'
import { useHealthCheck } from '../hooks/useHealthCheck'

const statusLabel = {
  checking: 'Verificando conexão com a API...',
  online: 'API conectada',
  offline: 'API indisponível',
}

export function HomePage() {
  const { user } = useAuth()
  const connectionState = useHealthCheck()

  return (
    <>
      <NavBar />
      <main className="app">
        <h1>Bem-vindo, {user?.first_name || user?.email}.</h1>
        <p className={`status status--${connectionState}`}>{statusLabel[connectionState]}</p>
        <p>
          <Link to="/tasks">Minhas tarefas</Link>
        </p>
        <p>
          <Link to="/shared-tasks">Tarefas compartilhadas comigo</Link>
        </p>
        <p>
          <Link to="/categories">Gerenciar categorias</Link>
        </p>
      </main>
    </>
  )
}
