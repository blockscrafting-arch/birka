import { useEffect, useRef, useState } from "react";

import { CompanySelect } from "../../components/shared/CompanySelect";
import { ProductCard } from "../../components/shared/ProductCard";
import { Button } from "../../components/ui/Button";
import { Input } from "../../components/ui/Input";
import { Modal } from "../../components/ui/Modal";
import { Pagination } from "../../components/ui/Pagination";
import { Skeleton } from "../../components/ui/Skeleton";
import { Toast } from "../../components/ui/Toast";
import { useActiveCompany } from "../../hooks/useActiveCompany";
import { useCompanies } from "../../hooks/useCompanies";
import { useProducts } from "../../hooks/useProducts";
import { apiClient } from "../../services/api";
import { Product } from "../../types";
import { ProductForm } from "./ProductForm";

export function ProductsPage() {
  const { items: companies = [] } = useCompanies();
  const { companyId, setCompanyId } = useActiveCompany();
  const activeCompanyId = companyId ?? companies[0]?.id ?? null;
  const [page, setPage] = useState(1);
  const limit = 20;
  const { items, total, isLoading, error, create, update, uploadPhoto, importExcel } = useProducts(
    activeCompanyId ?? undefined,
    page,
    limit
  );
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState<Product | null>(null);
  const [query, setQuery] = useState("");
  const [pageError, setPageError] = useState<string | null>(null);
  const [toast, setToast] = useState<{ message: string; variant?: "success" | "error" } | null>(null);
  const importRef = useRef<HTMLInputElement | null>(null);

  useEffect(() => {
    if (!companyId && companies.length > 0) {
      setCompanyId(companies[0].id);
    }
  }, [companies, companyId, setCompanyId]);

  useEffect(() => {
    setPage(1);
  }, [activeCompanyId]);

  if (companies.length === 0) {
    return (
      <div className="rounded-lg border border-slate-800 bg-slate-900/60 p-4 text-sm text-slate-200">
        Сначала добавьте компанию, чтобы управлять товарами.
      </div>
    );
  }

  const totalPages = Math.max(1, Math.ceil(total / limit));
  const filtered = items.filter((product) => {
    const term = query.trim().toLowerCase();
    if (!term) return true;
    return product.name.toLowerCase().includes(term) || product.barcode?.includes(term);
  });

  const handleCreate = async (payload: {
    name: string;
    brand?: string;
    size?: string;
    color?: string;
    barcode?: string;
    wb_article?: string;
    wb_url?: string;
    packing_instructions?: string;
    photo?: File | null;
  }) => {
    if (!activeCompanyId) return;
    setPageError(null);
    try {
      const { photo, ...rest } = payload;
      const created = await create.mutateAsync({ company_id: activeCompanyId, ...rest });
      if (photo) {
        await uploadPhoto.mutateAsync({ productId: created.id, file: photo });
      }
      setOpen(false);
      setPage(1);
      setToast({ message: "Товар создан" });
    } catch (err) {
      setPageError(err instanceof Error ? err.message : "Не удалось создать товар");
    }
  };

  const handleUpdate = async (payload: {
    name: string;
    brand?: string;
    size?: string;
    color?: string;
    barcode?: string;
    wb_article?: string;
    wb_url?: string;
    packing_instructions?: string;
    photo?: File | null;
  }) => {
    if (!editing) return;
    setPageError(null);
    try {
      const { photo, ...rest } = payload;
      await update.mutateAsync({ id: editing.id, ...rest });
      if (photo) {
        await uploadPhoto.mutateAsync({ productId: editing.id, file: photo });
      }
      setEditing(null);
      setToast({ message: "Товар обновлён" });
    } catch (err) {
      setPageError(err instanceof Error ? err.message : "Не удалось обновить товар");
    }
  };

  const handleImport = async (file: File) => {
    if (!activeCompanyId) return;
    setPageError(null);
    try {
      await importExcel.mutateAsync({ companyId: activeCompanyId, file });
      setToast({ message: "Импорт завершён" });
    } catch (err) {
      setPageError(err instanceof Error ? err.message : "Ошибка импорта");
    }
  };

  const handleExport = async () => {
    if (!activeCompanyId) return;
    setPageError(null);
    try {
      const { blob, filename } = await apiClient.apiFile(`/products/export?company_id=${activeCompanyId}`);
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = filename ?? "products.xlsx";
      link.click();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
      setToast({ message: "Файл экспорта скачан" });
    } catch (err) {
      setPageError(err instanceof Error ? err.message : "Ошибка экспорта");
    }
  };

  return (
    <div className="space-y-4">
      {toast ? <Toast message={toast.message} variant={toast.variant} onClose={() => setToast(null)} /> : null}
      <CompanySelect companies={companies} value={activeCompanyId} onChange={setCompanyId} />

      <div className="flex flex-wrap items-center gap-2">
        <Button onClick={() => setOpen(true)}>Добавить товар</Button>
        <Button variant="secondary" onClick={() => importRef.current?.click()}>
          Импорт Excel
        </Button>
        <Button variant="ghost" onClick={handleExport}>
          Экспорт Excel
        </Button>
        <input
          ref={importRef}
          type="file"
          accept=".xlsx,.xls"
          className="hidden"
          onChange={(event) => {
            const file = event.target.files?.[0];
            if (file) {
              handleImport(file);
              event.target.value = "";
            }
          }}
        />
      </div>

      <Input
        label="Поиск"
        placeholder="Название или штрихкод"
        value={query}
        onChange={(event) => setQuery(event.target.value)}
      />

      {pageError ? <div className="text-sm text-rose-300">{pageError}</div> : null}
      {isLoading ? (
        <div className="space-y-2">
          <Skeleton className="h-20" />
          <Skeleton className="h-20" />
        </div>
      ) : null}
      {error ? <div className="text-sm text-rose-300">Не удалось загрузить товары</div> : null}
      {!isLoading && filtered.length === 0 ? (
        <div className="rounded-lg border border-slate-800 bg-slate-900/60 p-4 text-sm text-slate-200">
          Нет товаров для выбранной компании.
        </div>
      ) : null}

      <div className="space-y-3">
        {filtered.map((product) => (
          <ProductCard
            key={product.id}
            name={product.name}
            barcode={product.barcode}
            stock={product.stock_quantity}
            defect={product.defect_quantity}
            onClick={() => setEditing(product)}
          />
        ))}
      </div>
      <Pagination page={page} totalPages={totalPages} onPageChange={setPage} />

      <Modal title="Новый товар" open={open} onClose={() => setOpen(false)}>
        <ProductForm isSubmitting={create.isPending} onSubmit={handleCreate} submitLabel="Создать" />
      </Modal>

      <Modal title="Редактирование товара" open={Boolean(editing)} onClose={() => setEditing(null)}>
        <ProductForm
          initial={editing ?? undefined}
          isSubmitting={update.isPending}
          onSubmit={handleUpdate}
          submitLabel="Сохранить"
        />
      </Modal>
    </div>
  );
}
