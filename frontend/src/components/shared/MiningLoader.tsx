import { motion, useReducedMotion } from 'framer-motion';

import { useId } from 'react';

interface MiningLoaderProps {
  title?: string;
  detail?: string;
  fullScreen?: boolean;
  className?: string;
}

export function MiningLoader({
  title = 'Cargando el Gemelo Digital',
  detail,
  fullScreen = false,
  className = '',
}: MiningLoaderProps) {
  const reduceMotion = useReducedMotion();
  const innerShadowId = useId();

  return (
    <div
      role="status"
      aria-live="polite"
      className={(fullScreen ? 'min-h-screen' : 'h-full min-h-[12rem]') + ' flex w-full items-center justify-center px-4 py-6 ' + className}
    >
      <div className="flex max-w-sm flex-col items-center text-center">
        <svg aria-hidden="true" viewBox="0 0 120 68" className="h-14 w-24 overflow-visible">
          <defs>
            <filter id={innerShadowId} x="-20%" y="-20%" width="140%" height="140%" colorInterpolationFilters="sRGB">
              <feGaussianBlur in="SourceAlpha" stdDeviation="2" result="softAlpha" />
              <feOffset in="softAlpha" dx="-1" dy="-1" result="shiftedAlpha" />
              <feComposite in="SourceAlpha" in2="shiftedAlpha" operator="out" result="innerEdge" />
              <feFlood floodColor="#020617" floodOpacity="0.24" result="shade" />
              <feComposite in="shade" in2="innerEdge" operator="in" result="innerShade" />
              <feComposite in="innerShade" in2="SourceGraphic" operator="over" />
            </filter>
          </defs>
          <motion.path
            d="M6 58 L29 19 L45 42 L66 10 L91 58 Z"
            className="fill-slate-700 dark:fill-slate-300"
            filter={`url(#${innerShadowId})`}
            animate={reduceMotion ? undefined : { d: [
              'M6 58 L29 19 L45 42 L66 10 L91 58 Z',
              'M6 58 L29 31 L45 46 L66 25 L91 58 Z',
              'M6 58 L29 17 L45 41 L66 8 L91 58 Z',
              'M6 58 L29 19 L45 42 L66 10 L91 58 Z',
            ] }}
            transition={{ duration: 2.1, times: [0, 0.3, 0.55, 1], repeat: Infinity, ease: 'easeInOut' }}
          />
          <motion.path
            d="M49 62 L65 39 L76 47 L96 28 L116 62 Z"
            className="fill-amber-500"
            filter={`url(#${innerShadowId})`}
            animate={reduceMotion ? undefined : { d: [
              'M49 62 L65 39 L76 47 L96 28 L116 62 Z',
              'M49 62 L65 47 L76 50 L96 40 L116 62 Z',
              'M49 62 L65 37 L76 46 L96 25 L116 62 Z',
              'M49 62 L65 39 L76 47 L96 28 L116 62 Z',
            ] }}
            transition={{ duration: 2.1, times: [0, 0.3, 0.55, 1], repeat: Infinity, ease: 'easeInOut', delay: 0.12 }}
          />
        </svg>
        <p className="mt-2 font-display text-sm font-semibold text-slate-700 dark:text-slate-200">{title}</p>
        {detail && <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">{detail}</p>}
      </div>
    </div>
  );
}

