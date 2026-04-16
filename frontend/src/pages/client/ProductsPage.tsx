import { useEffect, useState } from "react";

import { ProductCard } from "../../components/shared/ProductCard";
import { Button } from "../../components/ui/Button";
import { Input } from "../../components/ui/Input";
import { Modal } from "../../components/ui/Modal";
import { Pagination } from "../../components/ui/Pagination";
import { Skeleton } from "../../components/ui/Skeleton";
import { Toast } from "../../components/ui/Toast";
import { useCompanies } from "../../hooks/useCompanies";
import { useProducts } from "../../hooks/useProducts";
import { useProductDefectPhotos } from "../../hooks/useProductDefectPhotos";
import { apiClient } from "../../services/api";
import { Product } from "../../types";
import { ProductForm } from "./ProductForm";

export function ProductsPage() {
  const { items: companies = [] } = useCompanies();
  const activeCompanyId = companies[0]?.id ?? null;
  const [searchInput, setSearchInput] = useState("");
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const limit = 20;
  const { items, total, isLoading, error, update, uploadPhoto } = useProducts(
    activeCompanyId ?? undefined,
    page,
    limit,
    search
  );
  const [editing, setEditing] = useState<Product | null>(null);
  const [defectProduct, setDefectProduct] = useState<Product | null>(null);
  const [exporting, setExporting] = useState(false);
  const [pageError, setPageError] = useState<string | null>(null);
  const [toast, setToast] = useState<{ message: string; variant?: "success" | "error" } | null>(null);
  const { data: defectPhotos = [], isLoading: defectLoading } = useProductDefectPhotos(defectProduct?.id);

  useEffect(() => {
    setPage(1);
  }, [activeCompanyId]);

  useEffect(() => {
    const handler = window.setTimeout(() => {
      setSearch(searchInput.trim());
      setPage(1);
    }, 300);
    return () => window.clearTimeout(handler);
  }, [searchInput]);

  if (companies.length === 0) {
    return (
      <div className="rounded-lg border border-slate-200 bg-white p-4 text-sm text-slate-700 shadow-soft">
        Сначала добавьте компанию, чтобы управлять товарами.
      </div>
    );
  }

  const totalPages = Math.max(1, Math.ceil(total / limit));

  const handleUpdate = async (payload: {
    name: string;
    brand?: string;
    size?: string;
    color?: string;
    barcode?: string;
    wb_article?: string;
    wb_url?: string;
    packing_instructions?: string;
    supplier_name?: string;
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

  const handleExport = async () => {
    if (!activeCompanyId) return;
    setPageError(null);
    if (total === 0) {
      setToast({ message: "Нет товаров для экспорта", variant: "error" });
      return;
    }
    setExporting(true);
    try {
      await apiClient.api(`/products/export/send?company_id=${activeCompanyId}`, { method: "POST" });
      setToast({ message: "Файл отправлен в чат с ботом" });
    } catch (err) {
      setPageError(err instanceof Error ? err.message : "Ошибка экспорта");
    } finally {
      setExporting(false);
    }
  };

  return (
    <div className="space-y-4">
      {toast ? <Toast message={toast.message} variant={toast.variant} onClose={() => setToast(null)} /> : null}

      <div className="flex flex-wrap items-center gap-2">
        <Button
          variant="secondary"
          onClick={async () => {
            setPageError(null);
            try {
              await apiClient.api("/products/template/send", { method: "POST" });
              setToast({ message: "Файл отправлен в чат с ботом" });
            } catch (err) {
              setPageError(err instanceof Error ? err.message : "Ошибка отправки шаблона");
            }
          }}
        >
          Отправить шаблон в Telegram
        </Button>
        <Button variant="ghost" onClick={handleExport} disabled={exporting}>
          {exporting ? "Экспортирую..." : "Экспорт Excel"}
        </Button>
      </div>

      <Input
        label="Поиск"
        placeholder="Название или штрихкод"
        value={searchInput}
        onChange={(event) => setSearchInput(event.target.value)}
      />

      {pageError ? <div className="text-sm text-rose-500">{pageError}</div> : null}
      {isLoading ? (
        <div className="space-y-2">
          <Skeleton className="h-20" />
          <Skeleton className="h-20" />
        </div>
      ) : null}
      {error ? <div className="text-sm text-rose-500">Не удалось загрузить товары</div> : null}
      {!isLoading && items.length === 0 ? (
        <div className="rounded-xl border border-slate-200 bg-white p-6 text-center shadow-soft">
          <p className="text-sm text-slate-600">Нет товаров. Новые товары появляются при импорте заявки.</p>
        </div>
      ) : null}

      <div className="space-y-3">
        {items.map((product) => (
          <ProductCard
            key={product.id}
            name={product.name}
            barcode={product.barcode ?? undefined}
            stock={product.stock_quantity}
            defect={product.defect_quantity}
            onClick={() => setEditing(product)}
            onShowDefects={() => setDefectProduct(product)}
          />
        ))}
      </div>
      <Pagination page={page} totalPages={totalPages} onPageChange={setPage} />

      <Modal title="Редактирование товара" open={Boolean(editing)} onClose={() => setEditing(null)}>
        <ProductForm
          initial={editing ? {
            name: editing.name,
            brand: editing.brand ?? undefined,
            size: editing.size ?? undefined,
            color: editing.color ?? undefined,
            barcode: editing.barcode ?? undefined,
            wb_article: editing.wb_article ?? undefined,
            wb_url: editing.wb_url ?? undefined,
            packing_instructions: editing.packing_instructions ?? undefined,
            supplier_name: editing.supplier_name ?? undefined,
          } : undefined}
          isSubmitting={update.isPending}
          onSubmit={handleUpdate}
          submitLabel="Сохранить"
        />
      </Modal>

      <Modal title="Фото брака" open={Boolean(defectProduct)} onClose={() => setDefectProduct(null)}>
        {defectLoading ? (
          <div className="text-sm text-slate-600">Загрузка фото...</div>
        ) : (
          <div className="space-y-2">
            {defectPhotos.length === 0 ? (
              <div className="text-sm text-slate-600">Фото брака не найдено.</div>
            ) : (
              <div className="grid grid-cols-3 gap-2">
                {defectPhotos.map((url) => (
                  <img key={url} src={url} alt="defect" className="h-24 w-full rounded-xl object-cover" />
                ))}
              </div>
            )}
          </div>
        )}
      </Modal>
    </div>
  );
}
