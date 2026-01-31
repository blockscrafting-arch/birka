import { useState } from "react";

import { Button } from "../../components/ui/Button";
import { Input } from "../../components/ui/Input";
import { Select } from "../../components/ui/Select";

const demoProducts = [
  { id: 1, name: "Шлем боксерский", barcode: "2044283645181" },
];

export function PrintPage() {
  const [companyId, setCompanyId] = useState("");
  const [query, setQuery] = useState("");

  return (
    <div className="space-y-3">
      <Select label="Компания" value={companyId} onChange={(e) => setCompanyId(e.target.value)}>
        <option value="">Выберите компанию</option>
        <option value="1">ИП Белогур Д.А.</option>
      </Select>
      <Input label="Поиск по артикулу/баркоду" value={query} onChange={(e) => setQuery(e.target.value)} />

      <div className="space-y-2">
        {demoProducts.map((product) => (
          <div key={product.id} className="rounded bg-white p-4 shadow-sm">
            <div className="text-sm font-semibold">{product.name}</div>
            <div className="text-xs text-slate-600">ШК: {product.barcode}</div>
            <Button className="mt-2" variant="secondary">
              Печать ШК
            </Button>
          </div>
        ))}
      </div>
    </div>
  );
}
