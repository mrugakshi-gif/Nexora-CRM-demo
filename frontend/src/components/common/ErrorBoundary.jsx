import React from 'react';
import Icon from './Icon';

export default class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    console.error('[ErrorBoundary caught error]:', error, errorInfo);
  }

  handleReset = () => {
    this.setState({ hasError: false, error: null });
    if (this.props.onReset) {
      this.props.onReset();
    }
  };

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }
      return (
        <div style={{
          padding: '48px 24px',
          textAlign: 'center',
          background: 'var(--white, #ffffff)',
          borderRadius: '16px',
          border: '1px solid var(--border, #e5e7eb)',
          margin: '24px auto',
          maxWidth: '600px',
          boxShadow: '0 4px 20px rgba(0, 0, 0, 0.05)'
        }}>
          <div style={{
            width: '48px',
            height: '48px',
            borderRadius: '12px',
            background: 'rgba(239, 68, 68, 0.1)',
            color: 'var(--danger, #ef4444)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            margin: '0 auto 16px'
          }}>
            <Icon name="alert-triangle" size={24} stroke={2} />
          </div>
          <h2 style={{ fontSize: '18px', fontWeight: 700, color: 'var(--heading-primary, #111827)', marginBottom: '8px' }}>
            Unable to load this section
          </h2>
          <p style={{ fontSize: '14px', color: 'var(--ink-mute, #6b7280)', marginBottom: '24px', lineHeight: 1.5 }}>
            {this.state.error?.message || 'An unexpected rendering error occurred. Please try reloading.'}
          </p>
          <div style={{ display: 'flex', gap: '12px', justifyContent: 'center' }}>
            <button
              onClick={this.handleReset}
              className="btn btn-primary"
              style={{
                padding: '8px 20px',
                background: 'var(--accent-primary, #1e3a8a)',
                color: '#ffffff',
                border: 'none',
                borderRadius: '8px',
                fontSize: '13px',
                fontWeight: 600,
                cursor: 'pointer'
              }}
            >
              Try Again
            </button>
            <button
              onClick={() => window.location.reload()}
              className="btn btn-secondary"
              style={{
                padding: '8px 20px',
                background: 'var(--bg-light, #f9fafb)',
                color: 'var(--ink, #374151)',
                border: '1px solid var(--border, #d1d5db)',
                borderRadius: '8px',
                fontSize: '13px',
                fontWeight: 600,
                cursor: 'pointer'
              }}
            >
              Reload Page
            </button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
