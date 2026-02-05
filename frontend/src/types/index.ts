/** Shared types aligned with backend API responses. */

export type CurrentUser = {
  id: number;
  telegram_id: number;
  telegram_username: string | null;
  first_name: string | null;
  last_name: string | null;
  role: string;
};

export type Company = {
  id: number;
  inn: string;
  name: string;
  legal_form: string | null;
  director: string | null;
  bank_bik: string | null;
  bank_account: string | null;
  kpp: string | null;
  ogrn: string | null;
  legal_address: string | null;
  okved: string | null;
  okved_name: string | null;
  bank_name: string | null;
  bank_corr_account: string | null;
};

export type Product = {
  id: number;
  company_id: number;
  name: string;
  brand: string | null;
  size: string | null;
  color: string | null;
  barcode: string | null;
  wb_article: string | null;
  wb_url: string | null;
  packing_instructions: string | null;
  supplier_name: string | null;
  stock_quantity: number;
  defect_quantity: number;
};

export type Order = {
  id: number;
  company_id: number;
  order_number: string;
  status: string;
  destination: string | null;
  planned_qty: number;
  received_qty: number;
  packed_qty: number;
  photo_count?: number;
};

export type OrderItem = {
  id: number;
  product_id: number;
  product_name: string;
  barcode: string | null;
  brand: string | null;
  size: string | null;
  color: string | null;
  wb_article: string | null;
  wb_url: string | null;
  packing_instructions: string | null;
  supplier_name: string | null;
  planned_qty: number;
  received_qty: number;
  defect_qty: number;
  packed_qty: number;
  adjustment_qty: number;
  adjustment_note: string | null;
  destination: string | null;
};

export type OrderPhoto = {
  id: number;
  s3_key: string;
  url: string;
  photo_type: string | null;
  product_id: number | null;
  created_at: string;
};

export type Destination = {
  id: number;
  name: string;
  is_active: boolean;
};

export type Service = {
  id: number;
  category: string;
  name: string;
  price: number;
  unit: string;
  comment: string | null;
  is_active: boolean;
  sort_order: number;
};

export type ServiceCalculateResponse = {
  items: { service_id: number; name: string; category: string; price: number; unit: string; quantity: number; subtotal: number }[];
  total: number;
};

export type ShippingRequest = {
  id: number;
  company_id: number;
  destination_type: string;
  destination_comment: string | null;
  status: string;
  created_at: string;
};
