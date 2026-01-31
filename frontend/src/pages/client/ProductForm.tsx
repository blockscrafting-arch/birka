import { useState } from "react";

import { Button } from "../../components/ui/Button";
import { Input } from "../../components/ui/Input";
import { PhotoUpload } from "../../components/shared/PhotoUpload";

type ProductFormProps = {
  onSubmit: () => void;
};

export function ProductForm({ onSubmit }: ProductFormProps) {
  const [name, setName] = useState("");
  const [brand, setBrand] = useState("");
  const [size, setSize] = useState("");
  const [color, setColor] = useState("");
  const [barcode, setBarcode] = useState("");
  const [article, setArticle] = useState("");
  const [wbUrl, setWbUrl] = useState("");
  const [packing, setPacking] = useState("");

  return (
    <form
      className="space-y-3"
      onSubmit={(event) => {
        event.preventDefault();
        onSubmit();
      }}
    >
      <Input label="Название" value={name} onChange={(event) => setName(event.target.value)} />
      <Input label="Бренд" value={brand} onChange={(event) => setBrand(event.target.value)} />
      <Input label="Размер" value={size} onChange={(event) => setSize(event.target.value)} />
      <Input label="Цвет" value={color} onChange={(event) => setColor(event.target.value)} />
      <Input label="Баркод" value={barcode} onChange={(event) => setBarcode(event.target.value)} />
      <Input label="Артикул WB" value={article} onChange={(event) => setArticle(event.target.value)} />
      <Input label="Ссылка WB" value={wbUrl} onChange={(event) => setWbUrl(event.target.value)} />
      <Input
        label="ТЗ на упаковку"
        value={packing}
        onChange={(event) => setPacking(event.target.value)}
      />
      <PhotoUpload onFileChange={() => undefined} />
      <Button type="submit">Сохранить</Button>
    </form>
  );
}
