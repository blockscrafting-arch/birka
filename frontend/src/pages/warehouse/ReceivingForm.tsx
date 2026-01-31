import { useState } from "react";

import { PhotoUpload } from "../../components/shared/PhotoUpload";
import { Button } from "../../components/ui/Button";
import { Input } from "../../components/ui/Input";

type ReceivingFormProps = {
  onSubmit: () => void;
};

export function ReceivingForm({ onSubmit }: ReceivingFormProps) {
  const [received, setReceived] = useState("30");
  const [defect, setDefect] = useState("0");

  return (
    <form
      className="space-y-3"
      onSubmit={(event) => {
        event.preventDefault();
        onSubmit();
      }}
    >
      <div className="rounded bg-slate-50 p-3 text-sm">
        Товар: Шлем боксерский (ШК 2044283645181)
      </div>
      <Input label="Фактическое количество" value={received} onChange={(e) => setReceived(e.target.value)} />
      <Input label="Брак" value={defect} onChange={(e) => setDefect(e.target.value)} />
      <PhotoUpload onFileChange={() => undefined} />
      <Button type="submit">Завершить приёмку</Button>
    </form>
  );
}
