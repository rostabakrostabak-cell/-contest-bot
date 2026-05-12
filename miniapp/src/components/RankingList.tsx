import { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { fetchRanking } from '@/api';
import type { Category, RankingResponse, SellerStat } from '@/types';

interface Props {
  category: Category;
}

export function RankingList({ category }: Props) {
  const [data, setData] = useState<RankingResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);

    fetchRanking(category)
      .then((result) => {
        if (!cancelled) setData(result);
      })
      .catch((e) => {
        if (!cancelled) setError(e instanceof Error ? e.message : 'Ошибка');
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => { cancelled = true; };
  }, [category]);

  if (loading) {
    return (
      <div className="flex justify-center py-6">
        <div className="w-6 h-6 border-2 border-slate-400 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-slate-800/40 rounded-xl p-4 text-center">
        <p className="text-slate-500 text-xs">Рейтинг временно недоступен</p>
      </div>
    );
  }

  if (!data) return null;

  const colorClass = category === 'day' ? 'text-amber-400' : 'text-indigo-400';

  return (
    <div className="space-y-4">
      {/* Sellers ranking */}
      <div className="bg-slate-800/60 rounded-xl p-4 backdrop-blur-sm border border-slate-700/50">
        <h3 className={`text-sm font-bold mb-3 ${colorClass}`}>🏆 Топ продавцов</h3>
        {data.sellers.length === 0 ? (
          <p className="text-slate-500 text-sm text-center py-4">Пока нет данных</p>
        ) : (
          <div className="space-y-2">
            {data.sellers.map((seller, i) => (
              <RankingRow key={seller.id} rank={i + 1} seller={seller} category={category} />
            ))}
          </div>
        )}
      </div>

      {/* Shops ranking */}
      <div className="bg-slate-800/40 rounded-xl p-4 backdrop-blur-sm border border-slate-700/30">
        <h3 className="text-sm font-bold text-slate-400 mb-3">🏪 Топ магазинов</h3>
        {data.shops.length === 0 ? (
          <p className="text-slate-600 text-sm text-center py-2">—</p>
        ) : (
          <div className="space-y-1">
            {data.shops.map((shop, i) => (
              <div key={shop.id} className="flex items-center gap-3 py-1">
                <span className="text-slate-500 text-sm font-mono w-5">{i + 1}.</span>
                <span className="text-slate-300 text-sm flex-1">{shop.name}</span>
                <span className="text-white text-sm font-bold">{shop.count}</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function RankingRow({ rank, seller, category }: {
  rank: number;
  seller: SellerStat;
  category: Category;
}) {
  const medalEmoji = ['🥇', '🥈', '🥉'];

  return (
    <motion.div
      className="flex items-center gap-3 py-1.5"
      initial={{ opacity: 0, x: -10 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ delay: rank * 0.05 }}
    >
      <span className={`w-5 text-center text-lg ${rank <= 3 ? medalEmoji[rank - 1] : `${rank}.`}`} />
      <div className="flex-1">
        <span className="text-white text-sm font-medium">{seller.name}</span>
        {seller.shop && (
          <span className="text-slate-500 text-xs ml-2">({seller.shop})</span>
        )}
      </div>
      <span className={`text-sm font-bold ${
        category === 'day' ? 'text-amber-400' : 'text-indigo-400'
      }`}>
        {seller.count}
      </span>
    </motion.div>
  );
}