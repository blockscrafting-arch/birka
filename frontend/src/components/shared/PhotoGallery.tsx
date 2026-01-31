type PhotoGalleryProps = {
  photos: string[];
};

export function PhotoGallery({ photos }: PhotoGalleryProps) {
  if (photos.length === 0) {
    return <div className="text-sm text-slate-500">Фото нет</div>;
  }
  return (
    <div className="grid grid-cols-3 gap-2">
      {photos.map((url) => (
        <img key={url} src={url} alt="photo" className="h-24 w-full rounded object-cover" />
      ))}
    </div>
  );
}
