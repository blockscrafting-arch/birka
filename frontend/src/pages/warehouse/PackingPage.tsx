import { useState } from "react";

import { Button } from "../../components/ui/Button";
import { Modal } from "../../components/ui/Modal";
import { PackingForm } from "./PackingForm";

const demoOrders = [{ id: 1, title: "Заявка 24/01/26 №1" }];

export function PackingPage() {
  const [open, setOpen] = useState(false);

  return (
    <div className="space-y-3">
      {demoOrders.map((order) => (
        <div key={order.id} className="rounded bg-white p-4 shadow-sm">
          <div className="text-sm font-semibold">{order.title}</div>
          <Button className="mt-2" onClick={() => setOpen(true)}>
            Взять в работу
          </Button>
        </div>
      ))}

      <Modal title="Упаковка" open={open} onClose={() => setOpen(false)}>
        <PackingForm onSubmit={() => setOpen(false)} />
      </Modal>
    </div>
  );
}
