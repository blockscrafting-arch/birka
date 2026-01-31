import { useState } from "react";

import { Button } from "../../components/ui/Button";
import { Input } from "../../components/ui/Input";

type CompanyFormProps = {
  onSubmit: () => void;
};

export function CompanyForm({ onSubmit }: CompanyFormProps) {
  const [inn, setInn] = useState("");
  const [bik, setBik] = useState("");
  const [account, setAccount] = useState("");

  return (
    <form
      className="space-y-3"
      onSubmit={(event) => {
        event.preventDefault();
        onSubmit();
      }}
    >
      <Input label="ИНН" value={inn} onChange={(event) => setInn(event.target.value)} />
      <Input label="БИК" value={bik} onChange={(event) => setBik(event.target.value)} />
      <Input label="Расчётный счёт" value={account} onChange={(event) => setAccount(event.target.value)} />
      <Button type="submit">Сохранить</Button>
    </form>
  );
}
