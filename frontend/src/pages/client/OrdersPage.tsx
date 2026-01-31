import { useNavigate } from "react-router-dom";

import { Button } from "../../components/ui/Button";
import { OrderCard } from "../../components/shared/OrderCard";

const demoOrders = [
  { id: 1, title: "Заявка 24/01/26 №1", status: "Принято" as const },
  { id: 2, title: "Заявка 24/01/26 №2", status: "На приемке" as const },
];

export function OrdersPage() {
  const navigate = useNavigate();

  return (
    <div className="space-y-3">
      <Button>Создать заявку</Button>
      {demoOrders.map((order) => (
        <OrderCard
          key={order.id}
          title={order.title}
          status={order.status}
          onClick={() => navigate(`/client/orders/${order.id}`)}
        />
      ))}
    </div>
  );
}
