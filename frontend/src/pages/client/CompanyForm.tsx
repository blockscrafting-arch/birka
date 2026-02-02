import { useCallback, useEffect, useState } from "react";

import { apiClient } from "../../services/api";
import { Button } from "../../components/ui/Button";
import { Input } from "../../components/ui/Input";

type CompanyFormPayload = {
  inn: string;
  name?: string;
  bank_bik?: string;
  bank_account?: string;
  bank_name?: string;
  bank_corr_account?: string;
};

type CompanyFormProps = {
  initial?: {
    inn?: string;
    name?: string;
    bank_bik?: string;
    bank_account?: string;
    kpp?: string;
    ogrn?: string;
    legal_address?: string;
    okved?: string;
    okved_name?: string;
    bank_name?: string;
    bank_corr_account?: string;
  };
  isSubmitting?: boolean;
  submitLabel?: string;
  onSubmit: (payload: CompanyFormPayload) => void;
};

export function CompanyForm({ initial, isSubmitting, submitLabel, onSubmit }: CompanyFormProps) {
  const [inn, setInn] = useState("");
  const [name, setName] = useState("");
  const [bik, setBik] = useState("");
  const [account, setAccount] = useState("");
  const [bankName, setBankName] = useState("");
  const [bankCorrAccount, setBankCorrAccount] = useState("");
  const [showBankDetails, setShowBankDetails] = useState(false);
  const [errors, setErrors] = useState<{
    inn?: string;
    bank_bik?: string;
    bank_account?: string;
  }>({});

  useEffect(() => {
    setInn(initial?.inn ?? "");
    setName(initial?.name ?? "");
    setBik(initial?.bank_bik ?? "");
    setAccount(initial?.bank_account ?? "");
    setBankName(initial?.bank_name ?? "");
    setBankCorrAccount(initial?.bank_corr_account ?? "");
    setShowBankDetails(
      Boolean(
        initial?.bank_bik ||
          initial?.bank_account ||
          initial?.bank_name ||
          initial?.bank_corr_account
      )
    );
    setErrors({});
  }, [initial]);

  const fetchBankByBik = useCallback(async (bikValue: string) => {
    if (bikValue.length !== 9 || !/^\d{9}$/.test(bikValue)) return;
    try {
      const data = await apiClient.api<{ bank_name: string | null; bank_corr_account: string | null }>(
        `/companies/bank-by-bik?bik=${encodeURIComponent(bikValue)}`
      );
      if (data.bank_name != null) setBankName(data.bank_name);
      if (data.bank_corr_account != null) setBankCorrAccount(data.bank_corr_account);
    } catch {
      setBankName("");
      setBankCorrAccount("");
    }
  }, []);

  useEffect(() => {
    const trimmed = bik.trim();
    if (trimmed.length === 9 && /^\d{9}$/.test(trimmed)) {
      const t = setTimeout(() => fetchBankByBik(trimmed), 400);
      return () => clearTimeout(t);
    }
  }, [bik, fetchBankByBik]);

  const hasReadOnlyRequisites =
    initial?.kpp ||
    initial?.ogrn ||
    initial?.legal_address ||
    initial?.okved ||
    initial?.okved_name;

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
          bank_name: bankName.trim() || undefined,
          bank_corr_account: bankCorrAccount.trim() || undefined,
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

      {hasReadOnlyRequisites && (
        <div className="rounded-lg border border-slate-200 bg-slate-50 p-3 text-sm text-slate-700">
          <div className="font-medium text-slate-800">Реквизиты из ЕГРЮЛ</div>
          <dl className="mt-2 space-y-1">
            {initial?.kpp && (
              <div>
                <span className="text-slate-500">КПП:</span> {initial.kpp}
              </div>
            )}
            {initial?.ogrn && (
              <div>
                <span className="text-slate-500">ОГРН:</span> {initial.ogrn}
              </div>
            )}
            {initial?.legal_address && (
              <div>
                <span className="text-slate-500">Юр. адрес:</span> {initial.legal_address}
              </div>
            )}
            {(initial?.okved || initial?.okved_name) && (
              <div>
                <span className="text-slate-500">ОКВЭД:</span> {[initial.okved, initial.okved_name].filter(Boolean).join(" — ")}
              </div>
            )}
          </dl>
        </div>
      )}

      <Button
        type="button"
        variant="ghost"
        className="w-full justify-center border border-dashed border-slate-700"
        onClick={() => setShowBankDetails((current) => !current)}
      >
        {showBankDetails ? "Скрыть банковские реквизиты" : "Добавить банковские реквизиты"}
      </Button>
      {showBankDetails && (
        <>
          <Input
            label="БИК"
            value={bik}
            error={errors.bank_bik}
            inputMode="numeric"
            placeholder="9 цифр"
            onChange={(event) => setBik(event.target.value)}
          />
          {bankName && (
            <div className="text-sm text-slate-600">
              <span className="text-slate-500">Банк:</span> {bankName}
            </div>
          )}
          {bankCorrAccount && (
            <div className="text-sm text-slate-600">
              <span className="text-slate-500">Корр. счёт:</span> {bankCorrAccount}
            </div>
          )}
          <Input
            label="Расчётный счёт"
            value={account}
            error={errors.bank_account}
            inputMode="numeric"
            placeholder="20 цифр"
            onChange={(event) => setAccount(event.target.value)}
          />
        </>
      )}
      <Button type="submit" disabled={isSubmitting}>
        {submitLabel ?? "Сохранить"}
      </Button>
    </form>
  );
}
