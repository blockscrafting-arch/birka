import { useCallback, useRef } from "react";

/**
 * Генерирует короткий бип через Web Audio API.
 */
function beep(
  audioContext: AudioContext,
  frequency: number,
  durationMs: number,
  type: OscillatorType = "sine"
): void {
  const oscillator = audioContext.createOscillator();
  const gainNode = audioContext.createGain();
  oscillator.connect(gainNode);
  gainNode.connect(audioContext.destination);
  oscillator.type = type;
  oscillator.frequency.value = frequency;
  gainNode.gain.setValueAtTime(0.15, audioContext.currentTime);
  gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + durationMs / 1000);
  oscillator.start(audioContext.currentTime);
  oscillator.stop(audioContext.currentTime + durationMs / 1000);
}

/**
 * Хук для звуковой и вибро-обратной связи при сканировании штрихкодов.
 * Генерирует бипы программно (без внешних файлов) и вызывает vibrate при поддержке.
 */
export function useScanFeedback() {
  const audioContextRef = useRef<AudioContext | null>(null);

  const getContext = useCallback((): AudioContext | null => {
    if (typeof window === "undefined") return null;
    if (!audioContextRef.current) {
      audioContextRef.current = new (window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext)();
    }
    return audioContextRef.current;
  }, []);

  const playSuccess = useCallback(() => {
    const ctx = getContext();
    if (ctx) {
      ctx.resume?.().then(() => {
        beep(ctx, 880, 80);
      });
    }
    if (navigator.vibrate) navigator.vibrate(100);
  }, [getContext]);

  const playError = useCallback(() => {
    const ctx = getContext();
    if (ctx) {
      ctx.resume?.().then(() => {
        beep(ctx, 220, 120);
        setTimeout(() => beep(ctx, 180, 120), 180);
      });
    }
    if (navigator.vibrate) navigator.vibrate([100, 50, 100]);
  }, [getContext]);

  const playWarning = useCallback(() => {
    const ctx = getContext();
    if (ctx) {
      ctx.resume?.().then(() => {
        beep(ctx, 440, 100);
      });
    }
    if (navigator.vibrate) navigator.vibrate(80);
  }, [getContext]);

  return { playSuccess, playError, playWarning };
}
