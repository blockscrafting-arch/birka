import { useEffect, useState } from "react";

import { Button } from "../../components/ui/Button";
import { Input } from "../../components/ui/Input";

type CompanyFormProps = {
  initial?: {
    inn?: string;
    name?: string;
    bank_bik?: string;
    bank_account?: string;
  };
  isSubmitting?: boolean;
  submitLabel?: string;
  onSubmit: (payload: { inn: string; name?: string; bank_bik?: string; bank_account?: string }) => void;
};

export function CompanyForm({ initial, isSubmitting, submitLabel, onSubmit }: CompanyFormProps) {
  const [inn, setInn] = useState("");
  const [name, setName] = useState("");
  const [bik, setBik] = useState("");
  const [account, setAccount] = useState("");
  const [errors, setErrors] = useState<{ inn?: string; name?: string; bank_bik?: string; bank_account?: string }>({});

  useEffect(() => {
    setInn(initial?.inn ?? "");
    setName(initial?.name ?? "");
    setBik(initial?.bank_bik ?? "");
    setAccount(initial?.bank_account ?? "");
    setErrors({});
  }, [initial]);

  return (
    <form
      className="space-y-3"
      onSubmit={(event) => {
        event.preventDefault();
        const trimmedInn = inn.trim();
        const trimmedName = name.trim();
        const trimmedBik = bik.trim();
        const trimmedAccount = account.trim();
        const nextErrors: typeof errors = {};

        if (!trimmedInn) {
          nextErrors.inn = "Введите ИНН";
        } else if (![10, 12].includes(trimmedInn.length)) {
          nextErrors.inn = "ИНН должен быть 10 или 12 цифр";
        }

        if (trimmedBik && trimmedBik.length !== 9) {
          nextErrors.bank_bik = "БИК должен быть 9 цифр";
        }

        if (trimmedAccount && trimmedAccount.length !== 20) {
          nextErrors.bank_account = "Расчётный счёт должен быть 20 цифр";
        }

        if (Object.keys(nextErrors).length) {
          setErrors(nextErrors);
          return;
        }

        onSubmit({
          inn: trimmedInn,
          name: trimmedName || undefined,
          bank_bik: trimmedBik || undefined,
          bank_account: trimmedAccount || undefined,
        });
      }}
    >
      <Input
        label="ИНН"
        value={inn}
        error={errors.inn}
        inputMode="numeric"
        placeholder="10 или 12 цифр"
        onChange={(event) => setInn(event.target.value)}
      />
      <Input label="Название компании" value={name} onChange={(event) => setName(event.target.value)} />
      <Input
        label="БИК"
        value={bik}
        error={errors.bank_bik}
        inputMode="numeric"
        placeholder="9 цифр"
        onChange={(event) => setBik(event.target.value)}
      />
      <Input
        label="Расчётный счёт"
        value={account}
        error={errors.bank_account}
        inputMode="numeric"
        placeholder="20 цифр"
        onChange={(event) => setAccount(event.target.value)}
      />
      <Button type="submit" disabled={isSubmitting}>
        {submitLabel ?? "Сохранить"}
      </Button>
    </form>
  );
}
