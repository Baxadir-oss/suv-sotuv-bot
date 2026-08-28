// window.Telegram.WebApp atrofida yupqa, xavfsiz wrapper.
// Oddiy brauzerda (Telegram tashqarisida) ochilsa ham xato bermasligi uchun
// har bir chaqiruv mavjudligini tekshiradi.

const tg = typeof window !== "undefined" ? window.Telegram?.WebApp : null;

export function initTelegramApp() {
  if (!tg) return;
  tg.ready();
  tg.expand();
}

export function getInitData() {
  return tg?.initData || "";
}

export function getUser() {
  return tg?.initDataUnsafe?.user || null;
}

export function hapticSuccess() {
  tg?.HapticFeedback?.notificationOccurred?.("success");
}

export function hapticImpact(style = "light") {
  tg?.HapticFeedback?.impactOccurred?.(style);
}

export function showAlert(message) {
  if (tg?.showAlert) {
    tg.showAlert(message);
  } else {
    // eslint-disable-next-line no-alert
    alert(message);
  }
}

export function closeApp() {
  tg?.close?.();
}

export function isInsideTelegram() {
  return Boolean(tg);
}
