import { useState } from "react";

import { PhotoUpload } from "../../components/shared/PhotoUpload";
import { Button } from "../../components/ui/Button";
import { Input } from "../../components/ui/Input";
import { Select } from "../../components/ui/Select";

type PackingFormProps = {
  onSubmit: () => void;
};

export function PackingForm({ onSubmit }: PackingFormProps) {
  const [employeeId, setEmployeeId] = useState("");
  const [pallet, setPallet] = useState("");
  const [box, setBox] = useState("");
  const [quantity, setQuantity] = useState("10");
  const [warehouse, setWarehouse] = useState("");
  const [materials, setMaterials] = useState("");
  const [time, setTime] = useState("");

  return (
    <form
      className="space-y-3"
      onSubmit={(event) => {
        event.preventDefault();
        onSubmit();
      }}
    >
      <Input label="ID сотрудника" value={employeeId} onChange={(e) => setEmployeeId(e.target.value)} />
      <Select label="Товар">
        <option value="1">Шлем боксерский</option>
      </Select>
      <Input label="Номер паллеты" value={pallet} onChange={(e) => setPallet(e.target.value)} />
      <Input label="Номер короба" value={box} onChange={(e) => setBox(e.target.value)} />
      <Input label="Количество в коробе" value={quantity} onChange={(e) => setQuantity(e.target.value)} />
      <Input label="Склад назначения" value={warehouse} onChange={(e) => setWarehouse(e.target.value)} />
      <Input label="Использованные материалы" value={materials} onChange={(e) => setMaterials(e.target.value)} />
      <Input label="Время упаковки (мин)" value={time} onChange={(e) => setTime(e.target.value)} />
      <PhotoUpload onFileChange={() => undefined} />
      <Button type="submit">Завершить упаковку</Button>
    </form>
  );
}
