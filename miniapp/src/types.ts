export interface SellerStat {
  id: number;
  name: string;
  shop?: string;
  count: number;
}

export interface ShopStat {
  id: number;
  name: string;
  count: number;
}

export interface ContestInfo {
  end_at_msk: string;
  raffle_at_msk: string;
  day_goal: number;
  night_goal: number;
  day_approved: number;
  night_approved: number;
  day_progress_pct: number;
  night_progress_pct: number;
  is_finalized: boolean;
}

export interface RankingResponse {
  category: string;
  sellers: SellerStat[];
  shops: ShopStat[];
}

export interface WsMessage {
  type: 'init' | 'receipt:approved' | 'receipt:rejected' | 'contest:finalized' | 'pong';
  day_approved?: number;
  night_approved?: number;
  day_goal?: number;
  night_goal?: number;
  sellers_day?: { name: string; count: number }[];
  sellers_night?: { name: string; count: number }[];
  receipt_id?: number;
  category?: string;
  new_total?: number;
  winner_day?: string | null;
  winner_night?: string | null;
}

export type Category = 'day' | 'night';