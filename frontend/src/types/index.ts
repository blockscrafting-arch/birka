export type Company = {
  id: number;
  inn: string;
  name: string;
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
  stock_quantity: number;
  defect_quantity: number;
};

export type Order = {
  id: number;
  company_id: number;
  order_number: string;
  status: "На приемке" | "Принято" | "Упаковка" | "Готово к отгрузке" | "Завершено";
  planned_qty: number;
  received_qty: number;
  packed_qty: number;
};

export type OrderItem = {
  id: number;
  product_id: number;
  product_name: string;
  barcode?: string;
  planned_qty: number;
  received_qty: number;
  defect_qty: number;
  packed_qty: number;
};
