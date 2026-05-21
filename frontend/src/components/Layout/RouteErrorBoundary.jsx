import { Component } from 'react';

/**
 * Catches render errors so a single broken screen does not leave a blank app.
 */
export default class RouteErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  render() {
    if (this.state.hasError) {
      const msg = this.state.error?.message || 'Something went wrong';
      return (
        <div className="flex flex-col items-center justify-center min-h-[40vh] px-6 py-12 text-center">
          <div className="text-4xl mb-3" aria-hidden>
            ⚠️
          </div>
          <h2 className="text-lg font-bold text-slate-900">This page could not be displayed</h2>
          <p className="text-sm text-slate-600 mt-2 max-w-md whitespace-pre-wrap break-words">{msg}</p>
          <button
            type="button"
            className="btn-primary mt-6"
            onClick={() => window.location.reload()}
          >
            Reload page
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}
