// 데이터·API 계약서(doc/data-contract.md) 3.2·3.3의 응답 형식

export const CATEGORIES = ["용역", "공사", "물품", "외자"] as const;
export type Category = (typeof CATEGORIES)[number];

export interface BidSummary {
  summary: string;
  qualifications: string | null;
  required_documents: string[];
  ai_generated: boolean;
  model: string;
}

export interface Bid {
  id: number;
  bid_ntce_no: string;
  bid_ntce_ord: string;
  category: Category;
  bid_ntce_nm: string;
  ntce_instt_nm: string | null;
  dminstt_nm: string | null;
  presmpt_prce: number | null;
  bid_ntce_dt: string | null;
  bid_clse_dt: string | null;
  openg_dt: string | null;
  bid_ntce_dtl_url: string | null;
  summary: BidSummary | null;
}

export interface Attachment {
  name: string;
  url: string;
}

export interface BidDetail extends Bid {
  attachments: Attachment[];
}

export interface BidList {
  items: Bid[];
  total: number;
  page: number;
  size: number;
}

// GET /api/bids 쿼리 파라미터 (모두 선택)
export interface BidQuery {
  category?: Category;
  q?: string;
  institution?: string;
  min_price?: string;
  max_price?: string;
  closing_from?: string;
  closing_to?: string;
  page?: string;
}
