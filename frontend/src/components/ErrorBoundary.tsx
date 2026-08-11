"use client";

import React, { Component, ErrorInfo, ReactNode } from "react";
import { AlertTriangle, RefreshCw } from "lucide-react";

interface Props {
  children: ReactNode;
  fallbackTitle?: string;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
    error: null,
  };

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error("ErrorBoundary caught an error:", error, errorInfo);
  }

  private handleReset = () => {
    this.setState({ hasError: false, error: null });
  };

  public render() {
    if (this.state.hasError) {
      return (
        <div className="error-boundary-card">
          <div className="error-boundary-header">
            <AlertTriangle className="icon-amber" size={20} />
            <h4>{this.props.fallbackTitle || "Unable to render component"}</h4>
          </div>
          <p className="error-boundary-msg">
            {this.state.error?.message || "An unexpected rendering error occurred in this view widget."}
          </p>
          <button onClick={this.handleReset} className="btn btn-secondary btn-sm" style={{ marginTop: 12 }}>
            <RefreshCw size={14} style={{ marginRight: 6 }} /> Try Reloading Widget
          </button>
        </div>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;
