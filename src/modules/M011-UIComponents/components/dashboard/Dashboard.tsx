/**
 * Dashboard - Main dashboard component with widget layout
 * 
 * Provides the main dashboard interface with:
 * - Responsive grid layout for widgets
 * - Real-time data updates
 * - Customizable widget arrangement
 * - Accessibility features
 * - Error boundaries and loading states
 */

import React, { useState, useEffect, useCallback } from 'react';
import {
  Box,
  Grid,
  Paper,
  Typography,
  Button,
  CircularProgress,
  Alert,
  useTheme,
  useMediaQuery,
  Fab,
  Tooltip
} from '@mui/material';
import {
  Refresh as RefreshIcon,
  Settings as SettingsIcon,
  Add as AddIcon
} from '@mui/icons-material';

import DocumentHealthWidget from './DocumentHealthWidget';
import QualityMetricsWidget from './QualityMetricsWidget';
import TrackingMatrixWidget from './TrackingMatrixWidget';
import RecentActivityWidget from './RecentActivityWidget';
import QuickActionsWidget from './QuickActionsWidget';

import { DashboardState, DashboardLayout } from './types';
import { useGlobalState } from '../../core/state-management';
import { BackendServiceFactory } from '../../core/integration-contracts';
import { eventManager, UIEventType } from '../../core/event-system';
import { accessibilityManager } from '../../core/accessibility';

/**
 * Default dashboard layout
 */
const DEFAULT_LAYOUT: DashboardLayout = {
  columns: 12,
  rowHeight: 100,
  margin: [16, 16],
  containerPadding: [16, 16],
  widgets: [
    {
      id: 'document-health',
      component: 'DocumentHealthWidget',
      position: { x: 0, y: 0, width: 6, height: 3 }
    },
    {
      id: 'quality-metrics',
      component: 'QualityMetricsWidget',
      position: { x: 6, y: 0, width: 6, height: 3 }
    },
    {
      id: 'tracking-matrix',
      component: 'TrackingMatrixWidget',
      position: { x: 0, y: 3, width: 8, height: 4 }
    },
    {
      id: 'recent-activity',
      component: 'RecentActivityWidget',
      position: { x: 8, y: 3, width: 4, height: 4 }
    },
    {
      id: 'quick-actions',
      component: 'QuickActionsWidget',
      position: { x: 0, y: 7, width: 12, height: 2 }
    }
  ]
};

/**
 * Widget component mapping
 */
const WIDGET_COMPONENTS = {
  DocumentHealthWidget,
  QualityMetricsWidget,
  TrackingMatrixWidget,
  RecentActivityWidget,
  QuickActionsWidget
};

/**
 * Dashboard component
 */
