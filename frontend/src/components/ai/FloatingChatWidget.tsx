import React, { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Bot,
  Send,
  Sparkles,
  Trash2,
  ChevronDown,
  User,
  AlertCircle,
  History,
  Plus,
  MessageSquare,
  ChevronLeft,
  Calendar,
  Check
} from 'lucide-react';
import { MiningProject, BlockModelItem, UserRole } from '../../types';
import { useChatSession } from './useChatSession';
import { ChatContext } from '../../services/api';

interface FloatingChatWidgetProps {
  project: MiningProject | null;
  blocks: BlockModelItem[];
  selectedBlock: BlockModelItem | null;
  userName: string;
  userRole: UserRole;
}

export const FloatingChatWidget: React.FC<FloatingChatWidgetProps> = ({
  project,
  blocks,
  selectedBlock,
  userName,
  userRole,
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const [view, setView] = useState<'chat' | 'history'>('chat');
  const [input, setInput] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const {
    sessions,
    currentSessionId,
    messages,
    isLoading,
    sendMessage,
    createNewSession,
    selectSession,
    deleteSession,
    clearAllSessions,
  } = useChatSession();

  // Calcular contexto geológico dinámico
  const context: ChatContext | undefined = React.useMemo(() => {
    if (!project) return undefined;
    const activeBench = project.activeBench;
    const benchBlocks = blocks.filter(b => b.bench === activeBench);
    const avgGrade = benchBlocks.length > 0
      ? benchBlocks.reduce((s, b) => s + b.cu_bayesian, 0) / benchBlocks.length
      : undefined;
    const totalTonnage = benchBlocks.reduce((s, b) => s + b.tonnage, 0);

    return {
      active_bench: activeBench,
      selected_block_id: selectedBlock?.id,
      selected_block_cu: selectedBlock?.cu_bayesian,
      selected_block_lithology: selectedBlock?.lithology,
      project_name: project.name,
      cut_off_grade: project.cutOffGrade,
      avg_bench_grade: avgGrade,
      total_bench_tonnage: totalTonnage,
      user_role: userRole,
      user_name: userName,
    };
  }, [project, blocks, selectedBlock, userName, userRole]);

  // Scroll automático al último mensaje
  useEffect(() => {
    if (isOpen && view === 'chat' && messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages, isOpen, view]);

  // Focus en input al abrir
  useEffect(() => {
    if (isOpen && view === 'chat' && inputRef.current) {
      setTimeout(() => inputRef.current?.focus(), 100);
    }
  }, [isOpen, view]);

  const handleSend = (textToSend?: string) => {
    const text = textToSend || input;
    if (!text.trim() || isLoading) return;
    sendMessage(text, context);
    setInput('');
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleNewChat = () => {
    createNewSession();
    setView('chat');
  };

  const handleSelectSession = (id: string) => {
    selectSession(id);
    setView('chat');
  };

  const formatTimestamp = (ts: number) => {
    const d = new Date(ts);
    const now = new Date();
    const isToday = d.toDateString() === now.toDateString();
    if (isToday) {
      return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    }
    return d.toLocaleDateString([], { day: '2-digit', month: 'short' });
  };

  const quickPrompts = [
    "¿Cuáles son las litologías del banco 3170?",
    "¿Qué alteración predomina en zonas de alta ley?",
    "Explica la diferencia entre incertidumbre epistémica y aleatoria.",
  ];

  return (
    <>
      {/* ─── Botón Flotante ─── */}
      <AnimatePresence>
        {!isOpen && (
          <motion.button
            initial={{ scale: 0, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            exit={{ scale: 0, opacity: 0 }}
            transition={{ type: 'spring', stiffness: 260, damping: 20 }}
            onClick={() => setIsOpen(true)}
            className="fixed bottom-6 right-6 z-50 w-14 h-14 rounded-full bg-gradient-to-r from-amber-600 to-amber-500 hover:from-amber-500 hover:to-amber-400 text-white shadow-xl shadow-amber-500/30 hover:shadow-amber-500/50 flex items-center justify-center transition-all group"
            aria-label="Abrir Copiloto IA"
            title="Copiloto IA Geológico (LangFlow)"
          >
            <Sparkles className="w-6 h-6 transition-transform group-hover:scale-110" />
            <span className="absolute -top-1 -right-1 flex h-4 w-4">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-4 w-4 bg-emerald-500 border-2 border-white dark:border-slate-900"></span>
            </span>
          </motion.button>
        )}
      </AnimatePresence>

      {/* ─── Panel de Chat Overlay ─── */}
      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ opacity: 0, y: 20, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 20, scale: 0.95 }}
            transition={{ type: 'spring', stiffness: 300, damping: 25 }}
            className="fixed bottom-6 right-6 z-50 w-[94vw] max-w-[420px] h-[580px] max-h-[85vh] rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-2xl flex flex-col overflow-hidden font-sans"
          >
            {/* Header */}
            <div className="shrink-0 flex items-center justify-between px-4 py-3 bg-gradient-to-r from-amber-600 to-amber-700 text-white shadow-md">
              <div className="flex items-center gap-2.5 min-w-0">
                {view === 'history' ? (
                  <button
                    onClick={() => setView('chat')}
                    className="p-1 rounded-lg hover:bg-white/20 transition-colors"
                    title="Volver a la conversación"
                  >
                    <ChevronLeft className="w-5 h-5" />
                  </button>
                ) : (
                  <div className="w-8 h-8 rounded-lg bg-white/20 flex items-center justify-center shrink-0 border border-white/20 shadow-inner">
                    <Bot className="w-4.5 h-4.5" />
                  </div>
                )}
                <div className="min-w-0">
                  <div className="text-sm font-bold truncate flex items-center gap-1.5">
                    {view === 'history' ? 'Historial de Conversaciones' : 'Copiloto IA M-6'}
                    <span className="text-[9px] bg-emerald-500/30 border border-emerald-400/40 text-emerald-100 px-1.5 py-0.5 rounded-full font-mono font-medium">
                      LangFlow
                    </span>
                  </div>
                  <div className="text-[10px] text-amber-100 font-mono truncate">
                    {view === 'history' ? `${sessions.length} chats guardados` : 'Memoria persistente activa'}
                  </div>
                </div>
              </div>

              <div className="flex items-center gap-1">
                {/* Botón Nuevo Chat */}
                <button
                  onClick={handleNewChat}
                  className="p-1.5 rounded-lg hover:bg-white/20 transition-colors text-white"
                  title="Nueva Conversación"
                >
                  <Plus className="w-4 h-4" />
                </button>

                {/* Botón Historial (Message History) */}
                <button
                  onClick={() => setView(v => (v === 'chat' ? 'history' : 'chat'))}
                  className={`p-1.5 rounded-lg transition-colors text-white ${
                    view === 'history' ? 'bg-white/30 font-bold' : 'hover:bg-white/20'
                  }`}
                  title={view === 'history' ? 'Ver Chat' : 'Historial de Conversaciones'}
                >
                  <History className="w-4 h-4" />
                </button>

                {/* Botón Minimizar */}
                <button
                  onClick={() => setIsOpen(false)}
                  className="p-1.5 rounded-lg hover:bg-white/20 transition-colors text-white ml-0.5"
                  title="Cerrar chat"
                >
                  <ChevronDown className="w-4.5 h-4.5" />
                </button>
              </div>
            </div>

            {/* ─── VISTA 1: HISTORIAL DE CONVERSACIONES (Message History Panel) ─── */}
            {view === 'history' ? (
              <div className="flex-1 flex flex-col overflow-hidden bg-slate-50 dark:bg-slate-950">
                <div className="p-3 border-b border-slate-200 dark:border-slate-800 flex items-center justify-between bg-white dark:bg-slate-900/50">
                  <span className="text-xs font-semibold text-slate-600 dark:text-slate-300">
                    Conversaciones Previas
                  </span>
                  <button
                    onClick={handleNewChat}
                    className="text-xs font-semibold text-amber-600 dark:text-amber-400 hover:text-amber-500 flex items-center gap-1"
                  >
                    <Plus className="w-3.5 h-3.5" /> Nuevo Chat
                  </button>
                </div>

                <div className="flex-1 overflow-y-auto p-3 space-y-2">
                  {sessions.map(s => {
                    const isActive = s.id === currentSessionId;
                    const userMsgCount = s.messages.filter(m => m.role === 'user').length;

                    return (
                      <div
                        key={s.id}
                        onClick={() => handleSelectSession(s.id)}
                        className={`group relative p-3 rounded-xl border transition-all cursor-pointer flex items-start justify-between gap-2 ${
                          isActive
                            ? 'bg-amber-50 dark:bg-amber-950/30 border-amber-300 dark:border-amber-700/60 shadow-sm'
                            : 'bg-white dark:bg-slate-900 border-slate-200 dark:border-slate-800 hover:border-amber-300 dark:hover:border-amber-700 hover:shadow'
                        }`}
                      >
                        <div className="flex items-start gap-2.5 min-w-0 flex-1">
                          <div
                            className={`p-2 rounded-lg shrink-0 mt-0.5 ${
                              isActive
                                ? 'bg-amber-500 text-white'
                                : 'bg-slate-100 dark:bg-slate-800 text-slate-500 group-hover:text-amber-500'
                            }`}
                          >
                            <MessageSquare className="w-3.5 h-3.5" />
                          </div>
                          <div className="min-w-0 flex-1">
                            <div className="text-xs font-bold text-slate-800 dark:text-slate-200 truncate group-hover:text-amber-600 dark:group-hover:text-amber-400">
                              {s.title}
                            </div>
                            <div className="flex items-center gap-2 mt-1 text-[10px] text-slate-400 font-mono">
                              <span className="flex items-center gap-0.5">
                                <Calendar className="w-2.5 h-2.5" />
                                {formatTimestamp(s.updatedAt)}
                              </span>
                              <span>•</span>
                              <span>{userMsgCount} {userMsgCount === 1 ? 'pregunta' : 'preguntas'}</span>
                              {isActive && (
                                <>
                                  <span>•</span>
                                  <span className="text-emerald-500 font-bold flex items-center gap-0.5">
                                    <Check className="w-2.5 h-2.5" /> Activo
                                  </span>
                                </>
                              )}
                            </div>
                          </div>
                        </div>

                        {/* Botón eliminar sesión individual */}
                        {sessions.length > 1 && (
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              deleteSession(s.id);
                            }}
                            className="opacity-0 group-hover:opacity-100 p-1.5 text-slate-400 hover:text-rose-500 hover:bg-rose-50 dark:hover:bg-rose-950/40 rounded-lg transition-all"
                            title="Eliminar conversación"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        )}
                      </div>
                    );
                  })}
                </div>

                {/* Footer del historial */}
                <div className="p-3 border-t border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 flex justify-between items-center">
                  <span className="text-[10px] text-slate-400 font-mono">
                    Persistido en navegador
                  </span>
                  <button
                    onClick={clearAllSessions}
                    className="text-xs text-rose-500 hover:text-rose-600 font-medium flex items-center gap-1 hover:underline"
                  >
                    <Trash2 className="w-3 h-3" /> Vaciar todo el historial
                  </button>
                </div>
              </div>
            ) : (
              /* ─── VISTA 2: CHAT ACTIVO ─── */
              <>
                {/* Messages Area */}
                <div className="flex-1 overflow-y-auto p-3 space-y-3 bg-slate-50 dark:bg-slate-950/50">
                  {messages.map((msg, idx) => (
                    <div
                      key={idx}
                      className={`flex gap-2 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
                    >
                      {msg.role === 'assistant' && (
                        <div className="w-7 h-7 rounded-lg bg-amber-500/20 text-amber-600 dark:text-amber-400 flex items-center justify-center shrink-0 mt-0.5 border border-amber-500/30 shadow-sm">
                          <Bot className="w-3.5 h-3.5" />
                        </div>
                      )}

                      <div
                        className={`max-w-[85%] rounded-2xl px-3.5 py-2.5 text-xs leading-relaxed shadow-sm ${
                          msg.role === 'user'
                            ? 'bg-gradient-to-r from-amber-500 to-amber-600 text-white font-medium rounded-tr-none'
                            : msg.content.startsWith('⚠️')
                              ? 'bg-rose-50 dark:bg-rose-950/30 border border-rose-200 dark:border-rose-800 text-rose-800 dark:text-rose-300 rounded-tl-none'
                              : 'bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 text-slate-800 dark:text-slate-200 rounded-tl-none'
                        }`}
                      >
                        <div className="whitespace-pre-line">{msg.content}</div>
                      </div>

                      {msg.role === 'user' && (
                        <div className="w-7 h-7 rounded-lg bg-amber-500/20 text-amber-600 dark:text-amber-400 flex items-center justify-center shrink-0 mt-0.5 border border-amber-500/30 shadow-sm">
                          <User className="w-3.5 h-3.5" />
                        </div>
                      )}
                    </div>
                  ))}

                  {/* Sugerencias Rápidas si es una conversación nueva */}
                  {messages.length === 1 && (
                    <div className="mt-4 space-y-1.5">
                      <div className="text-[10px] font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wider px-1">
                        Consultas sugeridas:
                      </div>
                      {quickPrompts.map((prompt, qIdx) => (
                        <button
                          key={qIdx}
                          onClick={() => handleSend(prompt)}
                          className="w-full text-left p-2 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 hover:border-amber-400 dark:hover:border-amber-600 text-slate-700 dark:text-slate-300 text-xs transition-all hover:shadow-sm"
                        >
                          💬 {prompt}
                        </button>
                      ))}
                    </div>
                  )}

                  {isLoading && (
                    <div className="flex gap-2 items-center text-xs text-amber-600 dark:text-amber-400 font-mono py-1">
                      <div className="w-7 h-7 rounded-lg bg-amber-500/20 text-amber-400 flex items-center justify-center border border-amber-500/30 animate-spin">
                        <Sparkles className="w-3.5 h-3.5" />
                      </div>
                      <span className="animate-pulse">Consultando LangFlow M-6...</span>
                    </div>
                  )}

                  <div ref={messagesEndRef} />
                </div>

                {/* Context Pill (cuando hay bloque seleccionado) */}
                {selectedBlock && (
                  <div className="shrink-0 px-3 py-1.5 bg-amber-50 dark:bg-amber-950/20 border-t border-amber-100 dark:border-amber-900/30">
                    <div className="flex items-center gap-1.5 text-[10px] text-amber-700 dark:text-amber-400 font-mono truncate">
                      <AlertCircle className="w-3 h-3 shrink-0" />
                      <span className="truncate">
                        Contexto Bloque: {selectedBlock.id} — {selectedBlock.cu_bayesian.toFixed(2)}% Cu | {selectedBlock.lithology}
                      </span>
                    </div>
                  </div>
                )}

                {/* Input Area */}
                <div className="shrink-0 p-3 border-t border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900">
                  <form
                    onSubmit={(e) => {
                      e.preventDefault();
                      handleSend();
                    }}
                    className="flex gap-2"
                  >
                    <input
                      ref={inputRef}
                      type="text"
                      value={input}
                      onChange={(e) => setInput(e.target.value)}
                      onKeyDown={handleKeyDown}
                      placeholder="Pregunta sobre leyes, litología, JORC..."
                      className="flex-1 px-3.5 py-2.5 bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-700 rounded-xl text-xs text-slate-900 dark:text-slate-100 placeholder-slate-400 focus:outline-none focus:border-amber-500 focus:ring-1 focus:ring-amber-500 transition-all"
                      disabled={isLoading}
                    />
                    <button
                      type="submit"
                      disabled={isLoading || !input.trim()}
                      className="px-3.5 py-2.5 bg-gradient-to-r from-amber-600 to-amber-500 hover:from-amber-500 hover:to-amber-400 disabled:opacity-40 disabled:cursor-not-allowed text-white rounded-xl text-xs font-bold transition-all flex items-center gap-1 shadow-md shadow-amber-500/20"
                      title="Enviar mensaje"
                    >
                      <Send className="w-3.5 h-3.5" />
                    </button>
                  </form>
                </div>
              </>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
};
