/**
 * ErrorBoundary - Error boundary components with retry functionality
 * 
 * Provides comprehensive error handling with:
 * - React error boundary implementation
 * - Error logging and reporting
 * - Retry mechanisms
 * - Fallback UI components
 * - Accessibility support
 */

import React, { Component, ReactNode } from 'react';
import {
  Box,
  Typography,
  Button,
  Alert,
  AlertTitle,
  Paper,
  Accordion,
  AccordionSummary,
  AccordionDetails
} from '@mui/material';
import {
  ErrorOutline,
  Refresh,
  BugReport,
  ExpandMore,
  Home
} from '@mui/icons-material';

/**
 * Error boundary state interface
 */
interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
  errorInfo: React.ErrorInfo | null;
  retryCount: number;
}

/**
 * Props interface
 */
interface ErrorBoundaryProps {
  children: ReactNode;
  fallback?: ReactNode;
  onError?: (error: Error, errorInfo: React.ErrorInfo) => void;
  maxRetries?: number;
  showDetails?: boolean;
  level?: 'page' | 'component' | 'widget';
  resetKeys?: Array<string | number>;
  isolate?: boolean;
}

/**
 * Error boundary class component
 */
class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  private resetTimeoutId: number | null = null;

  constructor(props: ErrorBoundaryProps) {
    super(props);
    
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null,
      retryCount: 0
    };
  }

  static getDerivedStateFromError(error: Error): Partial<ErrorBoundaryState> {
    return {
      hasError: true,
      error
    };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    this.setState({
      error,
      errorInfo
    });

    // Log error to console in development
    if (process.env.NODE_ENV === 'development') {
      console.error('ErrorBoundary caught an error:', error, errorInfo);
    }

    // Call custom error handler if provided
    if (this.props.onError) {
      this.props.onError(error, errorInfo);
    }

    // Log to error tracking service in production
    if (process.env.NODE_ENV === 'production') {
      this.logErrorToService(error, errorInfo);
    }
  }

  componentDidUpdate(prevProps: ErrorBoundaryProps) {
    const { resetKeys } = this.props;
    const { hasError } = this.state;

    if (hasError && prevProps.resetKeys !== resetKeys) {
      if (resetKeys && resetKeys.length > 0) {
        const hasResetKeyChanged = resetKeys.some(
          (key, index) => prevProps.resetKeys?.[index] !== key
        );

        if (hasResetKeyChanged) {
          this.resetErrorBoundary();
        }
      }
    }
  }

  componentWillUnmount() {
    if (this.resetTimeoutId) {
      clearTimeout(this.resetTimeoutId);
    }
  }

  private logErrorToService = (error: Error, errorInfo: React.ErrorInfo) => {
    // In a real application, send to error tracking service
    // For now, we'll just log to console
    console.error('Production error logged:', {
      message: error.message,
      stack: error.stack,
      componentStack: errorInfo.componentStack,
      timestamp: new Date().toISOString(),
      userAgent: navigator.userAgent,
      url: window.location.href
    });
  };

  private handleRetry = () => {
    const { maxRetries = 3 } = this.props;
    const { retryCount } = this.state;

    if (retryCount < maxRetries) {
      this.setState(prevState => ({
        hasError: false,
        error: null,
        errorInfo: null,
        retryCount: prevState.retryCount + 1
      }));
    }
  };

  private resetErrorBoundary = () => {
    this.setState({
      hasError: false,
      error: null,
      errorInfo: null,
      retryCount: 0
    });
  };

  private handleReportError = () => {
    const { error, errorInfo } = this.state;
    
    // Create error report
    const errorReport = {
      message: error?.message || 'Unknown error',
      stack: error?.stack || '',
      componentStack: errorInfo?.componentStack || '',
      timestamp: new Date().toISOString(),
      userAgent: navigator.userAgent,
      url: window.location.href
    };

    // In production, this would send to error reporting service
    console.log('Error report:', errorReport);
    
    // For now, copy to clipboard
    navigator.clipboard.writeText(JSON.stringify(errorReport, null, 2))
      .then(() => {
        alert('Error report copied to clipboard');
      })
      .catch(() => {
        console.log('Failed to copy error report');
      });
  };

  private renderErrorDetails = () => {
    const { error, errorInfo } = this.state;
    const { showDetails = process.env.NODE_ENV === 'development' } = this.props;

    if (!showDetails || !error) return null;

    return (
      <Box sx={{ mt: 2 }}>
        <Accordion>
          <AccordionSummary
            expandIcon={<ExpandMore />}
            aria-controls="error-details-content"
            id="error-details-header"
          >
            <Typography variant="body2">Show Error Details</Typography>
          </AccordionSummary>
          <AccordionDetails>
            <Box sx={{ mb: 2 }}>
              <Typography variant="subtitle2" gutterBottom>
                Error Message:
              </Typography>
              <Typography
                variant="body2"
                component="pre"
                sx={{
                  backgroundColor: 'grey.100',
                  p: 1,
                  borderRadius: 1,
                  fontSize: '0.75rem',
                  overflow: 'auto',
                  fontFamily: 'monospace'
                }}
              >
                {error.message}
              </Typography>
            </Box>

            {error.stack && (
              <Box sx={{ mb: 2 }}>
                <Typography variant="subtitle2" gutterBottom>
                  Stack Trace:
                </Typography>
                <Typography
                  variant="body2"
                  component="pre"
                  sx={{
                    backgroundColor: 'grey.100',
                    p: 1,
                    borderRadius: 1,
                    fontSize: '0.75rem',
                    overflow: 'auto',
                    fontFamily: 'monospace',
                    maxHeight: 200
                  }}
                >
                  {error.stack}
                </Typography>
              </Box>
            )}

            {errorInfo?.componentStack && (
              <Box>
                <Typography variant="subtitle2" gutterBottom>
                  Component Stack:
                </Typography>
                <Typography
                  variant="body2"
                  component="pre"
                  sx={{
                    backgroundColor: 'grey.100',
                    p: 1,
                    borderRadius: 1,
                    fontSize: '0.75rem',
                    overflow: 'auto',
                    fontFamily: 'monospace',
                    maxHeight: 200
                  }}
                >
                  {errorInfo.componentStack}
                </Typography>
              </Box>
            )}
          </AccordionDetails>
        </Accordion>
      </Box>
    );
  };

  private renderErrorUI = () => {
    const { level = 'component', maxRetries = 3 } = this.props;
    const { error, retryCount } = this.state;

    const canRetry = retryCount < maxRetries;
    const isPageLevel = level === 'page';

    return (
      <Box
        sx={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          p: 3,
          textAlign: 'center',
          minHeight: isPageLevel ? '50vh' : 200,
          width: '100%'
        }}
        role="alert"
        aria-live="assertive"
      >
        <Paper
          elevation={isPageLevel ? 3 : 1}
          sx={{
            p: 3,
            maxWidth: 500,
            width: '100%'
          }}
        >
          <ErrorOutline 
            sx={{ 
              fontSize: isPageLevel ? 64 : 48, 
              color: 'error.main',
              mb: 2
            }} 
          />

          <Typography variant={isPageLevel ? 'h4' : 'h6'} gutterBottom>
            {isPageLevel ? 'Oops! Something went wrong' : 'Component Error'}
          </Typography>

          <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
            {error?.message || 'An unexpected error occurred while rendering this component.'}
          </Typography>

          <Alert severity="error" sx={{ mb: 2, textAlign: 'left' }}>
            <AlertTitle>Error Details</AlertTitle>
            {isPageLevel 
              ? 'The page encountered an error and cannot be displayed properly.'
              : 'This component failed to render due to an error.'
            }
            {retryCount > 0 && (
              <Typography variant="body2" sx={{ mt: 1 }}>
                Retry attempts: {retryCount}/{maxRetries}
              </Typography>
            )}
          </Alert>

          <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap', justifyContent: 'center' }}>
            {canRetry && (
              <Button
                variant="contained"
                startIcon={<Refresh />}
                onClick={this.handleRetry}
                size={isPageLevel ? 'medium' : 'small'}
              >
                Try Again
              </Button>
            )}

            <Button
              variant="outlined"
              startIcon={<BugReport />}
              onClick={this.handleReportError}
              size={isPageLevel ? 'medium' : 'small'}
            >
              Report Issue
            </Button>

            {isPageLevel && (
              <Button
                variant="text"
                startIcon={<Home />}
                onClick={() => window.location.href = '/'}
                size="medium"
              >
                Go Home
              </Button>
            )}
          </Box>

          {this.renderErrorDetails()}
        </Paper>
      </Box>
    );
  };

  render() {
    const { hasError } = this.state;
    const { children, fallback } = this.props;

    if (hasError) {
      return fallback || this.renderErrorUI();
    }

    return children;
  }
}

export default ErrorBoundary;