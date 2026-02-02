export type Company = {
  id: number;
  inn: string;
  name: string;
  legal_form?: string;
  director?: string;
  bank_bik?: string;
  bank_account?: string;
};

export type Destination = {
  id: number;
  name: string;
  is_active: boolean;
};

export type Product = {
  id: number;
  company_id: number;
  name: string;
  brand?: string;
  size?: string;
  color?: string;
  barcode?: string;
  wb_article?: string;
  wb_url?: string;
  packing_instructions?: string;
  supplier_name?: string;
  stock_quantity: number;
  defect_quantity: number;
};

export type Order = {
  id: number;
  company_id: number;
  order_number: string;
  status: "На приемке" | "Принято" | "Упаковка" | "Готово к отгрузке" | "Завершено";
  destination?: string;
  planned_qty: number;
  received_qty: number;
  packed_qty: number;
  photo_count?: number;
};

export type OrderItem = {
  id: number;
  product_id: number;
  product_name: string;
  barcode?: string;
  brand?: string;
  size?: string;
  color?: string;
  wb_article?: string;
  wb_url?: string;
  packing_instructions?: string;
  supplier_name?: string;
  planned_qty: number;
  received_qty: number;
  defect_qty: number;
  packed_qty: number;
  adjustment_qty: number;
  adjustment_note?: string;
};

export type OrderPhoto = {
  id: number;
  s3_key: string;
  url: string;
  photo_type?: string | null;
  created_at: string;
};

export type ShippingRequest = {
  id: number;
  company_id: number;
  destination_type: string;
  destination_comment?: string | null;
  status: string;
  created_at: string;
};

export type CurrentUser = {
  id: number;
  telegram_id: number;
  telegram_username?: string | null;
  first_name?: string | null;
  last_name?: string | null;
  role: "client" | "warehouse" | "admin";
};

export type AdminUser = {
  id: number;
  telegram_id: number;
  telegram_username?: string | null;
  first_name?: string | null;
  last_name?: string | null;
  role: "client" | "warehouse" | "admin";
  created_at: string;
};

export type ContractTemplate = {
  id: number;
  name: string;
  html_content: string;
  is_default: boolean;
  created_at: string;
  updated_at: string;
};
