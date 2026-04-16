import { useRef, useState } from "react";

import { Button } from "../ui/Button";

type PhotoUploadProps = {
  label?: string;
  onFileChange: (file: File) => void;
};

export function PhotoUpload({ label = "Добавить фото", onFileChange }: PhotoUploadProps) {
  const [preview, setPreview] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement | null>(null);

  return (
    <div className="space-y-2">
      <label className="block text-sm text-slate-300">{label}</label>
      <input
        ref={inputRef}
        type="file"
        accept="image/*"
        capture="environment"
        className="hidden"
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
      <div className="flex items-center gap-3">
        <Button type="button" variant="secondary" onClick={() => inputRef.current?.click()}>
          Выбрать фото
        </Button>
        {preview ? <span className="text-xs text-emerald-300">Файл выбран</span> : null}
      </div>
      {preview ? <img src={preview} alt="preview" className="h-32 rounded-xl object-cover" /> : null}
    </div>
  );
}
