import { useEffect } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { useUploadStore } from "../../stores/uploadStore";

/**
 * Устанавливает в uploadStore колбэки инвалидации запросов после загрузки.
 * Должен быть смонтирован один раз (например в App).
 */
export function UploadManager() {
  const queryClient = useQueryClient();
  const setInvalidateDocuments = useUploadStore((s) => s.setInvalidateDocuments);
  const setInvalidateTemplates = useUploadStore((s) => s.setInvalidateTemplates);

  useEffect(() => {
    setInvalidateDocuments(() => {
      queryClient.invalidateQueries({ queryKey: ["admin", "documents"] });
    });
    setInvalidateTemplates(() => {
      queryClient.invalidateQueries({ queryKey: ["contract-templates"] });
    });
    return () => {
      setInvalidateDocuments(null);
      setInvalidateTemplates(null);
    };
  }, [queryClient, setInvalidateDocuments, setInvalidateTemplates]);

  return null;
}
