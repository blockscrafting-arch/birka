import { useEffect, useRef, useState } from "react";
import {
  DndContext,
  DragEndEvent,
  PointerSensor,
  useSensor,
  useSensors,
} from "@dnd-kit/core";
import { SortableContext, arrayMove, useSortable, verticalListSortingStrategy } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";

import { Button } from "../../components/ui/Button";
import { Input } from "../../components/ui/Input";
import { Modal } from "../../components/ui/Modal";
import { Toast } from "../../components/ui/Toast";
import {
  useServices,
  useCreateService,
  useUpdateService,
  useImportServices,
  useExportServices,
  useReorderServices,
} from "../../hooks/useServices";
import { Service } from "../../types";

function groupByCategory(items: Service[]): Record<string, Service[]> {
  const map: Record<string, Service[]> = {};
  for (const s of items) {
    if (!map[s.category]) map[s.category] = [];
    map[s.category].push(s);
  }
  return map;
}

function SortableServiceRow({
  service: s,
  onEdit,
  onToggleActive,
  onPriceStartEdit,
  onPriceChange,
  onPriceSave,
  onPriceCancel,
  isEditingPrice,
  editingPriceValue,
  isActive,
  isUpdating,
}: {
  service: Service;
  onEdit: () => void;
  onToggleActive: () => void;
  onPriceStartEdit: () => void;
  onPriceChange: (value: string) => void;
  onPriceSave: () => void;
  onPriceCancel: () => void;
  isEditingPrice: boolean;
  editingPriceValue: string;
  isActive: boolean;
  isUpdating: boolean;
}) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({
    id: s.id,
  });
  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
  };
  return (
    <tr
      ref={setNodeRef}
      style={style}
      className={`border-b border-slate-100 ${isDragging ? "z-10 bg-white shadow-md" : ""}`}
    >
      <td className="cursor-grab py-2 pr-2" {...attributes} {...listeners} title="Перетащите для изменения порядка">
        <span className="text-slate-400">⋮⋮</span>
      </td>
      <td className="py-2 pr-2">
        <span className="text-slate-800">{s.name}</span>
        {s.comment ? <div className="text-xs text-slate-500">{s.comment}</div> : null}
      </td>
      <td
        className="py-2 pr-2 text-slate-700"
        onClick={!isEditingPrice ? onPriceStartEdit : undefined}
      >
        {isEditingPrice ? (
          <input
            type="text"
            inputMode="decimal"
            className="w-20 rounded border border-slate-200 px-2 py-0.5 text-sm text-slate-800"
            value={editingPriceValue}
            onChange={(e) => onPriceChange(e.target.value)}
            onBlur={onPriceSave}
            onKeyDown={(e) => {
              if (e.key === "Enter") onPriceSave();
              if (e.key === "Escape") onPriceCancel();
            }}
            autoFocus
            onClick={(e) => e.stopPropagation()}
          />
        ) : (
          <span className="cursor-pointer hover:bg-slate-100 rounded px-1">
            {Number(s.price).toLocaleString("ru-RU")} ₽
          </span>
        )}
      </td>
      <td className="py-2 pr-2 text-slate-600">{s.unit}</td>
      <td className="py-2 pr-2">
        <span className={s.is_active ? "text-emerald-600" : "text-slate-400"}>
          {s.is_active ? "Активна" : "Отключена"}
        </span>
      </td>
      <td className="py-2 pr-2">
        <div className="flex gap-1">
          <Button variant="secondary" className="!py-1 !text-xs" onClick={onEdit}>
            Изменить
          </Button>
          <Button
            variant="secondary"
            className="!py-1 !text-xs"
            onClick={onToggleActive}
            disabled={isUpdating}
          >
            {s.is_active ? "Отключить" : "Включить"}
          </Button>
        </div>
      </td>
    </tr>
  );
}

