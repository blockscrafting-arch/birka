import { useEffect, useState } from "react";

import { CompanySelect } from "../../components/shared/CompanySelect";
import { Button } from "../../components/ui/Button";
import { Input } from "../../components/ui/Input";
import { Modal } from "../../components/ui/Modal";
import { Pagination } from "../../components/ui/Pagination";
import { Skeleton } from "../../components/ui/Skeleton";
import { Toast } from "../../components/ui/Toast";
import { useActiveCompany } from "../../hooks/useActiveCompany";
import { useCompanies } from "../../hooks/useCompanies";
import { useShipping } from "../../hooks/useShipping";
import { Select } from "../../components/ui/Select";

export function ShippingPage() {
  const { items: companies = [] } = useCompanies();
  const { companyId, setCompanyId } = useActiveCompany();
  const activeCompanyId = companyId ?? companies[0]?.id ?? null;
  const [page, setPage] = useState(1);
  const limit = 20;
  const { items, total, isLoading, error, create } = useShipping(activeCompanyId ?? undefined, page, limit);
  const [open, setOpen] = useState(false);
  const [pageError, setPageError] = useState<string | null>(null);
  const [toast, setToast] = useState<{ message: string; variant?: "success" | "error" } | null>(null);
  const [destinationType, setDestinationType] = useState("WB");
  const [comment, setComment] = useState("");

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
      <div className="rounded-lg border border-slate-200 bg-white p-4 text-sm text-slate-700 shadow-soft">
        Сначала добавьте компанию, чтобы создавать отгрузки.
      </div>
    );
  }

  const totalPages = Math.max(1, Math.ceil(total / limit));

  const handleCreate = async () => {
    if (!activeCompanyId) return;
    setPageError(null);
    try {
      await create.mutateAsync({
        company_id: activeCompanyId,
        destination_type: destinationType,
        destination_comment: comment.trim() || undefined,
      });
      setOpen(false);
      setComment("");
      setPage(1);
      setToast({ message: "Заявка на отгрузку создана" });
    } catch (err) {
      setPageError(err instanceof Error ? err.message : "Не удалось создать заявку на отгрузку");
    }
  };

  return (
    <div className="space-y-4">
      {toast ? <Toast message={toast.message} variant={toast.variant} onClose={() => setToast(null)} /> : null}
      <CompanySelect companies={companies} value={activeCompanyId} onChange={setCompanyId} />
      <div className="flex items-center justify-between gap-2">
        <Button onClick={() => setOpen(true)}>Создать отгрузку</Button>
        {pageError ? <div className="text-sm text-rose-500">{pageError}</div> : null}
      </div>

      {isLoading ? (
        <div className="space-y-2">
          <Skeleton className="h-16" />
          <Skeleton className="h-16" />
        </div>
      ) : null}
      {error ? <div className="text-sm text-rose-500">Не удалось загрузить отгрузки</div> : null}
      {!isLoading && items.length === 0 ? (
        <div className="rounded-lg border border-slate-200 bg-white p-4 text-sm text-slate-700 shadow-soft">
          Пока нет заявок на отгрузку.
        </div>
      ) : null}

      <div className="space-y-3">
        {items.map((shipment) => (
          <div
            key={shipment.id}
            className="rounded-xl border border-slate-200 bg-white p-4 shadow-soft"
          >
            <div className="text-sm font-semibold text-slate-900">Отгрузка: {shipment.destination_type}</div>
            <div className="text-xs text-slate-500">Статус: {shipment.status}</div>
            {shipment.destination_comment ? (
              <div className="mt-1 text-xs text-slate-500">Комментарий: {shipment.destination_comment}</div>
            ) : null}
          </div>
        ))}
      </div>
      <Pagination page={page} totalPages={totalPages} onPageChange={setPage} />

      <Modal title="Новая отгрузка" open={open} onClose={() => setOpen(false)}>
        <div className="space-y-3">
          <Select label="Отгрузка на" value={destinationType} onChange={(e) => setDestinationType(e.target.value)}>
            <option value="WB">WB</option>
            <option value="OZON">OZON</option>
            <option value="Другое">Другое</option>
          </Select>
          {destinationType === "Другое" ? (
            <Input
              label="Куда отгружаем"
              value={comment}
              onChange={(e) => setComment(e.target.value)}
            />
          ) : (
            <Input
              label="Комментарий"
              value={comment}
              onChange={(e) => setComment(e.target.value)}
            />
          )}
          <Button onClick={handleCreate} disabled={create.isPending}>
            {create.isPending ? "Создаю..." : "Создать"}
          </Button>
        </div>
      </Modal>
    </div>
  );
}
