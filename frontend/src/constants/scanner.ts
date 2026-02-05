/** Сообщения об ошибках и подсказки сканера штрихкодов. */

export const CAMERA_ERROR_PERMISSION =
  "Разрешите доступ к камере в настройках браузера";
export const CAMERA_ERROR_NOT_FOUND = "Камера не найдена";
export const CAMERA_ERROR_NOT_READABLE = "Камера занята или недоступна";
export const SCANNER_ERROR_PREFIX = "Ошибка сканера";
export const SCAN_WARNING_NOT_IN_ORDER = "ШК не найден в позициях заявки";
export const SCAN_ERROR_MISMATCH =
  "Отсканированный ШК не совпадает с выбранной позицией";

const MAX_ERROR_LENGTH = 80;

/**
 * Возвращает сообщение для пользователя по тексту ошибки камеры/библиотеки.
 */
export function getCameraErrorMessage(msg: string): string {
  const m = String(msg);
  if (
    m.includes("NotAllowedError") ||
    m.includes("Permission") ||
    m.includes("NotAllowed")
  ) {
    return CAMERA_ERROR_PERMISSION;
  }
  if (m.includes("NotFoundError") || m.includes("NotFound")) {
    return CAMERA_ERROR_NOT_FOUND;
  }
  if (m.includes("NotReadableError") || m.includes("NotReadable")) {
    return CAMERA_ERROR_NOT_READABLE;
  }
  const short = m.slice(0, MAX_ERROR_LENGTH);
  return short
    ? `${SCANNER_ERROR_PREFIX}: ${short}${m.length > MAX_ERROR_LENGTH ? "…" : ""}`
    : SCANNER_ERROR_PREFIX;
}
