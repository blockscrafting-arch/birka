import { useState } from "react";

import { Button } from "../ui/Button";

type PhotoUploadProps = {
  label?: string;
  onFileChange: (file: File) => void;
};

export function PhotoUpload({ label = "Добавить фото", onFileChange }: PhotoUploadProps) {
  const [preview, setPreview] = useState<string | null>(null);

  return (
    <div className="space-y-2">
      <label className="block text-sm text-slate-700">{label}</label>
      <input
        type="file"
        accept="image/*"
        aria-label={label}
        onChange={(event) => {
          const file = event.target.files?.[0];
          if (!file) return;
          const reader = new FileReader();
          reader.onload = () => setPreview(reader.result as string);
          reader.readAsDataURL(file);
          onFileChange(file);
        }}
      />
      {preview ? <img src={preview} alt="preview" className="h-32 rounded object-cover" /> : null}
      <Button type="button" variant="secondary">
        Загрузить
      </Button>
    </div>
  );
}
