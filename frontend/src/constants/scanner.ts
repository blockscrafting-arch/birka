/** Сообщения об ошибках и подсказки сканера штрихкодов. */

export const CAMERA_ERROR_PERMISSION =
  "Разрешите доступ к камере в настройках браузера";
export const CAMERA_ERROR_NOT_FOUND = "Камера не найдена";
export const CAMERA_ERROR_NOT_READABLE = "Камера занята или недоступна";
export const SCANNER_ERROR_PREFIX = "Ошибка сканера";
export const SCAN_WARNING_NOT_IN_ORDER = "ШК не найден в товарах заявки";
export const SCAN_ERROR_MISMATCH =
  "Отсканированный ШК не совпадает с выбранной позицией";

const MAX_ERROR_LENGTH = 80;

/**
 * Определяет, является ли сообщение «ошибкой кадра» (в кадре не найден QR/штрихкод).
 * Такие ошибки библиотека вызывает на каждом кадре при пустом изображении — их
 * не показывают пользователю, чтобы избежать мелькания интерфейса.
 *
 * @returns true — ошибка кадра, не показывать в UI; false — реальная ошибка или неизвестное сообщение, показывать.
 */
export function isScanFrameError(msg: string): boolean {
  const lower = String(msg).toLowerCase();

  // Шаг 1: признаки реальной ошибки (камера/доступ) — показывать пользователю
  const realErrorMarkers = [
    "notallowederror",
    "permission",
    "notreadableerror",
    "error getting usermedia",
    "usermedia",
    "insecure context",
    "no camera",
    "notfounderror",
  ];
  if (realErrorMarkers.some((marker) => lower.includes(marker))) {
    return false;
  }

  // Шаг 2: признаки ошибки кадра (ничего не распознано в кадре) — не показывать
  const frameErrorMarkers = [
    "no barcode",
    "no qr",
    "no barcode or qr code",
    "qr code parse error",
    "notfoundexception",
    "not detected",
  ];
  if (frameErrorMarkers.some((marker) => lower.includes(marker))) {
    return true;
  }

  // Шаг 3: неизвестное сообщение — показывать, чтобы не скрыть реальную ошибку
  return false;
}

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
  if (m.includes("NotFoundError")) {
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
