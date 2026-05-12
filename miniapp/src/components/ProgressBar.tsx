import { motion } from 'framer-motion';

interface Props {
  label: string;
  current: number;
  goal: number;
  color: 'amber' | 'indigo';
  pct: number;
}

const colorMap = {
  amber: {
    bar: 'bg-gradient-to-r from-amber-400 to-orange-400',
    glow: 'shadow-amber-500/30',
  },
  indigo: {
    bar: 'bg-gradient-to-r from-indigo-400 to-purple-400',
    glow: 'shadow-indigo-500/30',
  },
};

export function ProgressBar({ label, current, goal, color, pct }: Props) {
  const colors = colorMap[color];

  return (
    <div className="bg-slate-800/60 rounded-xl p-4 backdrop-blur-sm border border-slate-700/50">
      <div className="flex justify-between items-center mb-2">
        <span className="text-slate-300 text-sm font-medium">{label}</span>
        <span className="text-white text-sm font-bold">{pct}%</span>
      </div>
      <div className="h-3 bg-slate-700 rounded-full overflow-hidden">
        <motion.div
          className={`h-full ${colors.bar} rounded-full shadow-lg ${colors.glow}`}
          initial={{ width: 0 }}
          animate={{ width: `${Math.min(pct, 100)}%` }}
          transition={{ duration: 1, ease: 'easeOut', delay: 0.2 }}
        />
      </div>
      <div className="flex justify-between mt-1.5">
        <span className="text-slate-500 text-xs">{current} одобрено</span>
        <span className="text-slate-500 text-xs">цель: {goal}</span>
      </div>
    </div>
  );
}