import { useEffect, useRef, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";

import { OrderCard } from "../../components/shared/OrderCard";
import { Button } from "../../components/ui/Button";
import { Modal } from "../../components/ui/Modal";
import { Select } from "../../components/ui/Select";
import { Pagination } from "../../components/ui/Pagination";
import { Skeleton } from "../../components/ui/Skeleton";
import { Toast } from "../../components/ui/Toast";
import { useCompanies } from "../../hooks/useCompanies";
import { useDestinations } from "../../hooks/useDestinations";
import { useOrders } from "../../hooks/useOrders";
import { useProducts } from "../../hooks/useProducts";
import { apiClient } from "../../services/api";
import { OrderForm } from "./OrderForm";

export function OrdersPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const { items: companies = [] } = useCompanies();
  const activeCompanyId = companies[0]?.id ?? null;
  const [page, setPage] = useState(1);
  const [statusFilter, setStatusFilter] = useState<string | undefined>(undefined);
  const limit = 20;
  const { items, total, isLoading, error, create, importExcel } = useOrders(activeCompanyId ?? undefined, page, limit, statusFilter);
  const importRef = useRef<HTMLInputElement | null>(null);
  const { items: products = [] } = useProducts(activeCompanyId ?? undefined, 1, 100);
  const { items: destinations = [] } = useDestinations(true);
  const [open, setOpen] = useState(false);
  const [initialServicesFromCalculator, setInitialServicesFromCalculator] = useState<
    { service_id: number; quantity: number }[] | null
  >(null);
  const [pageError, setPageError] = useState<string | null>(null);
  const [toast, setToast] = useState<{ message: string; variant?: "success" | "error" } | null>(null);
  const [templateSending, setTemplateSending] = useState(false);

  useEffect(() => {
    const stateServices = (location.state as { services?: { service_id: number; quantity: number }[] } | null)?.services;
    if (stateServices?.length) {
      setInitialServicesFromCalculator(stateServices);
      setOpen(true);
      navigate(location.pathname, { replace: true, state: {} });
    }
  }, [location.state, location.pathname, navigate]);

  useEffect(() => {
    setPage(1);
  }, [activeCompanyId]);

  if (companies.length === 0) {
    return (
      <div className="rounded-lg border border-slate-200 bg-white p-4 text-sm text-slate-700 shadow-soft">
        Сначала добавьте компанию, чтобы создавать заявки.
      </div>
    );
  }

  const totalPages = Math.max(1, Math.ceil(total / limit));
  const orders = items;

  const handleCreate = async (payload: { destination?: string; items: { product_id: number; planned_qty: number }[] }) => {
    if (!activeCompanyId) return;
    setPageError(null);
    try {
      await create.mutateAsync({ company_id: activeCompanyId, ...payload });
      setOpen(false);
      setPage(1);
      setToast({ message: "Заявка создана" });
    } catch (err) {
      setPageError(err instanceof Error ? err.message : "Не удалось создать заявку");
    }
  };

  const handleImport = async (file: File) => {
    if (!activeCompanyId) return;
    setPageError(null);
    try {
      await importExcel.mutateAsync({ companyId: activeCompanyId, file });
      setPage(1);
      setToast({ message: "Заявка создана из файла" });
    } catch (err) {
      setPageError(err instanceof Error ? err.message : "Ошибка импорта");
    }
  };

  const handleExportSend = async (orderId: number) => {
    setPageError(null);
    try {
      await apiClient.api(`/orders/${orderId}/export/send`, { method: "POST" });
      setToast({ message: "Файл отправлен в чат с ботом" });
    } catch (err) {
      setToast({ message: err instanceof Error ? err.message : "Ошибка выгрузки", variant: "error" });
    }
  };

  return (
    <div className="flex min-h-0 flex-1 flex-col gap-4">
      {toast ? <Toast message={toast.message} variant={toast.variant} onClose={() => setToast(null)} /> : null}
      <div className="flex shrink-0 flex-col gap-2">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="flex flex-wrap items-center gap-2">
            <Select
              value={statusFilter ?? ""}
              onChange={(e) => {
                setStatusFilter(e.target.value || undefined);
                setPage(1);
              }}
              className="min-w-0 max-w-[140px]"
            >
              <option value="">Все статусы</option>
              <option value="На приемке">На приемке</option>
              <option value="Принято">Принято</option>
              <option value="Упаковка">Упаковка</option>
              <option value="Готово к отгрузке">Готово к отгрузке</option>
              <option value="Завершено">Завершено</option>
            </Select>
            <Button onClick={() => setOpen(true)}>Создать заявку</Button>
          </div>
          {pageError ? <div className="text-sm text-rose-500 shrink-0">{pageError}</div> : null}
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <Button
            variant="secondary"
            className="py-1.5 text-xs"
            onClick={() => importRef.current?.click()}
            disabled={importExcel.isPending}
          >
            {importExcel.isPending ? "Импортирую..." : "Импорт Excel"}
          </Button>
          <Button
            variant="secondary"
            className="py-1.5 text-xs"
            onClick={async () => {
              setPageError(null);
              try {
                const { blob } = await apiClient.apiFile("/orders/import/template");
                const url = URL.createObjectURL(blob);
                const a = document.createElement("a");
                a.href = url;
                a.download = "Шаблон_заявки.xlsx";
                a.click();
                URL.revokeObjectURL(url);
                setToast({ message: "Шаблон загружен" });
              } catch (err) {
                setToast({ message: err instanceof Error ? err.message : "Ошибка загрузки", variant: "error" });
              }
            }}
          >
            Скачать шаблон
          </Button>
          <Button
            variant="ghost"
            className="py-1.5 text-xs"
            disabled={templateSending}
            onClick={async () => {
              setTemplateSending(true);
              try {
                await apiClient.api("/orders/import/template/send", { method: "POST" });
                setToast({ message: "Шаблон отправлен в Telegram" });
              } catch (err) {
                setToast({
                  message: err instanceof Error ? err.message : "Не удалось отправить шаблон",
                  variant: "error",
                });
              } finally {
                setTemplateSending(false);
              }
            }}
          >
            {templateSending ? "Отправляю..." : "Шаблон в Telegram"}
          </Button>
        </div>
      </div>
      <input
        ref={importRef}
        type="file"
        accept=".xlsx,.xls"
        className="hidden"
        onChange={(e) => {
          const file = e.target.files?.[0];
          if (file) {
            handleImport(file);
            e.target.value = "";
          }
        }}
      />

      {isLoading ? (
        <div className="space-y-2">
          <Skeleton className="h-16" />
          <Skeleton className="h-16" />
        </div>
      ) : null}
      {error ? <div className="text-sm text-rose-500">Не удалось загрузить заявки</div> : null}
      {!isLoading && orders.length === 0 ? (
        <div className="shrink-0 rounded-xl border border-slate-200 bg-white p-6 text-center shadow-soft">
          <p className="mb-4 text-sm text-slate-600">Пока нет заявок. Создайте первую заявку.</p>
          <Button onClick={() => setOpen(true)}>Создать заявку</Button>
        </div>
      ) : null}

      <div className="space-y-3 pb-24">
        {orders.map((order) => (
          <OrderCard
            key={order.id}
            title={order.order_number}
            status={order.status}
            photoCount={order.photo_count}
            onClick={() => navigate(`/client/orders/${order.id}`)}
            onExport={() => handleExportSend(order.id)}
          />
        ))}
      </div>
      <div className="shrink-0">
        <Pagination page={page} totalPages={totalPages} onPageChange={setPage} />
      </div>

      <Modal
        title="Новая заявка"
        open={open}
        onClose={() => {
          setOpen(false);
          setInitialServicesFromCalculator(null);
        }}
      >
        <OrderForm
          products={products}
          destinations={destinations}
          initialServices={initialServicesFromCalculator ?? undefined}
          isSubmitting={create.isPending}
          onSubmit={handleCreate}
        />
      </Modal>
    </div>
  );
}
