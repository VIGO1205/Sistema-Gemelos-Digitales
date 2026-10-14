import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { Eye, EyeOff, Lock, Mail, AlertCircle, Cpu, ShieldCheck, Activity, Layers } from 'lucide-react';
import { useAuth } from '../../context/AuthContext';

const DEMO_USERS = [
  { email: 'admin@m6gemelo.cl', password: 'AdminM6*2026', role: 'ADMIN', name: 'Administrador' },
  { email: 'qp.senior@m6gemelo.cl', password: 'QPSenior*2026', role: 'QP Senior', name: 'Dra. Elena Vásquez' },
  { email: 'geo.junior@m6gemelo.cl', password: 'GeoJunior*2026', role: 'Geólogo Junior', name: 'Sofía Alarcón' },
  { email: 'planificacion@m6gemelo.cl', password: 'Planifica*2026', role: 'Planificación', name: 'Ing. Carlos Mendoza' },
  { email: 'supervisor@m6gemelo.cl', password: 'Supervisor*2026', role: 'Supervisor', name: 'Marco Arismendi' },
  { email: 'auditor@m6gemelo.cl', password: 'Auditor*2026', role: 'Auditor / Viewer', name: 'Dr. Alejandro Morales' },
];

export const LoginPage: React.FC = () => {
  const { login } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setIsSubmitting(true);
    try {
      await login(email, password);
    } catch (err: any) {
      setError(err.message || 'Error de autenticación');
    } finally {
      setIsSubmitting(false);
    }
  };

  const fillDemo = (u: typeof DEMO_USERS[0]) => {
    setEmail(u.email);
    setPassword(u.password);
    setError('');
  };

  return (
    <div className="min-h-screen flex flex-col lg:flex-row overflow-hidden relative font-sans selection:bg-amber-500 selection:text-slate-950">
      {/* LEFT COLUMN: System Showcase & Information (Dark Theme) */}
      <motion.div
        initial={{ opacity: 0, x: -30 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ duration: 0.6, ease: 'easeOut' }}
        className="lg:w-1/2 p-8 lg:p-16 flex flex-col justify-between relative z-10 bg-slate-950 text-slate-100 border-b lg:border-b-0 lg:border-r border-slate-800"
      >
        {/* Subtle Background Glows on Left Side */}
        <div className="absolute top-0 left-1/4 w-[400px] h-[400px] bg-amber-500/10 rounded-full blur-3xl pointer-events-none -translate-y-1/2 -translate-x-1/2" />
        <div className="absolute bottom-0 right-1/4 w-[500px] h-[500px] bg-blue-600/10 rounded-full blur-3xl pointer-events-none translate-y-1/3 translate-x-1/3" />

        <div className="relative z-10">
          {/* Brand Header */}
          <div className="flex items-center gap-4 mb-8">
            <img
              src="/logo/LOGO-M6.png"
              alt="M-6 Gemelo Digital"
              className="w-16 h-16 object-contain drop-shadow-[0_0_15px_rgba(245,158,11,0.3)]"
            />
            <div>
              <h1 className="text-2xl font-extrabold tracking-tight text-white font-display">
                M-6 GEMELO DIGITAL
              </h1>
              <p className="text-xs uppercase tracking-wider text-amber-400 font-semibold">
                Control de Leyes Mineras & IA Bayesiana
              </p>
            </div>
          </div>

          {/* System Purpose & Description */}
          <div className="space-y-6 max-w-xl">
            <h2 className="text-3xl lg:text-4xl font-bold tracking-tight text-slate-100 leading-tight">
              Visualización 3D académica con <span className="text-transparent bg-clip-text bg-gradient-to-r from-amber-400 to-amber-200">estimación exploratoria de cobre</span>
            </h2>

            <p className="text-sm text-slate-300 leading-relaxed">
              Plataforma académica para explorar leyes de cobre (Cu%) en minería a cielo abierto. El visor Copper Creek usa sondajes públicos y geometría aproximada; los módulos operacionales ilustran flujos con datos generados.
            </p>

            {/* Key Capabilities Badges */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-4">
              <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800/80 hover:border-amber-500/40 transition-colors">
                <div className="flex items-center gap-3 mb-2 text-amber-400">
                  <Cpu className="w-5 h-5" />
                  <span className="font-semibold text-sm text-slate-100">Motor de 5 Modelos ML</span>
                </div>
                <p className="text-xs text-slate-400 leading-normal">
                  Red Neuronal Bayesiana, Stacking Ensemble, XGBoost, Random Forest y Kriging Ordinario.
                </p>
              </div>

              <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800/80 hover:border-amber-500/40 transition-colors">
                <div className="flex items-center gap-3 mb-2 text-amber-400">
                  <Activity className="w-5 h-5" />
                  <span className="font-semibold text-sm text-slate-100">Predicción P10-P50-P90</span>
                </div>
                <p className="text-xs text-slate-400 leading-normal">
                  Salidas ilustrativas del modelo de ejemplo; no clasifican material para despacho real.
                </p>
              </div>

              <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800/80 hover:border-amber-500/40 transition-colors">
                <div className="flex items-center gap-3 mb-2 text-amber-400">
                  <ShieldCheck className="w-5 h-5" />
                  <span className="font-semibold text-sm text-slate-100">Alcance académico documentado</span>
                </div>
                <p className="text-xs text-slate-400 leading-normal">
                  Resultados exploratorios y datos de demostración, sin certificación de recursos ni reservas.
                </p>
              </div>

              <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800/80 hover:border-amber-500/40 transition-colors">
                <div className="flex items-center gap-3 mb-2 text-amber-400">
                  <Layers className="w-5 h-5" />
                  <span className="font-semibold text-sm text-slate-100">Reconciliación de Banco</span>
                </div>
                <p className="text-xs text-slate-400 leading-normal">
                  Alertas automáticas de alta incertidumbre y riesgo de dilución operacional en producción.
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* Footer info */}
        <div className="mt-12 pt-6 border-t border-slate-800/60 flex items-center justify-between text-xs text-slate-500 font-mono relative z-10">
          <span>SISTEMA M-6 v1.0</span>
          <span>EPSG:32719 • UTM Zone 19S</span>
        </div>
      </motion.div>

      {/* RIGHT COLUMN: Clean White Background Login */}
      <motion.div
        initial={{ opacity: 0, x: 30 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ duration: 0.6, ease: 'easeOut', delay: 0.1 }}
        className="lg:w-1/2 p-8 lg:p-16 flex flex-col justify-center bg-white text-slate-900 relative z-10 w-full"
      >
        <div className="max-w-md mx-auto w-full">
          {/* Header */}
          <div className="mb-8">
            <h2 className="text-3xl font-extrabold tracking-tight text-slate-900 font-display">
              Iniciar Sesión
            </h2>
            <p className="text-sm text-slate-500 mt-2">
              Ingresa con tus credenciales institucionales para acceder a la plataforma
            </p>
          </div>

          {/* Borderless Form */}
          <form onSubmit={handleSubmit} className="space-y-5">
            {/* Email */}
            <div>
              <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-2">
                Correo Electrónico
              </label>
              <div className="relative">
                <Mail className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                <input
                  type="email"
                  value={email}
                  onChange={e => setEmail(e.target.value)}
                  placeholder="usuario@m6gemelo.cl"
                  className="w-full pl-11 pr-4 py-3 bg-slate-50 border border-slate-200 focus:border-amber-500 focus:bg-white rounded-xl text-sm text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-1 focus:ring-amber-500 transition-all"
                  required
                />
              </div>
            </div>

            {/* Password */}
            <div>
              <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-2">
                Contraseña
              </label>
              <div className="relative">
                <Lock className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                <input
                  type={showPassword ? 'text' : 'password'}
                  value={password}
                  onChange={e => setPassword(e.target.value)}
                  placeholder="••••••••"
                  className="w-full pl-11 pr-11 py-3 bg-slate-50 border border-slate-200 focus:border-amber-500 focus:bg-white rounded-xl text-sm text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-1 focus:ring-amber-500 transition-all"
                  required
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 transition-colors"
                >
                  {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
            </div>

            {/* Error Message */}
            {error && (
              <motion.div
                initial={{ opacity: 0, y: -6 }}
                animate={{ opacity: 1, y: 0 }}
                className="flex items-center gap-3 p-3.5 bg-red-50 border border-red-200 rounded-xl text-xs text-red-700"
              >
                <AlertCircle className="w-4 h-4 shrink-0 text-red-500" />
                <span>{error}</span>
              </motion.div>
            )}

            {/* Submit Button */}
            <button
              type="submit"
              disabled={isSubmitting}
              className="w-full py-3.5 bg-amber-500 hover:bg-amber-400 active:bg-amber-600 disabled:opacity-50 disabled:cursor-not-allowed text-slate-950 font-bold text-sm rounded-xl shadow-md shadow-amber-500/20 transition-all duration-200 flex items-center justify-center gap-2 tracking-wide"
            >
              {isSubmitting ? (
                <span className="w-5 h-5 border-2 border-slate-950 border-t-transparent rounded-full animate-spin" />
              ) : (
                'Acceder al Dashboard'
              )}
            </button>
          </form>

          {/* Quick Demo Selector */}
          {import.meta.env.DEV && <div className="mt-10 pt-8 border-t border-slate-200">
            <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-4">
              Cuentas de Demostración
            </p>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
              {DEMO_USERS.map((u, idx) => (
                <button
                  key={idx}
                  onClick={() => fillDemo(u)}
                  type="button"
                  className="flex items-center gap-3 p-2.5 bg-slate-50 hover:bg-slate-100/80 border border-slate-200/80 hover:border-amber-500/60 rounded-xl text-left transition-all duration-150 group"
                >
                  <div className="w-8 h-8 rounded-lg bg-amber-500/15 text-amber-700 group-hover:bg-amber-500 group-hover:text-slate-950 flex items-center justify-center text-xs font-bold shrink-0 transition-colors">
                    {u.name.charAt(0)}
                  </div>
                  <div className="min-w-0">
                    <div className="text-xs font-semibold text-slate-800 group-hover:text-slate-950 truncate">
                      {u.name}
                    </div>
                    <div className="text-[10px] text-slate-500 truncate font-mono">
                      {u.role}
                    </div>
                  </div>
                </button>
              ))}
            </div>
          </div>}
        </div>
      </motion.div>
    </div>
  );
};

