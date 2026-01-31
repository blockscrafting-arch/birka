import { PhotoGallery } from "../../components/shared/PhotoGallery";
import { StatusBadge } from "../../components/ui/StatusBadge";

const demoItems = [
  { id: 1, name: "Шлем боксерский", planned: 30, received: 30, defect: 0 },
];

export function OrderDetail() {
  return (
    <div className="space-y-4">
      <div className="rounded bg-white p-4 shadow-sm">
        <div className="flex items-center justify-between">
          <div className="text-sm font-semibold">Заявка 24/01/26 №1</div>
          <StatusBadge status="Принято" />
        </div>
      </div>

      <div className="rounded bg-white p-4 shadow-sm">
        <div className="text-sm font-semibold">Товары</div>
        <div className="mt-2 space-y-2 text-sm text-slate-700">
          {demoItems.map((item) => (
            <div key={item.id} className="flex justify-between border-b pb-2">
              <span>{item.name}</span>
              <span>
                План: {item.planned} / Факт: {item.received} / Брак: {item.defect}
              </span>
            </div>
          ))}
        </div>
      </div>

      <div className="rounded bg-white p-4 shadow-sm">
        <div className="text-sm font-semibold">Фото</div>
        <div className="mt-2">
          <PhotoGallery photos={[]} />
        </div>
      </div>
    </div>
  );
}