const Dashboard: React.FC = () => {
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('md'));
  const globalState = useGlobalState();
  const state = globalState.getState();

  // Dashboard state
  const [dashboardState, setDashboardState] = useState<DashboardState>({
    layout: DEFAULT_LAYOUT,
    data: {},
    loading: {},
    errors: {},
    lastRefresh: {}
  });

  const [globalLoading, setGlobalLoading] = useState(true);
  const [lastGlobalRefresh, setLastGlobalRefresh] = useState<number>(0);

  // Load dashboard data
  const loadDashboardData = useCallback(async () => {
    setGlobalLoading(true);
    
    try {
      // Load data from backend services
      const qualityService = BackendServiceFactory.createQualityAnalysisService();
      const configService = BackendServiceFactory.createConfigurationService();

      const [qualityTrends, configuration] = await Promise.allSettled([
        qualityService.getQualityTrends('7d'),
        configService.getConfiguration()
      ]);

      // Mock data for Pass 1 implementation
      const mockData = {
        documentHealth: {
          overall: 87,
          totalDocuments: 24,
          byType: {
            'API Documentation': { count: 8, averageScore: 89, trend: 'up' as const },
            'User Guide': { count: 6, averageScore: 85, trend: 'stable' as const },
            'Technical Spec': { count: 10, averageScore: 88, trend: 'up' as const }
          },
          recentScores: [
            { date: '2025-08-24', score: 82 },
            { date: '2025-08-25', score: 84 },
            { date: '2025-08-26', score: 86 },
            { date: '2025-08-27', score: 85 },
            { date: '2025-08-28', score: 87 },
            { date: '2025-08-29', score: 89 },
            { date: '2025-08-30', score: 87 }
          ],
          issues: [
            {
              id: 'issue-1',
              type: 'completeness',
              severity: 'medium' as const,
              message: 'Missing implementation details in API documentation',
              documentId: 'doc-1',
              documentName: 'Payment API.md'
            },
            {
              id: 'issue-2',
              type: 'clarity',
              severity: 'low' as const,
              message: 'Complex sentences detected in user guide',
              documentId: 'doc-2',
              documentName: 'User Onboarding.md'
            }
          ]
        },
        qualityMetrics: {
          dimensions: {
            completeness: 85,
            clarity: 92,
            structure: 88,
            accuracy: 87,
            formatting: 94
          },
          trends: {
            completeness: [
              { date: '2025-08-24', value: 82 },
              { date: '2025-08-25', value: 83 },
              { date: '2025-08-26', value: 84 },
              { date: '2025-08-27', value: 85 }
            ]
          },
          benchmarks: {
            completeness: 85,
            clarity: 90,
            structure: 85,
            accuracy: 88,
            formatting: 92
          }
        },
        trackingMatrix: {
          nodes: [
            { id: 'doc-1', name: 'API Documentation', type: 'api', status: 'ready' as const, qualityScore: 89, size: 120 },
            { id: 'doc-2', name: 'User Guide', type: 'guide', status: 'ready' as const, qualityScore: 85, size: 80 },
            { id: 'doc-3', name: 'Setup Guide', type: 'guide', status: 'draft' as const, qualityScore: 72, size: 40 }
          ],
          edges: [
            { source: 'doc-1', target: 'doc-2', type: 'references' as const, strength: 0.8 },
            { source: 'doc-2', target: 'doc-3', type: 'includes' as const, strength: 0.6 }
          ],
          clusters: [
            { id: 'cluster-1', name: 'API Documentation', nodes: ['doc-1'], health: 89 },
            { id: 'cluster-2', name: 'User Documentation', nodes: ['doc-2', 'doc-3'], health: 78 }
          ]
        },
        recentActivity: {
          activities: [
            {
              id: 'activity-1',
              type: 'generated' as const,
              title: 'API Documentation Generated',
              description: 'Generated comprehensive API documentation from OpenAPI spec',
              timestamp: '2025-08-31T10:30:00Z',
              documentId: 'doc-1',
              documentName: 'Payment API.md'
            },
            {
              id: 'activity-2',
              type: 'analyzed' as const,
              title: 'Quality Analysis Complete',
              description: 'Analyzed 12 documents with 87% average quality score',
              timestamp: '2025-08-31T09:15:00Z'
            }
          ]
        }
      };

      setDashboardState(prev => ({
        ...prev,
        data: mockData
      }));

      setLastGlobalRefresh(Date.now());
      
      // Emit dashboard loaded event
      eventManager.emitSimple(UIEventType.DATA_LOADED, 'dashboard', {
        dataTypes: ['documentHealth', 'qualityMetrics', 'trackingMatrix', 'recentActivity']
      });

      // Announce for screen readers
      accessibilityManager.announceToScreenReader('Dashboard data loaded');

    } catch (error) {
      console.error('Failed to load dashboard data:', error);
      
      // Emit error event
      eventManager.emitSimple(UIEventType.DATA_ERROR, 'dashboard', {
        error: (error as Error).message
      });

      // Show error state
      globalState.addError({
        message: 'Failed to load dashboard data',
        severity: 'medium',
        module: 'dashboard'
      });
    } finally {
      setGlobalLoading(false);
    }
  }, [globalState]);

  // Handle global refresh
  const handleGlobalRefresh = useCallback(async () => {
    await loadDashboardData();
  }, [loadDashboardData]);

  // Handle widget refresh
  const handleWidgetRefresh = useCallback(async (widgetId: string) => {
    setDashboardState(prev => ({
      ...prev,
      loading: { ...prev.loading, [widgetId]: true },
      errors: { ...prev.errors, [widgetId]: null }
    }));

    try {
      // Simulate widget-specific data loading
      await new Promise(resolve => setTimeout(resolve, 1000));
      
      setDashboardState(prev => ({
        ...prev,
        lastRefresh: { ...prev.lastRefresh, [widgetId]: Date.now() }
      }));

    } catch (error) {
      setDashboardState(prev => ({
        ...prev,
        errors: { ...prev.errors, [widgetId]: (error as Error).message }
      }));
    } finally {
      setDashboardState(prev => ({
        ...prev,
        loading: { ...prev.loading, [widgetId]: false }
      }));
    }
  }, []);

  // Load data on mount
  useEffect(() => {
    loadDashboardData();
  }, [loadDashboardData]);

  // Render widget
  const renderWidget = (widget: DashboardLayout['widgets'][0]) => {
    const WidgetComponent = WIDGET_COMPONENTS[widget.component as keyof typeof WIDGET_COMPONENTS];
    
    if (!WidgetComponent) {
      return (
        <Alert severity="error" sx={{ height: '100%' }}>
          Unknown widget: {widget.component}
        </Alert>
      );
    }

    return (
      <WidgetComponent
        data={dashboardState.data}
        loading={dashboardState.loading[widget.id] || false}
        error={dashboardState.errors[widget.id]}
        onRefresh={() => handleWidgetRefresh(widget.id)}
        {...widget.props}
      />
    );
  };

  // Show loading state
  if (globalLoading) {
    return (
      <Box
        sx={{
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          minHeight: '60vh',
          flexDirection: 'column',
          gap: 2
        }}
      >
        <CircularProgress size={48} />
        <Typography variant="body1" color="text.secondary">
          Loading dashboard...
        </Typography>
      </Box>
    );
  }

  return (
    <Box sx={{ width: '100%', position: 'relative' }}>
      {/* Header */}
      <Box
        sx={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          mb: 3,
          flexWrap: 'wrap',
          gap: 2
        }}
      >
        <Box>
          <Typography
            variant="h4"
            component="h1"
            gutterBottom
            sx={{ fontWeight: 600, mb: 1 }}
          >
            Dashboard
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Monitor your documentation health and progress
          </Typography>
        </Box>

        <Box sx={{ display: 'flex', gap: 1 }}>
          <Button
            variant="outlined"
            startIcon={<RefreshIcon />}
            onClick={handleGlobalRefresh}
            disabled={globalLoading}
          >
            Refresh
          </Button>
          <Button
            variant="outlined"
            startIcon={<SettingsIcon />}
          >
            Customize
          </Button>
        </Box>
      </Box>

      {/* Widget Grid */}
      <Grid container spacing={2}>
        {dashboardState.layout.widgets.map((widget) => (
          <Grid
            item
            key={widget.id}
            xs={12}
            md={widget.position.width}
            sx={{
              height: isMobile ? 'auto' : widget.position.height * dashboardState.layout.rowHeight
            }}
          >
            <Paper
              sx={{
                height: '100%',
                p: 2,
                display: 'flex',
                flexDirection: 'column',
                
                // High contrast support
                ...(state.ui.accessibility.highContrast && {
                  backgroundColor: '#ffffff',
                  border: '2px solid #000000',
                  color: '#000000'
                })
              }}
              elevation={1}
            >
              {renderWidget(widget)}
            </Paper>
          </Grid>
        ))}
      </Grid>

      {/* Floating Action Button for quick actions */}
      <Tooltip title="Quick Actions">
        <Fab
          color="primary"
          aria-label="Quick actions"
          sx={{
            position: 'fixed',
            bottom: 24,
            right: 24,
            zIndex: theme.zIndex.speedDial
          }}
        >
          <AddIcon />
        </Fab>
      </Tooltip>

      {/* Last updated info */}
      {lastGlobalRefresh > 0 && (
        <Typography
          variant="caption"
          color="text.secondary"
          sx={{
            position: 'fixed',
            bottom: 16,
            left: 16,
            backgroundColor: theme.palette.background.paper,
            px: 1,
            py: 0.5,
            borderRadius: 1,
            border: `1px solid ${theme.palette.divider}`
          }}
        >
          Last updated: {new Date(lastGlobalRefresh).toLocaleTimeString()}
        </Typography>
      )}
    </Box>
  );
};

export default Dashboard;