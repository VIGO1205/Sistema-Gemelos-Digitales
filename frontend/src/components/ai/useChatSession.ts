import { useState, useCallback, useRef, useEffect } from 'react';
import { chatApi, ChatMessage, ChatContext } from '../../services/api';

export interface ChatSessionItem {
  id: string;
  title: string;
  createdAt: number;
  updatedAt: number;
  messages: ChatMessage[];
}

export interface UseChatSessionReturn {
  sessions: ChatSessionItem[];
  currentSessionId: string;
  messages: ChatMessage[];
  isLoading: boolean;
  error: string | null;
  sendMessage: (content: string, context?: ChatContext) => Promise<void>;
  createNewSession: () => void;
  selectSession: (sessionId: string) => void;
  deleteSession: (sessionId: string) => void;
  clearChat: () => void;
  clearAllSessions: () => void;
}

const STORAGE_KEY_SESSIONS = 'm6_chat_sessions_v2';
const STORAGE_KEY_ACTIVE = 'm6_active_session_id_v2';

const WELCOME_MESSAGE: ChatMessage = {
  role: 'assistant',
  content: 'Hola, soy el Copiloto IA Geológico del Gemelo Digital M-6. Estoy conectado a LangFlow y modelos de vanguardia para minería. Pregúntame sobre control de leyes, incertidumbre geoestadística, reconciliación de planta o recomendaciones de sondajes.',
};

function createInitialSession(): ChatSessionItem {
  const newId = `session_${Date.now()}_${Math.random().toString(36).substring(2, 7)}`;
  return {
    id: newId,
    title: 'Nueva Conversación',
    createdAt: Date.now(),
    updatedAt: Date.now(),
    messages: [WELCOME_MESSAGE],
  };
}

function loadStoredSessions(): { sessions: ChatSessionItem[]; activeId: string } {
  try {
    const rawSessions = localStorage.getItem(STORAGE_KEY_SESSIONS);
    const rawActive = localStorage.getItem(STORAGE_KEY_ACTIVE);
    
    if (rawSessions) {
      const parsed: ChatSessionItem[] = JSON.parse(rawSessions);
      if (Array.isArray(parsed) && parsed.length > 0) {
        const activeId = rawActive && parsed.some(s => s.id === rawActive) ? rawActive : parsed[0].id;
        return { sessions: parsed, activeId };
      }
    }
  } catch (e) {
    console.error('Error cargando historial de chat de localStorage:', e);
  }

  const defaultSession = createInitialSession();
  return { sessions: [defaultSession], activeId: defaultSession.id };
}

export function useChatSession(): UseChatSessionReturn {
  const [sessionData, setSessionData] = useState<{ sessions: ChatSessionItem[]; activeId: string }>(() => loadStoredSessions());
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  const { sessions, activeId: currentSessionId } = sessionData;

  const currentSession = sessions.find(s => s.id === currentSessionId) || sessions[0] || createInitialSession();
  const messages = currentSession.messages;

  // Persistir en localStorage
  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY_SESSIONS, JSON.stringify(sessions));
      localStorage.setItem(STORAGE_KEY_ACTIVE, currentSessionId);
    } catch (e) {
      console.error('Error guardando historial de chat en localStorage:', e);
    }
  }, [sessions, currentSessionId]);

  const createNewSession = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    const newSession = createInitialSession();
    setSessionData(prev => ({
      sessions: [newSession, ...prev.sessions],
      activeId: newSession.id,
    }));
    setError(null);
    setIsLoading(false);
  }, []);

  const selectSession = useCallback((sessionId: string) => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    setSessionData(prev => ({
      ...prev,
      activeId: sessionId,
    }));
    setError(null);
    setIsLoading(false);
  }, []);

  const deleteSession = useCallback((sessionId: string) => {
    setSessionData(prev => {
      const filtered = prev.sessions.filter(s => s.id !== sessionId);
      if (filtered.length === 0) {
        const fresh = createInitialSession();
        return { sessions: [fresh], activeId: fresh.id };
      }
      const nextActiveId = prev.activeId === sessionId ? filtered[0].id : prev.activeId;
      return { sessions: filtered, activeId: nextActiveId };
    });
  }, []);

  const clearAllSessions = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    const fresh = createInitialSession();
    setSessionData({
      sessions: [fresh],
      activeId: fresh.id,
    });
    setError(null);
    setIsLoading(false);
  }, []);

  const clearChat = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    setSessionData(prev => ({
      ...prev,
      sessions: prev.sessions.map(s => {
        if (s.id === prev.activeId) {
          return {
            ...s,
            title: 'Nueva Conversación',
            updatedAt: Date.now(),
            messages: [WELCOME_MESSAGE],
          };
        }
        return s;
      }),
    }));
    setError(null);
    setIsLoading(false);
  }, []);

  const sendMessage = useCallback(async (content: string, context?: ChatContext) => {
    const trimmed = content.trim();
    if (!trimmed) return;

    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }

    const userMsg: ChatMessage = { role: 'user', content: trimmed };
    const updatedMessages = [...messages, userMsg];

    // Actualizar sesión con el mensaje de usuario
    setSessionData(prev => ({
      ...prev,
      sessions: prev.sessions.map(s => {
        if (s.id === prev.activeId) {
          // Generar título automático si es el primer mensaje del usuario
          const isFirstUserMsg = s.messages.filter(m => m.role === 'user').length === 0;
          const newTitle = isFirstUserMsg
            ? trimmed.length > 32 ? trimmed.substring(0, 32) + '...' : trimmed
            : s.title;

          return {
            ...s,
            title: newTitle,
            updatedAt: Date.now(),
            messages: updatedMessages,
          };
        }
        return s;
      }),
    }));

    setIsLoading(true);
    setError(null);

    try {
      const response = await chatApi.sendMessage(updatedMessages, context, currentSessionId);
      const assistantMsg: ChatMessage = response.data.message;

      setSessionData(prev => ({
        ...prev,
        sessions: prev.sessions.map(s => {
          if (s.id === prev.activeId) {
            return {
              ...s,
              updatedAt: Date.now(),
              messages: [...s.messages, assistantMsg],
            };
          }
          return s;
        }),
      }));
    } catch (err: any) {
      const msg = err.response?.data?.detail || err.message || 'Error al comunicarse con el asistente IA';
      setError(msg);

      setSessionData(prev => ({
        ...prev,
        sessions: prev.sessions.map(s => {
          if (s.id === prev.activeId) {
            return {
              ...s,
              updatedAt: Date.now(),
              messages: [
                ...s.messages,
                {
                  role: 'assistant',
                  content: `⚠️ **Error:** ${msg}\n\nPor favor, verifica la conexión con LangFlow o el servicio de IA.`,
                },
              ],
            };
          }
          return s;
        }),
      }));
    } finally {
      setIsLoading(false);
      abortControllerRef.current = null;
    }
  }, [messages, currentSessionId]);

  return {
    sessions,
    currentSessionId,
    messages,
    isLoading,
    error,
    sendMessage,
    createNewSession,
    selectSession,
    deleteSession,
    clearChat,
    clearAllSessions,
  };
}
