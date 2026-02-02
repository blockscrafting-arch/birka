import { useEffect, useState } from "react";

import { Button } from "../../components/ui/Button";
import { Input } from "../../components/ui/Input";
import {
  useContractTemplates,
  useCreateContractTemplate,
  useDeleteContractTemplate,
  useUpdateContractTemplate,
} from "../../hooks/useAdmin";

export function ContractTemplatesPage() {
  const { items: templates = [], isLoading, error } = useContractTemplates();
  const create = useCreateContractTemplate();
  const update = useUpdateContractTemplate();
  const remove = useDeleteContractTemplate();
  const [editingId, setEditingId] = useState<number | null>(null);
  const [name, setName] = useState("");
  const [htmlContent, setHtmlContent] = useState("");
  const [isDefault, setIsDefault] = useState(false);

  useEffect(() => {
    if (!editingId) return;
    const template = templates.find((item) => item.id === editingId);
    if (!template) return;
    setName(template.name);
    setHtmlContent(template.html_content);
    setIsDefault(template.is_default);
  }, [editingId, templates]);

  const resetForm = () => {
    setEditingId(null);
    setName("");
    setHtmlContent("");
    setIsDefault(false);
  };

  const handleSubmit = async () => {
    if (!name.trim() || !htmlContent.trim()) return;
    if (editingId) {
      await update.mutateAsync({ id: editingId, name: name.trim(), html_content: htmlContent, is_default: isDefault });
    } else {
      await create.mutateAsync({ name: name.trim(), html_content: htmlContent, is_default: isDefault });
    }
    resetForm();
  };

  return (
    <div className="space-y-4">
      <div className="text-lg font-semibold text-slate-900">Шаблоны договоров</div>

      {isLoading ? <div className="text-sm text-slate-600">Загрузка шаблонов...</div> : null}
      {error ? <div className="text-sm text-rose-500">Ошибка загрузки шаблонов</div> : null}

      <div className="space-y-2">
        {templates.map((template) => (
          <div key={template.id} className="rounded-xl border border-slate-200 bg-white p-4 shadow-soft">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div>
                <div className="text-sm font-semibold text-slate-900">{template.name}</div>
                <div className="text-xs text-slate-500">
                  {template.is_default ? "Шаблон по умолчанию" : "Обычный шаблон"}
                </div>
              </div>
              <div className="flex gap-2">
                <Button variant="secondary" onClick={() => setEditingId(template.id)}>
                  Редактировать
                </Button>
                <Button
                  variant="secondary"
                  onClick={() => remove.mutate(template.id)}
                  disabled={remove.isPending}
                >
                  Удалить
                </Button>
              </div>
            </div>
          </div>
        ))}
      </div>

      <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-soft">
        <div className="text-sm font-semibold text-slate-900">
          {editingId ? "Редактирование шаблона" : "Новый шаблон"}
        </div>
        <div className="mt-3 space-y-3">
          <Input label="Название" value={name} onChange={(e) => setName(e.target.value)} />
          <label className="block text-sm">
            <span className="mb-1 block text-slate-700">HTML-шаблон</span>
            <textarea
              className="h-56 w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs text-slate-800 shadow-soft focus:border-birka-500 focus:outline-none focus:ring-2 focus:ring-birka-100"
              value={htmlContent}
              onChange={(e) => setHtmlContent(e.target.value)}
            />
          </label>
          <label className="flex items-center gap-2 text-sm text-slate-700">
            <input
              type="checkbox"
              checked={isDefault}
              onChange={(e) => setIsDefault(e.target.checked)}
            />
            Сделать шаблоном по умолчанию
          </label>
          <div className="flex gap-2">
            <Button onClick={handleSubmit} disabled={create.isPending || update.isPending}>
              {editingId ? "Сохранить" : "Создать"}
            </Button>
            {editingId ? (
              <Button variant="secondary" onClick={resetForm}>
                Отменить
              </Button>
            ) : null}
          </div>
        </div>
      </div>
    </div>
  );
}
