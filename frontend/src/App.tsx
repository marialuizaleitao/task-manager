import { useHealthCheck } from './hooks/useHealthCheck'
import './App.css'

const statusLabel = {
  checking: 'Verificando conexão com a API...',
  online: 'API conectada',
  offline: 'API indisponível',
}

function App() {
  const connectionState = useHealthCheck()

  return (
    <main className="app">
      <h1>Task Manager</h1>
      <p className={`status status--${connectionState}`}>
        {statusLabel[connectionState]}
      </p>
    </main>
  )
}

export default App
