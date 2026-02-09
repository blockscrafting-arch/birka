import { useEffect, useState } from "react";

import { CompanySelect } from "../../components/shared/CompanySelect";
import { Button } from "../../components/ui/Button";
import { Input } from "../../components/ui/Input";
import { Modal } from "../../components/ui/Modal";
import { Select } from "../../components/ui/Select";
import { Skeleton } from "../../components/ui/Skeleton";
import { Toast } from "../../components/ui/Toast";
import { useActiveCompany } from "../../hooks/useActiveCompany";
import { useCompanies } from "../../hooks/useCompanies";
import { useFBOSupplies, FBOSupply } from "../../hooks/useFBOSupplies";
import { useProducts } from "../../hooks/useProducts";

export function FBOPage() {
  const { data: companies = [] } = useCompanies();
  const { companyId, setCompanyId } = useActiveCompany();
  const activeCompanyId = companyId ?? companies[0]?.id ?? null;
  const { data: supplies, isLoading, create, sync, remove, importBarcodes, downloadLabels } =
    useFBOSupplies(activeCompanyId);
  const { data: products = [] } = useProducts(activeCompanyId ?? undefined);
  const [marketplaceFilter, setMarketplaceFilter] = useState<string>("all");
  const [openCreate, setOpenCreate] = useState(false);
  const [importSupplyId, setImportSupplyId] = useState<number | null>(null);
  const [importText, setImportText] = useState("");
  const [pageError, setPageError] = useState<string | null>(null);
  const [toast, setToast] = useState<{ message: string; variant?: "success" | "error" } | null>(null);

  useEffect(() => {
    if (!companyId && companies.length > 0) {
      setCompanyId(companies[0].id);
    }
  }, [companies, companyId, setCompanyId]);

  const filtered = supplies.filter((s) => marketplaceFilter === "all" || s.marketplace === marketplaceFilter);

  const handleCreate = async (payload: {
    company_id: number;
    marketplace: "wb" | "ozon";
    warehouse_name?: string;
    boxes: { box_number: number; items: { product_id: number; quantity: number }[] }[];
  }) => {
    setPageError(null);
    try {
      await create.mutateAsync(payload);
      setOpenCreate(false);
      setToast({ message: "Поставка создана" });
    } catch (err) {
      setPageError(err instanceof Error ? err.message : "Не удалось создать поставку");
    }
  };

  const handleSync = async (supply: FBOSupply) => {
    setPageError(null);
    try {
      await sync.mutateAsync(supply.id);
      setToast({ message: "Поставка синхронизирована" });
    } catch (err) {
      setPageError(err instanceof Error ? err.message : "Ошибка синхронизации");
    }
  };

  const handleDownloadLabels = async (supplyId: number) => {
    setPageError(null);
    try {
      const { blob, filename } = await downloadLabels(supplyId);
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = filename ?? "fbo_labels.pdf";
      link.click();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
      setToast({ message: "Файл скачан" });
    } catch (err) {
      setPageError(err instanceof Error ? err.message : "Не удалось скачать этикетки");
    }
  };

  const handleImportBarcodes = async () => {
    if (!importSupplyId) return;
    const barcodes: Record<number, string> = {};
    importText
      .trim()
      .split(/\n/)
      .forEach((line) => {
        const [num, code] = line.split(/\s+/);
        const n = parseInt(num, 10);
        if (!isNaN(n) && code) barcodes[n] = code;
      });
    if (Object.keys(barcodes).length === 0) {
      setPageError("Введите строки: номер_короба штрихкод");
      return;
    }
    setPageError(null);
    try {
      await importBarcodes.mutateAsync({ supplyId: importSupplyId, barcodes });
      setImportSupplyId(null);
      setImportText("");
      setToast({ message: "ШК импортированы" });
    } catch (err) {
      setPageError(err instanceof Error ? err.message : "Ошибка импорта");
    }
  };

  const handleDelete = async (supply: FBOSupply) => {
    if (supply.status !== "draft") return;
    setPageError(null);
    try {
      await remove.mutateAsync(supply.id);
      setToast({ message: "Поставка удалена" });
    } catch (err) {
      setPageError(err instanceof Error ? err.message : "Не удалось удалить");
    }
  };

  if (companies.length === 0) {
    return (
      <div className="rounded-lg border border-slate-800 bg-slate-900/60 p-4 text-sm text-slate-200">
        Сначала добавьте компанию.
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {toast ? <Toast message={toast.message} variant={toast.variant} onClose={() => setToast(null)} /> : null}
      <CompanySelect companies={companies} value={activeCompanyId} onChange={setCompanyId} />

      <div className="flex flex-wrap items-center gap-2">
        <Select
          value={marketplaceFilter}
          onChange={(e) => setMarketplaceFilter(e.target.value)}
          className="rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-slate-200"
        >
          <option value="all">Все</option>
          <option value="wb">WB</option>
          <option value="ozon">Ozon</option>
        </Select>
        <Button onClick={() => setOpenCreate(true)}>Создать поставку</Button>
      </div>

      {pageError ? <div className="text-sm text-rose-300">{pageError}</div> : null}

      {isLoading ? (
        <div className="space-y-2">
          <Skeleton className="h-24" />
          <Skeleton className="h-24" />
        </div>
      ) : filtered.length === 0 ? (
        <div className="rounded-lg border border-slate-800 bg-slate-900/60 p-4 text-sm text-slate-200">
          Нет FBO-поставок для выбранной компании.
        </div>
      ) : (
        <div className="space-y-3">
          {filtered.map((supply) => (
            <div
              key={supply.id}
              className="rounded-xl border border-slate-800 bg-slate-900/60 p-4"
            >
              <div className="flex items-center justify-between">
                <div>
                  <span className="font-medium text-slate-100">
                    #{supply.id} {supply.marketplace.toUpperCase()}
                  </span>
                  <span className="ml-2 rounded bg-slate-700 px-2 py-0.5 text-xs text-slate-300">
                    {supply.status}
                  </span>
                </div>
                <div className="text-xs text-slate-400">
                  {new Date(supply.created_at).toLocaleDateString()}
                </div>
              </div>
              {supply.warehouse_name ? (
                <div className="mt-1 text-sm text-slate-400">{supply.warehouse_name}</div>
              ) : null}
              {supply.external_supply_id ? (
                <div className="mt-1 text-xs text-slate-500">ID поставки: {supply.external_supply_id}</div>
              ) : null}
              {supply.boxes?.length ? (
                <div className="mt-2 space-y-1">
                  {supply.boxes.map((box) => (
                    <div key={box.id} className="flex items-center gap-2 text-xs text-slate-400">
                      <span>Короб {box.box_number}</span>
                      {box.external_box_id ? (
                        <span className="text-slate-500">· ID: {box.external_box_id}</span>
                      ) : null}
                      {box.items?.length ? (
                        <span>· {box.items.length} поз.</span>
                      ) : null}
                    </div>
                  ))}
                </div>
              ) : null}
              <div className="mt-3 flex flex-wrap gap-2">
                {supply.status === "draft" ? (
                  <Button variant="secondary" onClick={() => handleSync(supply)} disabled={sync.isPending}>
                    Синхронизировать
                  </Button>
                ) : null}
                <Button variant="ghost" onClick={() => handleDownloadLabels(supply.id)}>
                  Скачать этикетки
                </Button>
                <Button variant="ghost" onClick={() => setImportSupplyId(supply.id)}>
                  Импорт ШК
                </Button>
                {supply.status === "draft" ? (
                  <Button variant="ghost" onClick={() => handleDelete(supply)} disabled={remove.isPending}>
                    Удалить
                  </Button>
                ) : null}
              </div>
            </div>
          ))}
        </div>
      )}

      <Modal title="Новая FBO-поставка" open={openCreate} onClose={() => setOpenCreate(false)}>
        {activeCompanyId != null ? (
          <FBOCreateForm
            companyId={activeCompanyId}
            products={products}
            onSubmit={handleCreate}
            isSubmitting={create.isPending}
          />
        ) : null}
      </Modal>

      <Modal
        title="Импорт штрихкодов коробов"
        open={importSupplyId != null}
        onClose={() => { setImportSupplyId(null); setImportText(""); }}
      >
        <div className="space-y-3">
          <p className="text-sm text-slate-400">
            Введите строки: номер_короба штрихкод (каждая с новой строки)
          </p>
          <textarea
            className="w-full rounded-lg border border-slate-700 bg-slate-900 p-2 text-sm text-slate-200"
            rows={5}
            value={importText}
            onChange={(e) => setImportText(e.target.value)}
            placeholder="1 1234567890&#10;2 0987654321"
          />
          <Button onClick={handleImportBarcodes} disabled={importBarcodes.isPending}>
            Импортировать
          </Button>
        </div>
      </Modal>
    </div>
  );
}

type BoxRow = { box_number: number; items: { product_id: number; quantity: number }[] };

function FBOCreateForm({
  companyId,
  products,
  onSubmit,
  isSubmitting,
}: {
  companyId: number;
  products: { id: number; name: string }[];
  onSubmit: (p: {
    company_id: number;
    marketplace: "wb" | "ozon";
    warehouse_name?: string;
    boxes: { box_number: number; items: { product_id: number; quantity: number }[] }[];
  }) => void;
  isSubmitting: boolean;
}) {
  const [marketplace, setMarketplace] = useState<"wb" | "ozon">("wb");
  const [warehouseName, setWarehouseName] = useState("");
  const [boxes, setBoxes] = useState<BoxRow[]>([
    { box_number: 1, items: [{ product_id: products[0]?.id ?? 0, quantity: 1 }] },
  ]);

  const addBox = () => {
    const nextNum = boxes.length ? Math.max(...boxes.map((b) => b.box_number), 0) + 1 : 1;
    setBoxes((prev) => [...prev, { box_number: nextNum, items: [{ product_id: products[0]?.id ?? 0, quantity: 1 }] }]);
  };

  const removeBox = (index: number) => {
    if (boxes.length <= 1) return;
    setBoxes((prev) => prev.filter((_, i) => i !== index));
  };

  const setBox = (index: number, upd: Partial<BoxRow> | ((prev: BoxRow) => BoxRow)) => {
    setBoxes((prev) => {
      const next = [...prev];
      next[index] = typeof upd === "function" ? upd(next[index]) : { ...next[index], ...upd };
      return next;
    });
  };

  const addItem = (boxIndex: number) => {
    setBoxes((prev) => {
      const next = [...prev];
      const box = next[boxIndex];
      box.items = [...box.items, { product_id: products[0]?.id ?? 0, quantity: 1 }];
      return next;
    });
  };

  const removeItem = (boxIndex: number, itemIndex: number) => {
    setBoxes((prev) => {
      const next = [...prev];
      const box = next[boxIndex];
      if (box.items.length <= 1) return prev;
      box.items = box.items.filter((_, i) => i !== itemIndex);
      return next;
    });
  };

  const setItem = (boxIndex: number, itemIndex: number, field: "product_id" | "quantity", value: number) => {
    setBoxes((prev) => {
      const next = [...prev];
      const item = { ...next[boxIndex].items[itemIndex], [field]: value };
      next[boxIndex].items = next[boxIndex].items.map((it, i) => (i === itemIndex ? item : it));
      return next;
    });
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const valid = boxes.every((b) => b.items.length >= 1 && b.items.every((i) => i.quantity >= 1));
    if (!valid) return;
    onSubmit({
      company_id: companyId,
      marketplace,
      warehouse_name: warehouseName.trim() || undefined,
      boxes: boxes.map((b) => ({
        box_number: b.box_number,
        items: b.items.map((i) => ({ product_id: i.product_id, quantity: Math.max(1, i.quantity) })),
      })),
    });
  };

  return (
    <form className="space-y-4" onSubmit={handleSubmit}>
      <Select
        value={marketplace}
        onChange={(e) => setMarketplace(e.target.value as "wb" | "ozon")}
        className="w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-slate-200"
      >
        <option value="wb">Wildberries</option>
        <option value="ozon">Ozon</option>
      </Select>
      <Input
        label="Склад (необязательно)"
        value={warehouseName}
        onChange={(e) => setWarehouseName(e.target.value)}
      />

      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <span className="text-sm font-medium text-slate-300">Короба и позиции</span>
          <Button type="button" variant="ghost" onClick={addBox}>
            + Короб
          </Button>
        </div>
        {boxes.map((box, boxIdx) => (
          <div key={boxIdx} className="rounded-lg border border-slate-700 bg-slate-800/50 p-3">
            <div className="mb-2 flex items-center justify-between">
              <Input
                label="Номер короба"
                type="number"
                value={String(box.box_number)}
                onChange={(e) => setBox(boxIdx, { box_number: parseInt(e.target.value, 10) || 1 })}
              />
              {boxes.length > 1 ? (
                <Button type="button" variant="ghost" onClick={() => removeBox(boxIdx)}>
                  Удалить короб
                </Button>
              ) : null}
            </div>
            {box.items.map((item, itemIdx) => (
              <div key={itemIdx} className="mb-2 flex flex-wrap items-end gap-2">
                <div className="min-w-[140px] flex-1">
                  <label className="mb-1 block text-xs text-slate-400">Товар</label>
                  <Select
                    value={String(item.product_id)}
                    onChange={(e) => setItem(boxIdx, itemIdx, "product_id", parseInt(e.target.value, 10))}
                    className="w-full rounded-lg border border-slate-700 bg-slate-900 px-2 py-1.5 text-sm text-slate-200"
                  >
                    {products.map((p) => (
                      <option key={p.id} value={p.id}>
                        {p.name}
                      </option>
                    ))}
                  </Select>
                </div>
                <div className="w-20">
                  <label className="mb-1 block text-xs text-slate-400">Кол-во</label>
                  <input
                    type="number"
                    min={1}
                    value={item.quantity}
                    onChange={(e) => setItem(boxIdx, itemIdx, "quantity", Math.max(1, parseInt(e.target.value, 10) || 1))}
                    className="w-full rounded border border-slate-700 bg-slate-900 px-2 py-1.5 text-sm text-slate-200"
                  />
                </div>
                {box.items.length > 1 ? (
                  <Button type="button" variant="ghost" onClick={() => removeItem(boxIdx, itemIdx)}>
                    ×
                  </Button>
                ) : null}
              </div>
            ))}
            <Button type="button" variant="ghost" onClick={() => addItem(boxIdx)}>
              + Позиция
            </Button>
          </div>
        ))}
      </div>

      <Button type="submit" disabled={isSubmitting}>
        Создать
      </Button>
    </form>
  );
}
