/**
 * Dashboard component types and interfaces
 */

import * as React from 'react';

/**
 * Dashboard widget base props
 */
export interface WidgetProps extends React.ComponentProps<any> {
  title?: string;
  loading?: boolean;
  error?: string | null;
  height?: number | string;
  refreshable?: boolean;
  onRefresh?: () => Promise<void>;
}

/**
 * Document health data
 */
export interface DocumentHealthData {
  overall: number;
  totalDocuments: number;
  byType: {
    [docType: string]: {
      count: number;
      averageScore: number;
      trend: 'up' | 'down' | 'stable';
    };
  };
  recentScores: Array<{
    date: string;
    score: number;
  }>;
  issues: Array<{
    id: string;
    type: string;
    severity: 'low' | 'medium' | 'high' | 'critical';
    message: string;
    documentId: string;
    documentName: string;
  }>;
}

/**
 * Quality metrics data
 */
export interface QualityMetricsData {
  dimensions: {
    completeness: number;
    clarity: number;
    structure: number;
    accuracy: number;
    formatting: number;
  };
  trends: {
    [dimension: string]: Array<{
      date: string;
      value: number;
    }>;
  };
  benchmarks: {
    [dimension: string]: number;
  };
}

/**
 * Tracking matrix data
 */
export interface TrackingMatrixData {
  nodes: Array<{
    id: string;
    name: string;
    type: string;
    status: 'draft' | 'ready' | 'outdated' | 'error';
    qualityScore: number;
    size: number;
  }>;
  edges: Array<{
    source: string;
    target: string;
    type: 'depends' | 'references' | 'includes';
    strength: number;
  }>;
  clusters: Array<{
    id: string;
    name: string;
    nodes: string[];
    health: number;
  }>;
}

/**
 * Recent activity data
 */
export interface RecentActivityData {
  activities: Array<{
    id: string;
    type: 'generated' | 'analyzed' | 'enhanced' | 'updated';
    title: string;
    description: string;
    timestamp: string;
    documentId?: string;
    documentName?: string;
    metadata?: {
      [key: string]: any;
    };
  }>;
}

/**
 * Quick action definition
 */
export interface QuickAction {
  id: string;
  label: string;
  description?: string;
  icon: string | React.ReactNode;
  action: () => Promise<void> | void;
  shortcut?: string;
  disabled?: boolean;
  category?: string;
}

/**
 * Dashboard layout configuration
 */
export interface DashboardLayout {
  widgets: Array<{
    id: string;
    component: string;
    position: {
      x: number;
      y: number;
      width: number;
      height: number;
    };
    props?: any;
  }>;
  columns: number;
  rowHeight: number;
  margin: [number, number];
  containerPadding: [number, number];
}

/**
 * Dashboard state interface
 */
export interface DashboardState {
  layout: DashboardLayout;
  data: {
    documentHealth?: DocumentHealthData;
    qualityMetrics?: QualityMetricsData;
    trackingMatrix?: TrackingMatrixData;
    recentActivity?: RecentActivityData;
  };
  loading: {
    [widgetId: string]: boolean;
  };
  errors: {
    [widgetId: string]: string | null;
  };
  lastRefresh: {
    [widgetId: string]: number;
  };
}