import { useState } from "react";

import { Button } from "../../components/ui/Button";
import { Modal } from "../../components/ui/Modal";
import { CompanyForm } from "./CompanyForm";

const demoCompanies = [
  { id: 1, name: "ИП Белогур Д.А.", inn: "1234567890" },
];

export function CompanyPage() {
  const [open, setOpen] = useState(false);

  return (
    <div className="space-y-3">
      <Button variant="primary" onClick={() => setOpen(true)}>
        Добавить компанию
      </Button>

      {demoCompanies.map((company) => (
        <div key={company.id} className="rounded bg-white p-4 shadow-sm">
          <div className="text-sm font-semibold">{company.name}</div>
          <div className="mt-1 text-xs text-slate-600">ИНН: {company.inn}</div>
          <div className="mt-3 flex gap-2">
            <Button variant="secondary">Редактировать</Button>
            <Button variant="ghost">Скачать договор</Button>
          </div>
        </div>
      ))}

      <Modal title="Новая компания" open={open} onClose={() => setOpen(false)}>
        <CompanyForm onSubmit={() => setOpen(false)} />
      </Modal>
    </div>
  );
}
