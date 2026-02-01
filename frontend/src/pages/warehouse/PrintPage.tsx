import { useEffect, useState } from "react";

import { CompanySelect } from "../../components/shared/CompanySelect";
import { Button } from "../../components/ui/Button";
import { Input } from "../../components/ui/Input";
import { useActiveCompany } from "../../hooks/useActiveCompany";
import { useCompanies } from "../../hooks/useCompanies";
import { useProducts } from "../../hooks/useProducts";
import { apiClient } from "../../services/api";

export function PrintPage() {
  const { data: companies = [] } = useCompanies();
  const { companyId, setCompanyId } = useActiveCompany();
  const activeCompanyId = companyId ?? companies[0]?.id ?? null;
  const { data: products = [], isLoading } = useProducts(activeCompanyId ?? undefined);
  const [query, setQuery] = useState("");
  const [pageError, setPageError] = useState<string | null>(null);

  useEffect(() => {
    if (!companyId && companies.length > 0) {
      setCompanyId(companies[0].id);
    }
  }, [companies, companyId, setCompanyId]);

  if (companies.length === 0) {
    return (
      <div className="rounded-lg border border-slate-800 bg-slate-900/60 p-4 text-sm text-slate-200">
        Сначала добавьте компанию, чтобы печатать этикетки.
      </div>
    );
  }

  const filtered = products.filter((product) => {
    const term = query.trim().toLowerCase();
    if (!term) return true;
    return product.name.toLowerCase().includes(term) || product.barcode?.includes(term);
  });

  const handlePrint = async (productId: number) => {
    setPageError(null);
    try {
      const { blob, filename } = await apiClient.apiFile(`/products/${productId}/label`);
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = filename ?? `label_${productId}.pdf`;
      link.click();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch (err) {
      setPageError(err instanceof Error ? err.message : "Не удалось скачать этикетку");
    }
  };

  return (
    <div className="space-y-4">
      <CompanySelect companies={companies} value={activeCompanyId} onChange={setCompanyId} />
      <Input
        label="Поиск по артикулу/баркоду"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
      />

      {pageError ? <div className="text-sm text-rose-300">{pageError}</div> : null}
      {isLoading ? <div className="text-sm text-slate-300">Загрузка товаров...</div> : null}

      <div className="space-y-2">
        {filtered.map((product) => (
          <div key={product.id} className="rounded-xl border border-slate-800 bg-slate-900/60 p-4 shadow-sm">
            <div className="text-sm font-semibold text-slate-100">{product.name}</div>
            <div className="text-xs text-slate-400">ШК: {product.barcode ?? "—"}</div>
            <Button className="mt-2" variant="secondary" onClick={() => handlePrint(product.id)}>
              Печать ШК
            </Button>
          </div>
        ))}
      </div>
    </div>
  );
}
