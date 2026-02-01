import { useEffect, useState } from "react";

const STORAGE_KEY = "birka_active_company_id";

export function useActiveCompany() {
  const [companyId, setCompanyId] = useState<number | null>(() => {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? Number(raw) : null;
  });

  useEffect(() => {
    if (companyId === null) {
      localStorage.removeItem(STORAGE_KEY);
      return;
    }
    localStorage.setItem(STORAGE_KEY, String(companyId));
  }, [companyId]);

  return { companyId, setCompanyId };
}
