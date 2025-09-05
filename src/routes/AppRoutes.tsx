/**
 * React Router configuration for DevDocAI application
 * Maps URLs to components and handles routing logic
 */

import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';

// Import page components
import Dashboard from '../components/Dashboard';
import DocumentGenerator from '../components/DocumentGenerator';
import QualityAnalyzer from '../components/QualityAnalyzer';
import TemplateManager from '../components/TemplateManager';
import SecurityDashboard from '../components/SecurityDashboard';
import EnhancementPipeline from '../components/EnhancementPipeline';
import ReviewEngine from '../components/ReviewEngine';
import ConfigurationPanel from '../components/ConfigurationPanel';

// Route configuration type
export interface RouteConfig {
  path: string;
  id: string;
  label: string;
  component: React.ComponentType<any>;
  icon?: React.ComponentType;
  module: string;
}

// Route definitions matching AppLayout navigation
export const routeConfig: RouteConfig[] = [
  {
    path: '/',
    id: 'dashboard',
    label: 'Dashboard',
    component: Dashboard,
    module: 'M011'
  },
  {
    path: '/dashboard',
    id: 'dashboard',
    label: 'Dashboard',
    component: Dashboard,
    module: 'M011'
  },
  {
    path: '/generator',
    id: 'generator',
    label: 'Document Generator',
    component: DocumentGenerator,
    module: 'M004'
  },
  {
    path: '/quality',
    id: 'quality',
    label: 'Quality Analyzer',
    component: QualityAnalyzer,
    module: 'M005'
  },
  {
    path: '/templates',
    id: 'templates',
    label: 'Template Manager',
    component: TemplateManager,
    module: 'M006'
  },
  {
    path: '/review',
    id: 'review',
    label: 'Review Engine',
    component: ReviewEngine,
    module: 'M007'
  },
  {
    path: '/enhancement',
    id: 'enhancement',
    label: 'Enhancement Pipeline',
    component: EnhancementPipeline,
    module: 'M009'
  },
  {
    path: '/security',
    id: 'security',
    label: 'Security Dashboard',
    component: SecurityDashboard,
    module: 'M010'
  },
  {
    path: '/config',
    id: 'config',
    label: 'Configuration',
    component: ConfigurationPanel,
    module: 'M001'
  }
];

// Helper function to get route by path
export const getRouteByPath = (path: string): RouteConfig | undefined => {
  return routeConfig.find(route => route.path === path);
};

// Helper function to get route by id
export const getRouteById = (id: string): RouteConfig | undefined => {
  return routeConfig.find(route => route.id === id);
};

// Helper function to get current route from pathname
export const getCurrentRoute = (pathname: string): RouteConfig | undefined => {
  // Exact match first
  const exactMatch = routeConfig.find(route => route.path === pathname);
  if (exactMatch) return exactMatch;
  
  // For root path, return dashboard
  if (pathname === '/') {
    return routeConfig.find(route => route.id === 'dashboard');
  }
  
  return undefined;
};

interface AppRoutesProps {
  moduleStatus: Record<string, boolean>;
}

const AppRoutes: React.FC<AppRoutesProps> = ({ moduleStatus }) => {
  return (
    <Routes>
      {routeConfig.map((route) => {
        const Component = route.component;
        
        return (
          <Route
            key={route.path}
            path={route.path}
            element={
              <Component
                moduleStatus={route.id === 'dashboard' ? moduleStatus : undefined}
              />
            }
          />
        );
      })}
      
      {/* Catch-all route - redirect to dashboard */}
      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  );
};

export default AppRoutes;