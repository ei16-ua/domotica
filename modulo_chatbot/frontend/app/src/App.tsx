import { useState, type FormEvent } from 'react'
import ChatBox from './ChatBox'

const CHATBOT_API = 'http://127.0.0.1:8002'

function App() {
  const [token, setToken] = useState<string | null>(localStorage.getItem('token'))
  const [username, setUsername] = useState<string | null>(localStorage.getItem('username'))
  const [showLogin, setShowLogin] = useState(true)
  const [loginUsername, setLoginUsername] = useState('')
  const [loginPassword, setLoginPassword] = useState('')
  const [loginEmail, setLoginEmail] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  const handleLogin = async (e: FormEvent) => {
    e.preventDefault()
    setError(null)
    setLoading(true)

    try {
      const response = await fetch(`${CHATBOT_API}/api/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username: loginUsername, password: loginPassword }),
      })

      if (!response.ok) {
        const data = await response.json()
        throw new Error(data.detail || 'Error al iniciar sesión')
      }

      const data = await response.json()
      localStorage.setItem('token', data.access_token)
      localStorage.setItem('username', loginUsername)
      setToken(data.access_token)
      setUsername(loginUsername)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error desconocido')
    } finally {
      setLoading(false)
    }
  }

  const handleRegister = async (e: FormEvent) => {
    e.preventDefault()
    setError(null)
    setLoading(true)

    try {
      const response = await fetch(`${CHATBOT_API}/api/auth/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          username: loginUsername,
          password: loginPassword,
          email: loginEmail || null
        }),
      })

      if (!response.ok) {
        const data = await response.json()
        throw new Error(data.detail || 'Error al registrar')
      }

      setShowLogin(true)
      await handleLogin(e)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error desconocido')
    } finally {
      setLoading(false)
    }
  }

  const handleLogout = () => {
    localStorage.removeItem('token')
    localStorage.removeItem('username')
    setToken(null)
    setUsername(null)
  }

  // If logged in, show full-screen chat
  if (token && username) {
    return <ChatBox token={token} username={username} onLogout={handleLogout} />
  }

  // Login/Register form
  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 to-slate-800 flex items-center justify-center p-8">
      <div className="bg-white/10 backdrop-blur-lg rounded-2xl shadow-xl border border-white/20 p-8 w-full max-w-md">
        <h1 className="text-3xl font-bold text-white text-center mb-2">📚 Chat Educativo</h1>
        <p className="text-slate-400 text-center mb-6">
          {showLogin ? 'Inicia sesión para continuar' : 'Crea una cuenta nueva'}
        </p>

        {error && (
          <div className="bg-red-500/20 border border-red-500 text-red-200 px-4 py-2 rounded-lg mb-4 text-sm">
            {error}
          </div>
        )}

        <form onSubmit={showLogin ? handleLogin : handleRegister} className="space-y-4">
          <div>
            <label className="block text-sm text-slate-300 mb-1">Usuario</label>
            <input
              type="text"
              value={loginUsername}
              onChange={e => setLoginUsername(e.target.value)}
              className="w-full px-4 py-3 bg-white/10 border border-white/20 rounded-lg text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="tu_usuario"
              required
            />
          </div>

          {!showLogin && (
            <div>
              <label className="block text-sm text-slate-300 mb-1">Email (opcional)</label>
              <input
                type="email"
                value={loginEmail}
                onChange={e => setLoginEmail(e.target.value)}
                className="w-full px-4 py-3 bg-white/10 border border-white/20 rounded-lg text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="tu@email.com"
              />
            </div>
          )}

          <div>
            <label className="block text-sm text-slate-300 mb-1">Contraseña</label>
            <input
              type="password"
              value={loginPassword}
              onChange={e => setLoginPassword(e.target.value)}
              className="w-full px-4 py-3 bg-white/10 border border-white/20 rounded-lg text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="••••••••"
              required
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full py-3 bg-gradient-to-r from-blue-500 to-purple-600 text-white font-semibold rounded-lg hover:from-blue-600 hover:to-purple-700 disabled:opacity-50"
          >
            {loading ? 'Cargando...' : showLogin ? 'Iniciar sesión' : 'Registrarse'}
          </button>
        </form>

        <div className="mt-6 text-center">
          <button
            onClick={() => { setShowLogin(!showLogin); setError(null) }}
            className="text-blue-400 hover:text-blue-300 text-sm"
          >
            {showLogin ? '¿No tienes cuenta? Regístrate' : '¿Ya tienes cuenta? Inicia sesión'}
          </button>
        </div>
      </div>
    </div>
  )
}

export default App
