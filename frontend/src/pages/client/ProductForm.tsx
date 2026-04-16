import { useEffect, useState } from "react";

import { Button } from "../../components/ui/Button";
import { Input } from "../../components/ui/Input";
import { PhotoUpload } from "../../components/shared/PhotoUpload";

type ProductFormProps = {
  initial?: {
    name?: string;
    brand?: string;
    size?: string;
    color?: string;
    barcode?: string;
    wb_article?: string;
    wb_url?: string;
    packing_instructions?: string;
    supplier_name?: string;
  };
  isSubmitting?: boolean;
  submitLabel?: string;
  onSubmit: (payload: {
    name: string;
    brand?: string;
    size?: string;
    color?: string;
    barcode?: string;
    wb_article?: string;
    wb_url?: string;
    packing_instructions?: string;
    supplier_name?: string;
    photo?: File | null;
  }) => void;
};

export function ProductForm({ initial, isSubmitting, submitLabel, onSubmit }: ProductFormProps) {
  const [name, setName] = useState("");
  const [brand, setBrand] = useState("");
  const [size, setSize] = useState("");
  const [color, setColor] = useState("");
  const [barcode, setBarcode] = useState("");
  const [article, setArticle] = useState("");
  const [wbUrl, setWbUrl] = useState("");
  const [packing, setPacking] = useState("");
  const [supplier, setSupplier] = useState("");
  const [photo, setPhoto] = useState<File | null>(null);
  const [errors, setErrors] = useState<{ name?: string }>({});

  useEffect(() => {
    setName(initial?.name ?? "");
    setBrand(initial?.brand ?? "");
    setSize(initial?.size ?? "");
    setColor(initial?.color ?? "");
    setBarcode(initial?.barcode ?? "");
    setArticle(initial?.wb_article ?? "");
    setWbUrl(initial?.wb_url ?? "");
    setPacking(initial?.packing_instructions ?? "");
    setSupplier(initial?.supplier_name ?? "");
    setPhoto(null);
    setErrors({});
  }, [initial]);

  return (
    <form
      className="space-y-3"
      onSubmit={(event) => {
        event.preventDefault();
        const trimmedName = name.trim();
        if (!trimmedName) {
          setErrors({ name: "Введите название товара" });
          return;
        }
        onSubmit({
          name: trimmedName,
          brand: brand.trim() || undefined,
          size: size.trim() || undefined,
          color: color.trim() || undefined,
          barcode: barcode.trim() || undefined,
          wb_article: article.trim() || undefined,
          wb_url: wbUrl.trim() || undefined,
          packing_instructions: packing.trim() || undefined,
          supplier_name: supplier.trim() || undefined,
          photo,
        });
      }}
    >
      <Input label="Название" value={name} error={errors.name} onChange={(event) => setName(event.target.value)} />
      <Input label="Бренд" value={brand} onChange={(event) => setBrand(event.target.value)} />
      <Input label="Размер" value={size} onChange={(event) => setSize(event.target.value)} />
      <Input label="Цвет" value={color} onChange={(event) => setColor(event.target.value)} />
      <Input label="Баркод" value={barcode} onChange={(event) => setBarcode(event.target.value)} />
      <Input label="Артикул WB" value={article} onChange={(event) => setArticle(event.target.value)} />
      <Input label="Ссылка WB" value={wbUrl} onChange={(event) => setWbUrl(event.target.value)} />
      <Input
        label="Поставщик (для этикетки)"
        value={supplier}
        onChange={(event) => setSupplier(event.target.value)}
      />
      <Input
        label="ТЗ на упаковку"
        value={packing}
        onChange={(event) => setPacking(event.target.value)}
      />
      <PhotoUpload onFileChange={(file) => setPhoto(file)} />
      <Button type="submit" disabled={isSubmitting}>
        {submitLabel ?? "Сохранить"}
      </Button>
    </form>
  );
}
