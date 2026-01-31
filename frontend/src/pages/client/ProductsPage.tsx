import { useState } from "react";

import { Button } from "../../components/ui/Button";
import { Modal } from "../../components/ui/Modal";
import { ProductCard } from "../../components/shared/ProductCard";
import { ProductForm } from "./ProductForm";

const demoProducts = [
  { id: 1, name: "Шлем боксерский", barcode: "2044283645181", stock: 30, defect: 0 },
];

export function ProductsPage() {
  const [open, setOpen] = useState(false);

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap gap-2">
        <Button onClick={() => setOpen(true)}>Добавить товар</Button>
        <Button variant="secondary">Импорт Excel</Button>
        <Button variant="ghost">Экспорт Excel</Button>
      </div>

      {demoProducts.map((product) => (
        <ProductCard
          key={product.id}
          name={product.name}
          barcode={product.barcode}
          stock={product.stock}
          defect={product.defect}
        />
      ))}

      <Modal title="Новый товар" open={open} onClose={() => setOpen(false)}>
        <ProductForm onSubmit={() => setOpen(false)} />
      </Modal>
    </div>
  );
}
