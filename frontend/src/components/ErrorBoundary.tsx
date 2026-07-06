import { Component, type ErrorInfo, type ReactNode } from "react";
import { reportClientError } from "../api/reportError";
import s from "./ErrorBoundary.module.css";

/*
 * Top-level crash guard. A render-time exception anywhere in the tree (a screen, a provider, a
 * bad API shape) would otherwise blank the whole PWA to a white screen with no recovery. This
 * catches it, logs it, and shows a friendly reload fallback in the app's own visual language.
 * Mounted as the outermost wrapper in main.tsx so it covers the providers too.
 *
 * (componentDidCatch is the single place a Sentry/error-tracking call would go later - see the
 * beta-readiness roadmap.)
 */

interface Props {
  children: ReactNode;
}

interface State {
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  componentDidCatch(error: Error, info: ErrorInfo): void {
    console.error("Uncaught render error:", error, info.componentStack);
    reportClientError(error.message, {
      kind: "react",
      stack: `${error.stack ?? ""}\n--- component stack ---${info.componentStack ?? ""}`,
    });
  }

  private handleReload = (): void => {
    window.location.reload();
  };

  render(): ReactNode {
    const { error } = this.state;
    if (!error) return this.props.children;
    return (
      <div className={s.wrap} role="alert">
        <div className={s.title}>Something went wrong</div>
        <div className={s.detail}>
          The app hit an unexpected error. Reloading usually clears it.
        </div>
        <button className={s.reload} onClick={this.handleReload}>
          Reload app
        </button>
        {error.message && <div className={s.errText}>{error.message}</div>}
      </div>
    );
  }
}
