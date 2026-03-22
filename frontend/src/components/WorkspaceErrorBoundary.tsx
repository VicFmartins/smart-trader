import { Component, type ErrorInfo, type ReactNode } from "react";

type WorkspaceErrorBoundaryProps = {
  children: ReactNode;
  resetKey: string;
  onReset?: () => void;
};

type WorkspaceErrorBoundaryState = {
  hasError: boolean;
  message: string | null;
};

export default class WorkspaceErrorBoundary extends Component<
  WorkspaceErrorBoundaryProps,
  WorkspaceErrorBoundaryState
> {
  override state: WorkspaceErrorBoundaryState = {
    hasError: false,
    message: null
  };

  static getDerivedStateFromError(error: Error): WorkspaceErrorBoundaryState {
    return {
      hasError: true,
      message: error.message || "The workspace received an unexpected payload."
    };
  }

  override componentDidCatch(error: Error, info: ErrorInfo) {
    console.error("Workspace render failure", error, info);
  }

  override componentDidUpdate(prevProps: WorkspaceErrorBoundaryProps) {
    if (prevProps.resetKey !== this.props.resetKey && this.state.hasError) {
      this.setState({ hasError: false, message: null });
    }
  }

  private handleReset = () => {
    this.setState({ hasError: false, message: null });
    this.props.onReset?.();
  };

  override render() {
    if (this.state.hasError) {
      return (
        <section className="rounded-[32px] border border-rose-200 bg-[#f8fafc] p-8 shadow-[0_24px_70px_rgba(15,23,42,0.18)]">
          <div className="rounded-[28px] border border-rose-200 bg-rose-50 px-6 py-12 text-center text-rose-700">
            <h2 className="font-display text-2xl font-bold tracking-tight">Workspace recovery needed</h2>
            <p className="mx-auto mt-4 max-w-2xl text-sm leading-7">
              O frontend encontrou uma resposta inesperada e interrompeu a renderizacao desta area para evitar uma tela vazia.
            </p>
            {this.state.message ? <p className="mx-auto mt-3 max-w-2xl text-sm leading-7">{this.state.message}</p> : null}
            <button
              type="button"
              onClick={this.handleReset}
              className="mt-6 rounded-2xl bg-slate-950 px-5 py-3 text-sm font-semibold text-white transition hover:opacity-90"
            >
              Recover workspace
            </button>
          </div>
        </section>
      );
    }

    return this.props.children;
  }
}
