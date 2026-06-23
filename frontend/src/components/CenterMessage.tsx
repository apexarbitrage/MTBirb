import s from "./CenterMessage.module.css";

/*
 * Fills the phone frame and centers a short status message - used for the trail
 * fetch's loading / error / empty states so screens never render against missing data.
 */
export function CenterMessage({
  title,
  detail,
  onRetry,
}: {
  title: string;
  detail?: string;
  onRetry?: () => void;
}) {
  return (
    <div className={s.wrap}>
      <div className={s.title}>{title}</div>
      {detail && <div className={s.detail}>{detail}</div>}
      {onRetry && (
        <button className={s.retry} onClick={onRetry}>
          Try again
        </button>
      )}
    </div>
  );
}
