import { useState, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useContestInfo, useWebSocket } from '@/hooks';
import { ProgressBar } from '@/components/ProgressBar';
import { RankingList } from '@/components/RankingList';
import type { Category } from '@/types';

export default function App() {
  const { info, error, loading, reload } = useContestInfo();
  const [category, setCategory] = useState<Category>('day');
  const [refreshKey, setRefreshKey] = useState(0);

  const handleWsMessage = useCallback((msg: unknown) => {
    const m = msg as { type?: string };
    if (m.type === 'receipt:approved' || m.type === 'receipt:rejected') {
      setRefreshKey(k => k + 1);
    }
  }, []);

  useWebSocket(handleWsMessage, () => { void reload(); });

  return (
    <div className="min-h-screen px-4 py-6 max-w-lg mx-auto">
      {/* Header */}
      <motion.div
        className="text-center mb-6"
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
      >
        <h1 className="text-3xl font-bold text-white mb-1">🧪 Колба</h1>
        <p className="text-slate-400 text-sm">Конкурс продавцов</p>
      </motion.div>

      {/* Category switcher */}
      <motion.div
        className="flex gap-2 mb-6"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.1 }}
      >
        {(['day', 'night'] as Category[]).map((cat) => (
          <button
            key={cat}
            onClick={() => setCategory(cat)}
            className={`flex-1 py-2 rounded-lg font-semibold text-sm transition-colors ${
              category === cat
                ? cat === 'day'
                  ? 'bg-amber-400 text-slate-900'
                  : 'bg-indigo-500 text-white'
                : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
            }`}
          >
            {cat === 'day' ? '☀️ Дневные' : '🌙 Ночные'}
          </button>
        ))}
      </motion.div>

      {/* Loading state */}
      <AnimatePresence mode="wait">
        {loading && (
          <motion.div
            key="loading"
            className="flex justify-center py-12"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
          >
            <div className="w-8 h-8 border-2 border-slate-400 border-t-transparent rounded-full animate-spin" />
          </motion.div>
        )}

        {/* Error state */}
        {error && !loading && (
          <motion.div
            key="error"
            className="bg-red-900/50 border border-red-700 rounded-xl p-4 text-center"
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
          >
            <p className="text-red-300 text-sm">{error}</p>
            <p className="text-slate-400 text-xs mt-2">Проверьте подключение к серверу</p>
          </motion.div>
        )}

        {/* Content */}
        {info && !loading && (
          <motion.div
            key={`content-${category}`}
            className="space-y-4"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
          >
            {/* Progress */}
            <ProgressBar
              label={category === 'day' ? '☀️ Дневные' : '🌙 Ночные'}
              current={category === 'day' ? info.day_approved : info.night_approved}
              goal={category === 'day' ? info.day_goal : info.night_goal}
              color={category === 'day' ? 'amber' : 'indigo'}
              pct={category === 'day' ? info.day_progress_pct : info.night_progress_pct}
            />

            {/* Counter */}
            <div className="bg-slate-800/60 rounded-xl p-4 text-center backdrop-blur-sm border border-slate-700/50">
              <div className="text-4xl font-bold text-white mb-1">
                {category === 'day' ? info.day_approved : info.night_approved}
              </div>
              <div className="text-slate-400 text-sm">
                из {category === 'day' ? info.day_goal : info.night_goal} чеков
              </div>
            </div>

            {/* Deadlines */}
            {info.is_finalized ? (
              <div className="bg-emerald-900/40 border border-emerald-700/50 rounded-xl p-4 text-center">
                <p className="text-emerald-300 font-semibold">🏁 Конкурс завершён!</p>
                <p className="text-emerald-200/70 text-sm mt-1">Розыгрыш состоялся</p>
              </div>
            ) : (
              <div className="bg-slate-800/40 rounded-xl p-3 text-center text-xs text-slate-400 space-y-1">
                <p>📅 Приём чеков до {info.end_at_msk}</p>
                <p>🎰 Розыгрыш в {info.raffle_at_msk}</p>
              </div>
            )}

            {/* Ranking */}
            <RankingList key={refreshKey} category={category} />

            {/* Footer */}
            <div className="text-center text-slate-500 text-xs pt-2 pb-4">
              Обновляется автоматически
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}