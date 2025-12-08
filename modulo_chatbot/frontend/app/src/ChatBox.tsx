import { useState, useRef, useEffect, type FormEvent, type ChangeEvent } from 'react'
import ReactMarkdown from 'react-markdown'
import rehypeRaw from 'rehype-raw'

const CHATBOT_API = 'http://127.0.0.1:8002'
const MATERIAL_API = 'http://127.0.0.1:8080'

interface Message {
    id: number
    role: 'user' | 'assistant'
    content: string
    sources?: { file: string; subject: string }[]
    created_at: string
}

interface Conversation {
    id: number
    title: string
    subject_id: string | null
    updated_at: string
}

interface ChatBoxProps {
    token: string | null
    username: string | null
    onLogout: () => void
}

export default function ChatBox({ token, username, onLogout }: ChatBoxProps) {
    const [darkMode, setDarkMode] = useState(() => {
        const saved = localStorage.getItem('darkMode')
        return saved !== null ? saved === 'true' : true
    })
    const [sidebarOpen, setSidebarOpen] = useState(false)
    const [messages, setMessages] = useState<Message[]>([])
    const [conversations, setConversations] = useState<Conversation[]>([])
    const [currentConversation, setCurrentConversation] = useState<number | null>(null)
    const [input, setInput] = useState('')
    const [loading, setLoading] = useState(false)
    const [subjectId, setSubjectId] = useState('')
    const [subjects, setSubjects] = useState<string[]>([])
    const messagesEndRef = useRef<HTMLDivElement>(null)
    const fileInputRef = useRef<HTMLInputElement>(null)

    // File upload state
    const [selectedFile, setSelectedFile] = useState<File | null>(null)
    const [showConfirmModal, setShowConfirmModal] = useState(false)
    const [showSaveModal, setShowSaveModal] = useState(false)
    const [materialTitle, setMaterialTitle] = useState('')
    const [materialSubject, setMaterialSubject] = useState('')
    const [materialDescription, setMaterialDescription] = useState('')
    const [uploadLoading, setUploadLoading] = useState(false)

    // Theme colors
    const theme = darkMode ? {
        bg: '#0f0f0f',
        bgSecondary: '#1a1a1a',
        border: '#2a2a2a',
        text: '#e0e0e0',
        textSecondary: '#888',
        textMuted: '#555',
        input: '#1a1a1a',
    } : {
        bg: '#f8fafc',
        bgSecondary: '#ffffff',
        border: '#e2e8f0',
        text: '#1e293b',
        textSecondary: '#64748b',
        textMuted: '#94a3b8',
        input: '#ffffff',
    }

    useEffect(() => {
        localStorage.setItem('darkMode', String(darkMode))
    }, [darkMode])

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
    }

    useEffect(() => {
        scrollToBottom()
    }, [messages])

    useEffect(() => {
        const fetchSubjects = async () => {
            try {
                const response = await fetch(`${MATERIAL_API}/api/material`)
                const materials = await response.json()
                const uniqueSubjects = [...new Set(materials.map((m: { subject_id: string }) => m.subject_id))] as string[]
                setSubjects(uniqueSubjects)
                if (uniqueSubjects.length > 0 && !subjectId) {
                    setSubjectId(uniqueSubjects[0])
                }
            } catch {
                console.error('Error fetching subjects')
            }
        }
        fetchSubjects()
    }, [])

    useEffect(() => {
        if (!username) return
        const fetchConversations = async () => {
            try {
                const response = await fetch(`${CHATBOT_API}/api/conversations?user_id=${username}`)
                const data = await response.json()
                setConversations(data.slice(0, 10))
            } catch {
                console.error('Error fetching conversations')
            }
        }
        fetchConversations()
    }, [username])

    const loadConversation = async (conversationId: number) => {
        try {
            const response = await fetch(`${CHATBOT_API}/api/conversations/${conversationId}/messages`)
            const data = await response.json()
            setMessages(data)
            setCurrentConversation(conversationId)
            setSidebarOpen(false)
        } catch {
            console.error('Error loading conversation')
        }
    }

    const deleteConversation = async (conversationId: number, e: React.MouseEvent) => {
        e.stopPropagation()
        if (!confirm('¿Eliminar esta conversación?')) return
        try {
            await fetch(`${CHATBOT_API}/api/conversations/${conversationId}`, { method: 'DELETE' })
            setConversations(prev => prev.filter(c => c.id !== conversationId))
            if (currentConversation === conversationId) {
                setCurrentConversation(null)
                setMessages([])
            }
        } catch {
            console.error('Error deleting conversation')
        }
    }

    const startNewConversation = () => {
        setCurrentConversation(null)
        setMessages([])
        setSidebarOpen(false)
    }

    // File upload handlers
    const handleFileSelect = (e: ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0]
        if (file && file.type === 'application/pdf') {
            setSelectedFile(file)
            setMaterialTitle(file.name.replace('.pdf', ''))
            setMaterialSubject(subjectId || '')
            setShowConfirmModal(true)
        } else if (file) {
            alert('Solo se permiten archivos PDF')
        }
        // Reset input
        if (fileInputRef.current) fileInputRef.current.value = ''
    }

    const handleConfirmNo = () => {
        setSelectedFile(null)
        setShowConfirmModal(false)
    }

    const handleConfirmYes = () => {
        setShowConfirmModal(false)
        setShowSaveModal(true)
    }

    const handleSaveMaterial = async (e: FormEvent) => {
        e.preventDefault()
        if (!selectedFile) return

        setUploadLoading(true)
        try {
            const formData = new FormData()
            formData.append('file', selectedFile)
            formData.append('title', materialTitle)
            formData.append('subject_id', materialSubject)
            formData.append('description', materialDescription)

            const response = await fetch(`${MATERIAL_API}/api/material/upload`, {
                method: 'POST',
                body: formData,
            })

            if (response.ok) {
                // Refresh subjects
                const materialsRes = await fetch(`${MATERIAL_API}/api/material`)
                const materials = await materialsRes.json()
                const uniqueSubjects = [...new Set(materials.map((m: { subject_id: string }) => m.subject_id))] as string[]
                setSubjects(uniqueSubjects)

                // Add success message to chat
                setMessages(prev => [...prev, {
                    id: Date.now(),
                    role: 'assistant',
                    content: `✅ Material guardado correctamente:\n\n**${materialTitle}**\nAsignatura: ${materialSubject}\n\n_El material será indexado automáticamente y estará disponible para consultas._`,
                    created_at: new Date().toISOString()
                }])

                // Reset
                setShowSaveModal(false)
                setSelectedFile(null)
                setMaterialTitle('')
                setMaterialSubject('')
                setMaterialDescription('')
            } else {
                throw new Error('Error al guardar')
            }
        } catch {
            alert('Error al guardar el material')
        } finally {
            setUploadLoading(false)
        }
    }

    const handleSubmit = async (e: FormEvent) => {
        e.preventDefault()
        if (!input.trim() || loading) return

        const userMessage = input.trim()
        setInput('')
        setLoading(true)

        setMessages(prev => [...prev, {
            id: Date.now(),
            role: 'user',
            content: userMessage,
            created_at: new Date().toISOString()
        }])

        try {
            const headers: Record<string, string> = { 'Content-Type': 'application/json' }
            if (token) headers['Authorization'] = `Bearer ${token}`

            const response = await fetch(`${CHATBOT_API}/api/chat`, {
                method: 'POST',
                headers,
                body: JSON.stringify({
                    message: userMessage,
                    conversation_id: currentConversation,
                    user_id: username || 'anonymous',
                    subject_id: subjectId || null,
                }),
            })
            const data = await response.json()
            setCurrentConversation(data.conversation_id)
            setMessages(prev => [...prev, {
                id: Date.now() + 1,
                role: 'assistant',
                content: data.message,
                sources: data.sources,
                created_at: new Date().toISOString()
            }])
            if (username) {
                const convResponse = await fetch(`${CHATBOT_API}/api/conversations?user_id=${username}`)
                const convData = await convResponse.json()
                setConversations(convData.slice(0, 10))
            }
        } catch {
            setMessages(prev => [...prev, {
                id: Date.now() + 1,
                role: 'assistant',
                content: '❌ Error de conexión',
                created_at: new Date().toISOString()
            }])
        } finally {
            setLoading(false)
        }
    }

    return (
        <div className="flex h-screen transition-colors duration-300" style={{ backgroundColor: theme.bg }}>
            {/* Confirm Modal */}
            {showConfirmModal && (
                <div className="fixed inset-0 bg-black/70 z-50 flex items-center justify-center p-4 backdrop-blur-sm">
                    <div className="rounded-2xl p-6 max-w-md w-full shadow-2xl" style={{ backgroundColor: theme.bgSecondary }}>
                        <div className="text-center">
                            <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-emerald-500/20 flex items-center justify-center">
                                <svg className="w-8 h-8 text-emerald-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                                </svg>
                            </div>
                            <h3 className="text-xl font-semibold mb-2" style={{ color: theme.text }}>
                                ¿Guardar este material?
                            </h3>
                            <p className="text-sm mb-6" style={{ color: theme.textSecondary }}>
                                {selectedFile?.name}
                            </p>
                            <div className="flex gap-3">
                                <button
                                    onClick={handleConfirmNo}
                                    className="flex-1 py-3 rounded-xl font-medium transition-colors"
                                    style={{ backgroundColor: theme.border, color: theme.text }}
                                >
                                    No, ignorar
                                </button>
                                <button
                                    onClick={handleConfirmYes}
                                    className="flex-1 py-3 bg-gradient-to-r from-emerald-500 to-cyan-500 text-white rounded-xl font-medium hover:from-emerald-600 hover:to-cyan-600 transition-all"
                                >
                                    Sí, guardar
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            )}

            {/* Save Material Modal */}
            {showSaveModal && (
                <div className="fixed inset-0 bg-black/70 z-50 flex items-center justify-center p-4 backdrop-blur-sm">
                    <div className="rounded-2xl p-6 max-w-lg w-full shadow-2xl" style={{ backgroundColor: theme.bgSecondary }}>
                        <h3 className="text-xl font-semibold mb-4" style={{ color: theme.text }}>
                            📚 Guardar Material
                        </h3>
                        <form onSubmit={handleSaveMaterial} className="space-y-4">
                            <div>
                                <label className="block text-sm mb-1" style={{ color: theme.textSecondary }}>Título</label>
                                <input
                                    type="text"
                                    value={materialTitle}
                                    onChange={e => setMaterialTitle(e.target.value)}
                                    className="w-full px-4 py-3 rounded-xl border focus:outline-none focus:ring-2 focus:ring-emerald-500/50"
                                    style={{ backgroundColor: theme.input, borderColor: theme.border, color: theme.text }}
                                    required
                                />
                            </div>
                            <div>
                                <label className="block text-sm mb-1" style={{ color: theme.textSecondary }}>Asignatura</label>
                                <input
                                    type="text"
                                    value={materialSubject}
                                    onChange={e => setMaterialSubject(e.target.value)}
                                    className="w-full px-4 py-3 rounded-xl border focus:outline-none focus:ring-2 focus:ring-emerald-500/50"
                                    style={{ backgroundColor: theme.input, borderColor: theme.border, color: theme.text }}
                                    placeholder="Ej: SI, IC, Matemáticas..."
                                    required
                                />
                                {subjects.length > 0 && (
                                    <div className="flex flex-wrap gap-2 mt-2">
                                        {subjects.map(s => (
                                            <button
                                                key={s}
                                                type="button"
                                                onClick={() => setMaterialSubject(s)}
                                                className={`px-3 py-1 rounded-lg text-sm transition-colors ${materialSubject === s ? 'bg-emerald-500 text-white' : ''}`}
                                                style={materialSubject !== s ? { backgroundColor: theme.border, color: theme.textSecondary } : {}}
                                            >
                                                {s}
                                            </button>
                                        ))}
                                    </div>
                                )}
                            </div>
                            <div>
                                <label className="block text-sm mb-1" style={{ color: theme.textSecondary }}>Descripción (opcional)</label>
                                <textarea
                                    value={materialDescription}
                                    onChange={e => setMaterialDescription(e.target.value)}
                                    className="w-full px-4 py-3 rounded-xl border focus:outline-none focus:ring-2 focus:ring-emerald-500/50 resize-none"
                                    style={{ backgroundColor: theme.input, borderColor: theme.border, color: theme.text }}
                                    rows={3}
                                    placeholder="Descripción del material..."
                                />
                            </div>
                            <div className="flex gap-3 pt-2">
                                <button
                                    type="button"
                                    onClick={() => { setShowSaveModal(false); setSelectedFile(null) }}
                                    className="flex-1 py-3 rounded-xl font-medium transition-colors"
                                    style={{ backgroundColor: theme.border, color: theme.text }}
                                    disabled={uploadLoading}
                                >
                                    Cancelar
                                </button>
                                <button
                                    type="submit"
                                    disabled={uploadLoading || !materialTitle || !materialSubject}
                                    className="flex-1 py-3 bg-gradient-to-r from-emerald-500 to-cyan-500 text-white rounded-xl font-medium hover:from-emerald-600 hover:to-cyan-600 transition-all disabled:opacity-50"
                                >
                                    {uploadLoading ? 'Guardando...' : 'Guardar'}
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            )}

            {/* Overlay */}
            {sidebarOpen && (
                <div
                    className="fixed inset-0 bg-black/60 z-20 lg:hidden backdrop-blur-sm"
                    onClick={() => setSidebarOpen(false)}
                />
            )}

            {/* Sidebar */}
            <div
                className={`fixed lg:relative z-30 h-full w-80 border-r transform transition-all duration-300 ease-out flex flex-col
                    ${sidebarOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0 lg:w-0 lg:overflow-hidden lg:border-0'}`}
                style={{ backgroundColor: theme.bgSecondary, borderColor: theme.border }}
            >
                {/* User Section */}
                <div className="p-5 border-b" style={{ borderColor: theme.border }}>
                    <div className="flex items-center gap-4">
                        <div className="w-11 h-11 rounded-xl bg-gradient-to-br from-emerald-400 to-cyan-500 flex items-center justify-center text-white font-bold text-lg shadow-lg shadow-emerald-500/20">
                            {username?.charAt(0).toUpperCase()}
                        </div>
                        <div className="flex-1 min-w-0">
                            <p className="font-semibold truncate" style={{ color: theme.text }}>{username}</p>
                            <p className="text-xs" style={{ color: theme.textSecondary }}>Estudiante</p>
                        </div>
                        <button
                            onClick={() => setDarkMode(!darkMode)}
                            className="p-2 rounded-lg transition-colors hover:bg-black/10"
                            title={darkMode ? 'Modo claro' : 'Modo oscuro'}
                        >
                            {darkMode ? (
                                <svg className="w-5 h-5 text-yellow-400" fill="currentColor" viewBox="0 0 24 24">
                                    <path d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z" />
                                </svg>
                            ) : (
                                <svg className="w-5 h-5 text-slate-600" fill="currentColor" viewBox="0 0 24 24">
                                    <path d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z" />
                                </svg>
                            )}
                        </button>
                    </div>
                </div>

                {/* Subject Selector */}
                <div className="p-5 border-b" style={{ borderColor: theme.border }}>
                    <label className="text-xs uppercase tracking-wider block mb-2" style={{ color: theme.textMuted }}>Asignatura</label>
                    <select
                        value={subjectId}
                        onChange={e => setSubjectId(e.target.value)}
                        className="w-full px-4 py-2.5 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500/50 transition-all"
                        style={{
                            backgroundColor: darkMode ? '#252525' : '#f1f5f9',
                            borderColor: theme.border,
                            color: theme.text
                        }}
                    >
                        <option value="">Todas las asignaturas</option>
                        {subjects.map(s => (
                            <option key={s} value={s}>{s}</option>
                        ))}
                    </select>
                </div>

                {/* New Chat */}
                <div className="p-5">
                    <button
                        onClick={startNewConversation}
                        className="w-full py-3 px-4 bg-gradient-to-r from-emerald-500 to-cyan-500 text-white rounded-xl hover:from-emerald-600 hover:to-cyan-600 flex items-center justify-center gap-2 font-medium shadow-lg shadow-emerald-500/25 transition-all hover:shadow-emerald-500/40"
                    >
                        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                        </svg>
                        Nueva conversación
                    </button>
                </div>

                {/* Conversations */}
                <div className="flex-1 overflow-y-auto px-3">
                    <p className="text-xs uppercase tracking-wider px-2 py-3" style={{ color: theme.textMuted }}>Historial</p>
                    {conversations.map(conv => (
                        <div
                            key={conv.id}
                            onClick={() => loadConversation(conv.id)}
                            className={`group flex items-center gap-3 p-3 rounded-xl cursor-pointer mb-1 transition-all border ${currentConversation === conv.id
                                    ? 'bg-emerald-500/10 border-emerald-500/30'
                                    : 'border-transparent'
                                }`}
                            style={{
                                backgroundColor: currentConversation === conv.id ? undefined : 'transparent'
                            }}
                            onMouseEnter={(e) => {
                                if (currentConversation !== conv.id) {
                                    e.currentTarget.style.backgroundColor = darkMode ? '#222' : '#f1f5f9'
                                }
                            }}
                            onMouseLeave={(e) => {
                                if (currentConversation !== conv.id) {
                                    e.currentTarget.style.backgroundColor = 'transparent'
                                }
                            }}
                        >
                            <div className={`w-8 h-8 rounded-lg flex items-center justify-center text-sm ${currentConversation === conv.id ? 'bg-emerald-500/20 text-emerald-400' : ''
                                }`} style={{
                                    backgroundColor: currentConversation !== conv.id ? (darkMode ? '#2a2a2a' : '#e2e8f0') : undefined,
                                    color: currentConversation !== conv.id ? theme.textMuted : undefined
                                }}>
                                💬
                            </div>
                            <span className="flex-1 truncate text-sm" style={{
                                color: currentConversation === conv.id ? '#6ee7b7' : theme.textSecondary
                            }}>{conv.title}</span>
                            <button
                                onClick={(e) => deleteConversation(conv.id, e)}
                                className="opacity-0 group-hover:opacity-100 p-1.5 hover:bg-red-500/20 rounded-lg text-red-400 transition-all"
                            >
                                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                                </svg>
                            </button>
                        </div>
                    ))}
                    {conversations.length === 0 && (
                        <p className="text-sm text-center py-8" style={{ color: theme.textMuted }}>Sin conversaciones</p>
                    )}
                </div>

                {/* Logout */}
                <div className="p-4 border-t" style={{ borderColor: theme.border }}>
                    <button
                        onClick={onLogout}
                        className="w-full py-2.5 hover:text-red-400 hover:bg-red-500/10 rounded-xl text-sm transition-all flex items-center justify-center gap-2"
                        style={{ color: theme.textSecondary }}
                    >
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
                        </svg>
                        Cerrar sesión
                    </button>
                </div>
            </div>

            {/* Main Chat */}
            <div className="flex-1 flex flex-col min-w-0 transition-colors" style={{ backgroundColor: theme.bg }}>
                {/* Header */}
                <header className="flex items-center gap-4 px-4 py-3 border-b" style={{ borderColor: darkMode ? '#1a1a1a' : theme.border, backgroundColor: theme.bg }}>
                    <button
                        onClick={() => setSidebarOpen(!sidebarOpen)}
                        className="p-2.5 rounded-xl transition-colors"
                        style={{ color: theme.textSecondary }}
                        onMouseEnter={(e) => e.currentTarget.style.backgroundColor = darkMode ? '#1a1a1a' : '#f1f5f9'}
                        onMouseLeave={(e) => e.currentTarget.style.backgroundColor = 'transparent'}
                    >
                        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
                        </svg>
                    </button>
                    <h1 className="text-lg font-semibold" style={{ color: theme.text }}>Chat Educativo</h1>
                    {subjectId && (
                        <span className="px-3 py-1 bg-emerald-500/10 text-emerald-500 rounded-lg text-sm border border-emerald-500/20">
                            {subjectId}
                        </span>
                    )}
                </header>

                {/* Messages */}
                <div className="flex-1 overflow-y-auto px-4 py-6">
                    {messages.length === 0 && (
                        <div className="h-full flex items-center justify-center">
                            <div className="text-center">
                                <div className="w-20 h-20 mx-auto mb-6 rounded-2xl bg-gradient-to-br from-emerald-500/20 to-cyan-500/20 flex items-center justify-center">
                                    <span className="text-4xl">🤖</span>
                                </div>
                                <p className="text-xl font-medium mb-2" style={{ color: theme.text }}>¡Hola! Soy tu asistente educativo</p>
                                <p style={{ color: theme.textMuted }}>Haz una pregunta o sube un PDF para guardar material</p>
                            </div>
                        </div>
                    )}

                    <div className="space-y-6 max-w-5xl mx-auto">
                        {messages.map((msg) => (
                            <div key={msg.id} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                                {msg.role === 'assistant' && (
                                    <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-emerald-500 to-cyan-500 flex items-center justify-center mr-3 mt-1 flex-shrink-0">
                                        <span className="text-sm">🤖</span>
                                    </div>
                                )}
                                <div
                                    className={`rounded-2xl px-5 py-4 ${msg.role === 'user' ? 'bg-gradient-to-r from-emerald-500 to-cyan-500 text-white max-w-[70%]' : 'flex-1 max-w-[90%] border'
                                        }`}
                                    style={msg.role === 'assistant' ? {
                                        backgroundColor: theme.bgSecondary,
                                        borderColor: theme.border,
                                        color: theme.text
                                    } : {}}
                                >
                                    {msg.role === 'assistant' ? (
                                        <div style={{
                                            fontSize: '15px',
                                            lineHeight: '1.9',
                                            color: theme.text,
                                        }}>
                                            <ReactMarkdown
                                                rehypePlugins={[rehypeRaw]}
                                                components={{
                                                    p: ({ children }) => <p style={{ marginBottom: '1.2em', lineHeight: '1.9' }}>{children}</p>,
                                                    h1: ({ children }) => <h1 style={{ marginTop: '1.8em', marginBottom: '0.8em', fontSize: '1.6em', fontWeight: '600', color: darkMode ? '#10b981' : '#047857', lineHeight: '1.3' }}>{children}</h1>,
                                                    h2: ({ children }) => <h2 style={{ marginTop: '1.6em', marginBottom: '0.6em', fontSize: '1.35em', fontWeight: '600', color: darkMode ? '#34d399' : '#059669', lineHeight: '1.3' }}>{children}</h2>,
                                                    h3: ({ children }) => <h3 style={{ marginTop: '1.4em', marginBottom: '0.5em', fontSize: '1.15em', fontWeight: '600', color: darkMode ? '#6ee7b7' : '#10b981', lineHeight: '1.3' }}>{children}</h3>,
                                                    ul: ({ children }) => <ul style={{ marginTop: '0.8em', marginBottom: '1.2em', paddingLeft: '1.8em', listStyleType: 'disc' }}>{children}</ul>,
                                                    ol: ({ children }) => <ol style={{ marginTop: '0.8em', marginBottom: '1.2em', paddingLeft: '1.8em', listStyleType: 'decimal' }}>{children}</ol>,
                                                    li: ({ children }) => <li style={{ marginBottom: '0.7em', paddingLeft: '0.3em', lineHeight: '1.7' }}>{children}</li>,
                                                    strong: ({ children }) => <strong style={{ fontWeight: '600', color: darkMode ? '#ffffff' : '#0f172a' }}>{children}</strong>,
                                                    em: ({ children }) => <em style={{ fontStyle: 'italic', color: darkMode ? '#d1d5db' : '#475569' }}>{children}</em>,
                                                    code: ({ children }) => <code style={{ backgroundColor: darkMode ? '#1e293b' : '#f1f5f9', padding: '0.2em 0.5em', borderRadius: '4px', fontSize: '0.9em', fontFamily: 'monospace' }}>{children}</code>,
                                                    blockquote: ({ children }) => <blockquote style={{ borderLeft: `3px solid ${darkMode ? '#10b981' : '#059669'}`, paddingLeft: '1em', marginLeft: '0', marginTop: '1em', marginBottom: '1em', fontStyle: 'italic', color: darkMode ? '#9ca3af' : '#64748b' }}>{children}</blockquote>,
                                                }}
                                            >
                                                {msg.content}
                                            </ReactMarkdown>
                                        </div>
                                    ) : (
                                        <p className="whitespace-pre-wrap">{msg.content}</p>
                                    )}
                                    {msg.sources && msg.sources.length > 0 && (
                                        <div className="mt-3 pt-3 border-t text-xs flex items-center gap-2" style={{ borderColor: theme.border, color: theme.textMuted }}>
                                            <span>📎</span>
                                            {msg.sources.map(s => s.file.split(/[/\\]/).pop()).join(', ')}
                                        </div>
                                    )}
                                </div>
                            </div>
                        ))}

                        {loading && (
                            <div className="flex justify-start">
                                <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-emerald-500 to-cyan-500 flex items-center justify-center mr-3">
                                    <span className="text-sm">🤖</span>
                                </div>
                                <div className="rounded-2xl px-5 py-4 border" style={{ backgroundColor: theme.bgSecondary, borderColor: theme.border }}>
                                    <div className="flex items-center gap-1.5">
                                        <div className="w-2 h-2 bg-emerald-400 rounded-full animate-bounce" />
                                        <div className="w-2 h-2 bg-emerald-400 rounded-full animate-bounce" style={{ animationDelay: '0.15s' }} />
                                        <div className="w-2 h-2 bg-emerald-400 rounded-full animate-bounce" style={{ animationDelay: '0.3s' }} />
                                    </div>
                                </div>
                            </div>
                        )}
                        <div ref={messagesEndRef} />
                    </div>
                </div>

                {/* Input */}
                <div className="p-4 border-t" style={{ borderColor: darkMode ? '#1a1a1a' : theme.border, backgroundColor: theme.bg }}>
                    <form onSubmit={handleSubmit} className="max-w-5xl mx-auto">
                        <div className="flex gap-3">
                            {/* File Upload Button */}
                            <input
                                type="file"
                                ref={fileInputRef}
                                onChange={handleFileSelect}
                                accept=".pdf"
                                className="hidden"
                            />
                            <button
                                type="button"
                                onClick={() => fileInputRef.current?.click()}
                                className="px-4 py-3.5 rounded-xl border transition-all hover:border-emerald-500/50"
                                style={{ backgroundColor: theme.input, borderColor: theme.border, color: theme.textSecondary }}
                                title="Adjuntar PDF"
                            >
                                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.172 7l-6.586 6.586a2 2 0 102.828 2.828l6.414-6.586a4 4 0 00-5.656-5.656l-6.415 6.585a6 6 0 108.486 8.486L20.5 13" />
                                </svg>
                            </button>
                            <input
                                type="text"
                                value={input}
                                onChange={e => setInput(e.target.value)}
                                placeholder="Escribe tu pregunta..."
                                className="flex-1 px-5 py-3.5 rounded-xl focus:outline-none focus:ring-2 focus:ring-emerald-500/50 transition-all border"
                                style={{
                                    backgroundColor: theme.input,
                                    borderColor: theme.border,
                                    color: theme.text,
                                }}
                                disabled={loading}
                            />
                            <button
                                type="submit"
                                disabled={loading || !input.trim()}
                                className="px-5 py-3.5 bg-gradient-to-r from-emerald-500 to-cyan-500 text-white rounded-xl hover:from-emerald-600 hover:to-cyan-600 disabled:opacity-40 disabled:cursor-not-allowed transition-all shadow-lg shadow-emerald-500/25 hover:shadow-emerald-500/40"
                            >
                                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
                                </svg>
                            </button>
                        </div>
                    </form>
                </div>
            </div>
        </div>
    )
}
