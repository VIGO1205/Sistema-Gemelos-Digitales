import React, { useState } from 'react';
import { BlockModelItem, MiningProject, UserRole } from '../../types';
import { 
  Bot, 
  Send, 
  Sparkles, 
  Compass, 
  Activity, 
  ShieldAlert, 
  FileText, 
  Lightbulb,
  CheckCircle2,
  Layers
} from 'lucide-react';

interface GeologicalCopilotProps {
  project: MiningProject;
  blocks: BlockModelItem[];
  currentRole: UserRole;
  selectedBlock?: BlockModelItem | null;
}

interface Message {
  sender: 'user' | 'ai';
  text: string;
  timestamp: string;
}

export const GeologicalCopilot: React.FC<GeologicalCopilotProps> = ({
  project,
  blocks,
  currentRole,
  selectedBlock
}) => {
  const [messages, setMessages] = useState<Message[]>([
    {
      sender: 'ai',
      text: `Hola, soy el Asistente Inteligente del Gemelo Digital M-6. He analizado el banco activo Z = ${project.activeBench}m en ${project.name}. ¿En qué puedo apoyarte hoy con respecto al control de leyes, incertidumbre epistémica o reconciliación de planta?`,
      timestamp: '08:30 UTC'
    }
  ]);
  const [inputQuery, setInputQuery] = useState('');
  const [isTyping, setIsTyping] = useState(false);

  const suggestedPrompts = [
    `¿Qué bloques en el Banco ${project.activeBench}m presentan alto riesgo de dilución por contacto litológico?`,
    `Analiza la ganancia de cobre fino estimada por el modelo de fusión MFM respecto al Kriging base.`,
    `¿Qué recomendaciones de sondajes infill se requieren para clasificar recursos de 'Inferido' a 'Indicado'?`,
    `Explica la firma hiperespectral del bloque seleccionado ${selectedBlock ? selectedBlock.id : 'BLK-3170-04-05'}.`
  ];

  const handleSend = (textToSend?: string) => {
    const q = textToSend || inputQuery;
    if (!q.trim()) return;

    const userMsg: Message = {
      sender: 'user',
      text: q,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    };

    setMessages(prev => [...prev, userMsg]);
    setInputQuery('');
    setIsTyping(true);

    setTimeout(() => {
      let reply = '';
      const lower = q.toLowerCase();

      if (lower.includes('dilución') || lower.includes('riesgo')) {
        reply = `**Análisis de Riesgo de Dilución (Banco ${project.activeBench}m):**\n\nSe han detectado 3 zonas críticas en los límites Este del rajo donde el contacto entre *Pórfido Cuprífero* y *Andesita* presenta un gradiente de ley abrupto (>0.45% Cu / 10m). El modelo Bayesiano cuantifica una incertidumbre epistémica $\\sigma > 0.18\\%$. Se sugiere reajustar la malla de voladura a $5\\text{m} \\times 5\\text{m}$ para mitigar la mezcla de estéril con mineral de alta ley.`;
      } else if (lower.includes('ganancia') || lower.includes('cobre fino') || lower.includes('kriging')) {
        reply = `**Conciliación y Ganancia de Metal:**\n\nEl Gemelo Digital M-6 estima un total de **${(blocks.reduce((acc, b) => acc + (b.tonnage * b.cu_bayesian)/100, 0)).toFixed(0)} toneladas de Cu fino**, lo que representa un incremento neto de **+248 t Cu** sobre la estimación de Kriging Ordinario. Esta ganancia proviene principalmente de la delimitación precisa de zonas de alteración fílica/potásica capturadas por espectrometría SWIR (2206 nm).`;
      } else if (lower.includes('sondaje') || lower.includes('infill') || lower.includes('inferido')) {
        reply = `**Plan de Perforación Infill Recomendado:**\n\nPara elevar los recursos de la categoría *Inferido* (13% del banco actual) a *Indicado*, se recomienda ejecutar **4 sondajes de circulación reversa (RC)** orientados N45°W / Dip -60° con una profundidad promedio de 85m en las coordenadas UTM E: 341,200 / N: 7,458,900.`;
      } else if (lower.includes('hiperespectral') || lower.includes('firma') || lower.includes('espectral')) {
        reply = `**Firma Espectral & Mineralogía:**\n\nEn el banco ${project.activeBench}m, el sensor SWIR ha identificado absorciones características de *Al-OH a 2206 nm* asociadas a Illita de alta cristalinidad y enlaces *Fe-OH a 2250 nm* correspondientes a biotita hidrotermal. Estas firmas correlacionan con un factor de recuperación metalúrgica estimado en 89.2% en celdas de flotación rugosa.`;
      } else {
        reply = `**Evaluación M-6 Digital Twin:**\n\nHe procesado tu consulta geológica para el Banco ${project.activeBench}m. Las predicciones bayesianas combinadas con datos de sondajes y espectrometría de drones muestran una varianza controlada con un coeficiente de variación del 14.8%, manteniéndose dentro de los límites de control estadístico SPC.`;
      }

      const aiMsg: Message = {
        sender: 'ai',
        text: reply,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      };

      setMessages(prev => [...prev, aiMsg]);
      setIsTyping(false);
    }, 700);
  };

  return (
    <div className="space-y-4 sm:space-y-6">
      
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-3 bg-white dark:bg-slate-900 p-4 sm:p-5 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-sm">
        <div>
          <h2 className="text-sm sm:text-base font-bold text-slate-900 dark:text-slate-100 font-display flex items-center gap-2">
            <Sparkles className="w-5 h-5 text-purple-600 dark:text-purple-400" />
            Copiloto IA Geológico (Gemini Powered)
          </h2>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
            Asistencia generativa para interpretación geoestadística, auditoría JORC y recomendaciones operacionales
          </p>
        </div>

        <div className="flex items-center gap-2">
          <span className="flex h-2.5 w-2.5 rounded-full bg-purple-500 animate-pulse" />
          <span className="text-xs font-mono text-purple-600 dark:text-purple-400 font-semibold">Gemini 2.5 Flash Geological Engine</span>
        </div>
      </div>

      {/* Main Chat Interface */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-4 sm:gap-6">
        
        {/* Left: Quick Prompts & Context Pill */}
        <div className="space-y-4">
          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-4 space-y-3 shadow-sm">
            <h3 className="text-xs font-bold text-slate-800 dark:text-slate-200 uppercase font-display tracking-wider flex items-center gap-1.5">
              <Lightbulb className="w-3.5 h-3.5 text-amber-500" />
              Consultas Frecuentes
            </h3>

            <div className="space-y-2">
              {suggestedPrompts.map((prompt, idx) => (
                <button
                  key={idx}
                  onClick={() => handleSend(prompt)}
                  className="w-full p-2.5 bg-slate-50 dark:bg-slate-950/80 hover:bg-slate-100 dark:hover:bg-slate-800 border border-slate-200 dark:border-slate-800 rounded-xl text-left text-xs text-slate-700 dark:text-slate-300 transition-colors leading-relaxed"
                >
                  {prompt}
                </button>
              ))}
            </div>
          </div>

          <div className="bg-purple-50 dark:bg-slate-900 border border-purple-200 dark:border-purple-500/30 rounded-2xl p-4 space-y-2">
            <span className="text-[10px] font-mono text-purple-700 dark:text-purple-400 uppercase font-bold">Contexto Geológico Activo</span>
            <div className="text-xs text-slate-700 dark:text-slate-300 space-y-1 font-mono">
              <div>Faena: <strong className="text-slate-900 dark:text-slate-100">{project.name}</strong></div>
              <div>Banco: <strong className="text-amber-600 dark:text-amber-400">Z = {project.activeBench}m</strong></div>
              <div>Bloques: <strong>{blocks.length} evaluados</strong></div>
            </div>
          </div>
        </div>

        {/* Center/Right: Message Feed */}
        <div className="lg:col-span-3 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl flex flex-col h-[560px] shadow-sm overflow-hidden">
          
          {/* Messages list */}
          <div className="flex-1 overflow-y-auto p-4 sm:p-5 space-y-4">
            {messages.map((m, idx) => (
              <div
                key={idx}
                className={`flex gap-3 ${m.sender === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                {m.sender === 'ai' && (
                  <div className="w-8 h-8 rounded-xl bg-purple-500/20 text-purple-600 dark:text-purple-400 flex items-center justify-center shrink-0 mt-1 border border-purple-500/30">
                    <Bot className="w-4 h-4" />
                  </div>
                )}

                <div
                  className={`max-w-[85%] sm:max-w-[75%] rounded-2xl p-4 text-xs leading-relaxed ${
                    m.sender === 'user'
                      ? 'bg-amber-500 text-slate-950 font-medium'
                      : 'bg-slate-50 dark:bg-slate-950/80 border border-slate-200 dark:border-slate-800 text-slate-800 dark:text-slate-200'
                  }`}
                >
                  <div className="flex items-center justify-between mb-1 text-[10px] opacity-70 font-mono">
                    <span>{m.sender === 'user' ? 'Tú' : 'Copiloto IA M-6'}</span>
                    <span>{m.timestamp}</span>
                  </div>
                  <div className="whitespace-pre-line">{m.text}</div>
                </div>
              </div>
            ))}

            {isTyping && (
              <div className="flex gap-3 items-center text-xs text-purple-600 dark:text-purple-400 font-mono">
                <div className="w-8 h-8 rounded-xl bg-purple-500/20 text-purple-400 flex items-center justify-center border border-purple-500/30 animate-spin">
                  <Sparkles className="w-4 h-4" />
                </div>
                <span>Sintetizando respuesta geoestadística...</span>
              </div>
            )}
          </div>

          {/* Input Box */}
          <div className="p-3 sm:p-4 border-t border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950/50">
            <form
              onSubmit={e => {
                e.preventDefault();
                handleSend();
              }}
              className="flex gap-2"
            >
              <input
                type="text"
                value={inputQuery}
                onChange={e => setInputQuery(e.target.value)}
                placeholder="Escribe tu consulta geológica sobre leyes, incertidumbre o JORC..."
                className="flex-1 px-4 py-2.5 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-xl text-xs text-slate-900 dark:text-slate-100 placeholder-slate-400 focus:outline-none focus:border-amber-500"
              />
              <button
                type="submit"
                className="px-4 py-2.5 bg-amber-500 hover:bg-amber-600 text-slate-950 rounded-xl text-xs font-bold font-mono transition-colors flex items-center gap-1.5 shadow"
              >
                <Send className="w-4 h-4" />
                <span className="hidden sm:inline">Enviar</span>
              </button>
            </form>
          </div>

        </div>

      </div>

    </div>
  );
};