export function ServicesPage() {
  const [searchQuery, setSearchQuery] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");
  const [toast, setToast] = useState<{ message: string; variant?: "success" | "error" } | null>(null);
  useEffect(() => {
    const timer = setTimeout(() => setDebouncedSearch(searchQuery), 300);
    return () => clearTimeout(timer);
  }, [searchQuery]);

  const { items: services = [], isLoading, error } = useServices({
    includeInactive: true,
    search: debouncedSearch,
  });
  const create = useCreateService();
  const update = useUpdateService();
  const reorder = useReorderServices();
  const importMut = useImportServices();
  const exportMut = useExportServices();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 8 } })
  );

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;
    if (!over || active.id === over.id) return;
    const activeId = active.id as number;
    const overId = over.id as number;
    const category = services.find((s) => s.id === activeId)?.category;
    if (!category) return;
    const grouped = groupByCategory(services);
    const items = grouped[category] ?? [];
    const oldIndex = items.findIndex((s) => s.id === activeId);
    const newIndex = items.findIndex((s) => s.id === overId);
    if (oldIndex === -1 || newIndex === -1) return;
    const reordered = arrayMove(items, oldIndex, newIndex);
    const payload = reordered.map((s, i) => ({ id: s.id, sort_order: i }));
    reorder.mutate(payload);
  };

  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState<Service | null>(null);
  const [category, setCategory] = useState("");
  const [name, setName] = useState("");
  const [price, setPrice] = useState("");
  const [unit, setUnit] = useState("шт");
  const [comment, setComment] = useState("");
  const [formError, setFormError] = useState<string | null>(null);
  const [editingPriceId, setEditingPriceId] = useState<number | null>(null);
  const [editingPriceValue, setEditingPriceValue] = useState("");

  useEffect(() => {
    if (!editing) return;
    setCategory(editing.category);
    setName(editing.name);
    setPrice(String(editing.price));
    setUnit(editing.unit);
    setComment(editing.comment ?? "");
  }, [editing]);

  const resetForm = () => {
    setEditing(null);
    setCategory("");
    setName("");
    setPrice("");
    setUnit("шт");
    setComment("");
    setFormError(null);
    setEditingPriceId(null);
    setModalOpen(false);
  };

  const handleSave = async () => {
    setFormError(null);
    const cat = category.trim();
    const n = name.trim();
    const p = parseFloat(price.replace(",", "."));
    if (!cat) {
      setFormError("Укажите категорию");
      return;
    }
    if (!n) {
      setFormError("Укажите название услуги");
      return;
    }
    if (Number.isNaN(p) || p < 0) {
      setFormError("Укажите корректную цену (число >= 0)");
      return;
    }
    if (editing) {
      await update.mutateAsync({
        id: editing.id,
        category: cat,
        name: n,
        price: p,
        unit: unit.trim() || "шт",
        comment: comment.trim() || null,
      });
    } else {
      await create.mutateAsync({
        category: cat,
        name: n,
        price: p,
        unit: unit.trim() || "шт",
        comment: comment.trim() || null,
      });
    }
    resetForm();
  };

  const handleImport = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    importMut.mutate(file);
    e.target.value = "";
  };

  const grouped = groupByCategory(services);
  const existingCategories = [...new Set(services.map((s) => s.category))].sort();

  return (
    <div className="space-y-4">
      {toast ? <Toast message={toast.message} variant={toast.variant} onClose={() => setToast(null)} /> : null}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="text-lg font-semibold text-slate-900">Прайс услуг</div>
        <Input
          type="search"
          placeholder="Название, категория, комментарий"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="max-w-xs"
          aria-label="Поиск по прайсу"
          maxLength={200}
        />
      </div>

      <div className="flex flex-wrap gap-2">
        <Button onClick={() => setModalOpen(true)}>Добавить услугу</Button>
        <Button
          variant="secondary"
          onClick={() => fileInputRef.current?.click()}
          disabled={importMut.isPending}
        >
          Импорт Excel
        </Button>
        <input
          ref={fileInputRef}
          type="file"
          accept=".xlsx,.xls"
          className="hidden"
          onChange={handleImport}
        />
        <Button
          variant="secondary"
          onClick={() =>
            exportMut.mutate(undefined, {
              onSuccess: () => setToast({ message: "Файл отправлен в чат с ботом" }),
              onError: (err) => setToast({ message: err?.message ?? "Ошибка", variant: "error" }),
            })
          }
          disabled={exportMut.isPending}
        >
          Экспорт Excel
        </Button>
      </div>

      {importMut.isSuccess && (
        <div className="text-sm text-emerald-600">
          Создано: {importMut.data?.created ?? 0}, обновлено: {importMut.data?.updated ?? 0}
        </div>
      )}
      {importMut.isError && (
        <div className="text-sm text-rose-500">{importMut.error?.message ?? "Ошибка импорта"}</div>
      )}

      {isLoading ? <div className="text-sm text-slate-600">Загрузка...</div> : null}
      {error ? <div className="text-sm text-rose-500">Ошибка загрузки прайса</div> : null}
      {!isLoading && services.length === 0 && (
        <div className="text-sm text-slate-500">
          {debouncedSearch.trim()
            ? `По запросу «${debouncedSearch}» ничего не найдено.`
            : "Услуги не найдены. Добавьте услугу вручную или импортируйте из Excel."}
        </div>
      )}

      <DndContext sensors={sensors} onDragEnd={handleDragEnd}>
        <div className="space-y-6">
          {Object.entries(grouped).map(([cat, items]) => (
            <div key={cat} className="rounded-xl border border-slate-200 bg-white p-4 shadow-soft">
              <div className="mb-3 text-sm font-semibold text-slate-800">{cat}</div>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-slate-200 text-left text-slate-600">
                      <th className="w-8 py-2 pr-2" aria-label="Порядок" />
                      <th className="py-2 pr-2">Название</th>
                      <th className="py-2 pr-2">Цена</th>
                      <th className="py-2 pr-2">Ед.</th>
                      <th className="py-2 pr-2">Статус</th>
                      <th className="py-2 pr-2" />
                    </tr>
                  </thead>
                  <SortableContext items={items.map((s) => s.id)} strategy={verticalListSortingStrategy}>
                    <tbody>
                      {items.map((s) => (
                        <SortableServiceRow
                          key={s.id}
                          service={s}
                          onEdit={() => {
                            setEditing(s);
                            setModalOpen(true);
                          }}
                          onToggleActive={() =>
                            update.mutate({ id: s.id, is_active: !s.is_active })
                          }
                          onPriceStartEdit={() => {
                            setEditingPriceId(s.id);
                            setEditingPriceValue(String(s.price));
                          }}
                          onPriceChange={setEditingPriceValue}
                          onPriceSave={() => {
                            if (editingPriceId !== s.id) return;
                            const v = parseFloat(editingPriceValue.replace(",", "."));
                            if (!Number.isNaN(v) && v >= 0) {
                              update.mutate({ id: s.id, price: v });
                            }
                            setEditingPriceId(null);
                          }}
                          onPriceCancel={() => setEditingPriceId(null)}
                          isEditingPrice={editingPriceId === s.id}
                          editingPriceValue={editingPriceId === s.id ? editingPriceValue : ""}
                          isActive={s.is_active}
                          isUpdating={update.isPending}
                        />
                      ))}
                    </tbody>
                  </SortableContext>
                </table>
              </div>
            </div>
          ))}
        </div>
      </DndContext>

      <Modal
        title={editing ? "Редактировать услугу" : "Новая услуга"}
        open={modalOpen}
        onClose={resetForm}
      >
        <div className="space-y-3">
          {formError && <div className="text-sm text-rose-500">{formError}</div>}
          <div>
            <label className="mb-1 block text-sm text-slate-700">Категория</label>
            <input
              type="text"
              list="category-suggestions"
              value={category}
              onChange={(e) => setCategory(e.target.value)}
              className="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-800 shadow-soft focus:border-birka-500 focus:outline-none focus:ring-2 focus:ring-birka-100"
            />
            <datalist id="category-suggestions">
              {existingCategories.map((cat) => (
                <option key={cat} value={cat} />
              ))}
            </datalist>
          </div>
          <Input label="Название" value={name} onChange={(e) => setName(e.target.value)} />
          <Input
            label="Цена (₽)"
            type="text"
            inputMode="decimal"
            value={price}
            onChange={(e) => setPrice(e.target.value)}
          />
          <Input label="Единица" value={unit} onChange={(e) => setUnit(e.target.value)} />
          <Input label="Комментарий" value={comment} onChange={(e) => setComment(e.target.value)} />
          <div className="flex gap-2 pt-2">
            <Button onClick={handleSave} disabled={create.isPending || update.isPending}>
              {editing ? "Сохранить" : "Добавить"}
            </Button>
            <Button variant="secondary" onClick={resetForm}>
              Отмена
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
