import React, { Component, ErrorInfo, ReactNode } from "react";

import { Button } from "./Button";

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

/**
 * Catches unhandled React render errors and shows a fallback UI instead of a white screen.
 */
export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  // eslint-disable-next-line @typescript-eslint/no-unused-vars -- required by React ErrorBoundary API
  componentDidCatch(error: Error, errorInfo: ErrorInfo): void {
    if (typeof window !== "undefined" && window.Telegram?.WebApp?.showAlert) {
      window.Telegram.WebApp.showAlert("Произошла ошибка. Попробуйте обновить приложение.");
    }
  }

  handleRetry = (): void => {
    this.setState({ hasError: false, error: null });
  };

  render(): ReactNode {
    if (this.state.hasError) {
      return (
        <div
          className="flex min-h-screen flex-col items-center justify-center gap-4 bg-slate-50 px-4"
          role="alert"
        >
          <p className="text-center text-slate-700">
            Что-то пошло не так. Обновите приложение или попробуйте позже.
          </p>
          <Button onClick={this.handleRetry}>Попробовать снова</Button>
        </div>
      );
    }
    return this.props.children;
  }
}
