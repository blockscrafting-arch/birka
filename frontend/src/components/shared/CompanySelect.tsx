import { Company } from "../../types";
import { Select } from "../ui/Select";

type CompanySelectProps = {
  companies: Company[];
  value: number | null;
  onChange: (companyId: number) => void;
};

export function CompanySelect({ companies, value, onChange }: CompanySelectProps) {
  return (
    <Select
      label="Компания"
      value={value ?? ""}
      onChange={(event) => onChange(Number(event.target.value))}
    >
      <option value="" disabled>
        Выберите компанию
      </option>
      {companies.map((company) => (
        <option key={company.id} value={company.id}>
          {company.name}
        </option>
      ))}
    </Select>
  );
}
