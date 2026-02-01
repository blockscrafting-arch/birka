type LoaderProps = {
  text?: string;
};

export function Loader({ text = "Загрузка..." }: LoaderProps) {
  return (
    <div className="flex items-center gap-2 text-sm text-slate-300">
      <span className="h-4 w-4 animate-spin rounded-full border-2 border-slate-600 border-t-sky-400" />
      <span>{text}</span>
    </div>
  );
}
