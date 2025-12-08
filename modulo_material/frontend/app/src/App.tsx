import { useState, useEffect, type FormEvent, type ChangeEvent } from 'react'

const API_BASE = 'http://127.0.0.1:8080'

interface Material {
  id: number
  title: string
  subject_id: string
  logical_type: string
  file_path: string
  original_name: string
  mime_type: string
  description: string
  created_at: string
}

function App() {
  const [materials, setMaterials] = useState<Material[]>([])
  const [loading, setLoading] = useState(true)
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Form state
  const [subjectId, setSubjectId] = useState('')
  const [title, setTitle] = useState('')
  const [logicalType, setLogicalType] = useState('documento')
  const [description, setDescription] = useState('')
  const [file, setFile] = useState<File | null>(null)

  const fetchMaterials = async () => {
    try {
      setLoading(true)
      const res = await fetch(`${API_BASE}/api/material`)
      if (!res.ok) throw new Error('Error al cargar materiales')
      const data = await res.json()
      setMaterials(data)
      setError(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error desconocido')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchMaterials()
  }, [])

  const handleFileChange = (e: ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0])
    }
  }

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    if (!file) {
      setError('Selecciona un archivo')
      return
    }

    const formData = new FormData()
    formData.append('subject_id', subjectId)
    formData.append('title', title)
    formData.append('logical_type', logicalType)
    formData.append('description', description)
    formData.append('file', file)

    try {
      setUploading(true)
      const res = await fetch(`${API_BASE}/api/material/upload`, {
        method: 'POST',
        body: formData,
      })
      if (!res.ok) throw new Error('Error al subir archivo')

      // Reset form
      setSubjectId('')
      setTitle('')
      setLogicalType('documento')
      setDescription('')
      setFile(null)

      // Refresh list
      await fetchMaterials()
      setError(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error al subir')
    } finally {
      setUploading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 to-slate-800 p-8">
      <header className="mb-8 text-center">
        <h1 className="text-4xl font-bold text-white mb-2">Módulo de Entrenamiento</h1>
        <p className="text-slate-400">Frontend React + Backend Go</p>
      </header>

      <main className="max-w-4xl mx-auto space-y-8">
        {/* Upload Form */}
        <div className="bg-white/10 backdrop-blur-lg rounded-2xl shadow-xl p-6 border border-white/20">
          <h2 className="text-xl font-semibold mb-4 text-white">Subir Material</h2>

          {error && (
            <div className="bg-red-500/20 border border-red-500 text-red-200 px-4 py-2 rounded-lg mb-4">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-1">Asignatura (ID)</label>
                <input
                  type="text"
                  value={subjectId}
                  onChange={(e) => setSubjectId(e.target.value)}
                  className="w-full px-4 py-2 bg-white/10 border border-white/20 rounded-lg text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="ej: matematicas-101"
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-1">Título</label>
                <input
                  type="text"
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  className="w-full px-4 py-2 bg-white/10 border border-white/20 rounded-lg text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="Nombre del material"
                  required
                />
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-slate-300 mb-1">Tipo</label>
              <select
                value={logicalType}
                onChange={(e) => setLogicalType(e.target.value)}
                className="w-full px-4 py-2 bg-white/10 border border-white/20 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="documento" className="bg-slate-800">Documento</option>
                <option value="video" className="bg-slate-800">Video</option>
                <option value="codigo" className="bg-slate-800">Código</option>
                <option value="presentacion" className="bg-slate-800">Presentación</option>
                <option value="otro" className="bg-slate-800">Otro</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-slate-300 mb-1">Descripción</label>
              <textarea
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                className="w-full px-4 py-2 bg-white/10 border border-white/20 rounded-lg text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="Descripción opcional del material"
                rows={2}
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-slate-300 mb-1">Archivo</label>
              <input
                type="file"
                onChange={handleFileChange}
                className="w-full px-4 py-2 bg-white/10 border border-white/20 rounded-lg text-white file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:bg-blue-500 file:text-white hover:file:bg-blue-600"
              />
            </div>

            <button
              type="submit"
              disabled={uploading}
              className="w-full py-3 px-4 bg-gradient-to-r from-blue-500 to-purple-600 text-white font-semibold rounded-lg hover:from-blue-600 hover:to-purple-700 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50 transition-all duration-200"
            >
              {uploading ? 'Subiendo...' : 'Subir Material'}
            </button>
          </form>
        </div>

        {/* Materials List */}
        <div className="bg-white/10 backdrop-blur-lg rounded-2xl shadow-xl p-6 border border-white/20">
          <h2 className="text-xl font-semibold mb-4 text-white">Material Disponible</h2>

          {loading ? (
            <p className="text-slate-400">Cargando materiales...</p>
          ) : materials.length === 0 ? (
            <p className="text-slate-400">No hay materiales. ¡Sube el primero!</p>
          ) : (
            <div className="space-y-4">
              {materials.map((m) => (
                <div key={m.id} className="bg-white/5 rounded-xl p-4 border border-white/10 hover:bg-white/10 transition-colors">
                  <div className="flex justify-between items-start">
                    <div>
                      <h3 className="text-lg font-medium text-white">{m.title}</h3>
                      <p className="text-sm text-slate-400">{m.subject_id} • {m.logical_type}</p>
                      {m.description && <p className="text-slate-300 mt-2">{m.description}</p>}
                    </div>
                    <span className="text-xs bg-blue-500/20 text-blue-300 px-2 py-1 rounded-full">
                      {m.original_name}
                    </span>
                  </div>
                  <p className="text-xs text-slate-500 mt-2">{new Date(m.created_at).toLocaleString()}</p>
                </div>
              ))}
            </div>
          )}
        </div>
      </main>
    </div>
  )
}

export default App
