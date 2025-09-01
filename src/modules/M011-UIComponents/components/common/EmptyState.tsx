/**
 * EmptyState - Empty state illustrations and messaging
 * 
 * Provides empty state components for different scenarios:
 * - No data available
 * - No search results
 * - Welcome/onboarding states
 * - Error states with retry actions
 */

import React from 'react';
import {
  Box,
  Typography,
  Button,
  Avatar,
  useTheme
} from '@mui/material';
import {
  Description,
  SearchOff,
  ErrorOutline,
  Add,
  Refresh,
  GetApp,
  TrendingUp,
  Assignment,
  Settings,
  School
} from '@mui/icons-material';

import { useGlobalState } from '../../core/state-management';

/**
 * Props interface
 */
interface EmptyStateProps {
  variant: 
    | 'no-documents' 
    | 'no-results' 
    | 'no-activity' 
    | 'no-metrics' 
    | 'no-templates'
    | 'welcome'
    | 'error'
    | 'custom';
  title?: string;
  description?: string;
  icon?: React.ReactNode;
  primaryAction?: {
    label: string;
    onClick: () => void;
    variant?: 'contained' | 'outlined' | 'text';
  };
  secondaryAction?: {
    label: string;
    onClick: () => void;
    variant?: 'contained' | 'outlined' | 'text';
  };
  illustration?: React.ReactNode;
  compact?: boolean;
  className?: string;
}

/**
 * Empty state configurations
 */
const EMPTY_STATE_CONFIG = {
  'no-documents': {
    icon: <Description fontSize="large" />,
    title: 'No Documents Found',
    description: 'Start by generating your first document or importing existing ones.',
    primaryAction: { label: 'Generate Document', icon: <Add /> },
    secondaryAction: { label: 'Import Documents', icon: <GetApp /> }
  },
  'no-results': {
    icon: <SearchOff fontSize="large" />,
    title: 'No Results Found',
    description: 'Try adjusting your search criteria or filters.',
    primaryAction: { label: 'Clear Filters', icon: <Refresh /> }
  },
  'no-activity': {
    icon: <TrendingUp fontSize="large" />,
    title: 'No Recent Activity',
    description: 'Start generating or analyzing documents to see activity here.',
    primaryAction: { label: 'Generate Document', icon: <Add /> }
  },
  'no-metrics': {
    icon: <TrendingUp fontSize="large" />,
    title: 'No Metrics Available',
    description: 'Quality metrics will appear here once you analyze your documents.',
    primaryAction: { label: 'Analyze Documents', icon: <TrendingUp /> }
  },
  'no-templates': {
    icon: <Assignment fontSize="large" />,
    title: 'No Templates Available',
    description: 'Create custom templates or import from the template registry.',
    primaryAction: { label: 'Browse Templates', icon: <Assignment /> },
    secondaryAction: { label: 'Create Template', icon: <Add /> }
  },
  'welcome': {
    icon: <School fontSize="large" />,
    title: 'Welcome to DevDocAI',
    description: 'Your AI-powered documentation generation and analysis system is ready to use.',
    primaryAction: { label: 'Get Started', icon: <School /> },
    secondaryAction: { label: 'View Documentation', icon: <Description /> }
  },
  'error': {
    icon: <ErrorOutline fontSize="large" />,
    title: 'Something Went Wrong',
    description: 'We encountered an error while loading this content.',
    primaryAction: { label: 'Try Again', icon: <Refresh /> },
    secondaryAction: { label: 'Report Issue', icon: <ErrorOutline /> }
  }
};

/**
 * EmptyState component
 */
const EmptyState: React.FC<EmptyStateProps> = ({
  variant,
  title,
  description,
  icon,
  primaryAction,
  secondaryAction,
  illustration,
  compact = false,
  className
}) => {
  const theme = useTheme();
  const globalState = useGlobalState();
  const state = globalState.getState();

  // Get configuration for the variant
  const config = variant !== 'custom' ? EMPTY_STATE_CONFIG[variant] : {};

  // Use provided props or fall back to configuration
  const effectiveTitle = title || config.title || 'No Data Available';
  const effectiveDescription = description || config.description || '';
  const effectiveIcon = icon || config.icon || <Description fontSize="large" />;

  const iconSize = compact ? 48 : 80;
  const spacing = compact ? 2 : 4;

  return (
    <Box
      sx={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        textAlign: 'center',
        py: spacing,
        px: 2,
        minHeight: compact ? 200 : 300,
        
        ...(state.ui.accessibility.highContrast && {
          backgroundColor: '#ffffff',
          color: '#000000'
        })
      }}
      className={className}
      role="status"
      aria-label={`${effectiveTitle}. ${effectiveDescription}`}
    >
      {/* Custom illustration or icon */}
      {illustration || (
        <Avatar
          sx={{
            width: iconSize,
            height: iconSize,
            backgroundColor: theme.palette.grey[100],
            color: theme.palette.grey[400],
            mb: 2,
            
            ...(state.ui.accessibility.highContrast && {
              backgroundColor: '#ffffff',
              border: '2px solid #000000',
              color: '#000000'
            })
          }}
        >
          {effectiveIcon}
        </Avatar>
      )}

      {/* Title */}
      <Typography
        variant={compact ? 'h6' : 'h5'}
        component="h2"
        gutterBottom
        sx={{
          fontWeight: 600,
          color: theme.palette.text.primary,
          mb: 1,
          
          ...(state.ui.accessibility.highContrast && {
            color: '#000000'
          })
        }}
      >
        {effectiveTitle}
      </Typography>

      {/* Description */}
      {effectiveDescription && (
        <Typography
          variant="body2"
          color="text.secondary"
          sx={{
            maxWidth: 400,
            mb: spacing,
            lineHeight: 1.6,
            
            ...(state.ui.accessibility.highContrast && {
              color: '#000000'
            })
          }}
        >
          {effectiveDescription}
        </Typography>
      )}

      {/* Actions */}
      {(primaryAction || secondaryAction) && (
        <Box
          sx={{
            display: 'flex',
            flexDirection: compact ? 'column' : 'row',
            gap: 1,
            alignItems: 'center'
          }}
        >
          {primaryAction && (
            <Button
              variant={primaryAction.variant || 'contained'}
              onClick={primaryAction.onClick}
              startIcon={config.primaryAction?.icon}
              sx={{
                ...(state.ui.accessibility.highContrast && {
                  backgroundColor: '#000000',
                  color: '#ffffff',
                  border: '2px solid #000000',
                  '&:hover': {
                    backgroundColor: '#333333'
                  }
                })
              }}
            >
              {primaryAction.label}
            </Button>
          )}

          {secondaryAction && (
            <Button
              variant={secondaryAction.variant || 'outlined'}
              onClick={secondaryAction.onClick}
              startIcon={config.secondaryAction?.icon}
              sx={{
                ...(state.ui.accessibility.highContrast && {
                  backgroundColor: '#ffffff',
                  color: '#000000',
                  border: '2px solid #000000',
                  '&:hover': {
                    backgroundColor: '#f0f0f0'
                  }
                })
              }}
            >
              {secondaryAction.label}
            </Button>
          )}
        </Box>
      )}

      {/* Additional help text for accessibility */}
      {state.ui.accessibility.enhancedSupport && (
        <Typography
          variant="caption"
          color="text.secondary"
          sx={{
            mt: 2,
            fontStyle: 'italic',
            ...(state.ui.accessibility.highContrast && {
              color: '#000000'
            })
          }}
        >
          Use keyboard navigation or screen reader to interact with available actions
        </Typography>
      )}
    </Box>
  );
};

export default EmptyState;