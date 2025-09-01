/**
 * Layout component types and interfaces
 */

import { ReactNode } from 'react';
import { ComponentProps } from '../../core/interfaces';

/**
 * Base layout props
 */
export interface LayoutProps extends ComponentProps {
  children?: ReactNode;
}

/**
 * App layout configuration
 */
export interface AppLayoutConfig {
  sidebarWidth: number;
  headerHeight: number;
  footerHeight: number;
  breakpoints: {
    mobile: number;
    tablet: number;
    desktop: number;
  };
  navigation: NavigationConfig;
}

/**
 * Navigation configuration
 */
export interface NavigationConfig {
  items: NavigationItem[];
  collapsible: boolean;
  defaultCollapsed: boolean;
}

/**
 * Navigation item
 */
export interface NavigationItem {
  id: string;
  label: string;
  icon?: ReactNode;
  path: string;
  children?: NavigationItem[];
  badge?: string | number;
  disabled?: boolean;
  external?: boolean;
}

/**
 * Sidebar props
 */
export interface SidebarProps extends LayoutProps {
  open: boolean;
  onClose: () => void;
  width: number;
  variant: 'permanent' | 'persistent' | 'temporary';
  navigation: NavigationItem[];
}

/**
 * Header props
 */
export interface HeaderProps extends LayoutProps {
  title?: string;
  showMenuButton?: boolean;
  onMenuClick?: () => void;
  actions?: ReactNode;
}

/**
 * Main content props
 */
export interface MainContentProps extends LayoutProps {
  sidebarOpen?: boolean;
  sidebarWidth?: number;
}

/**
 * Footer props
 */
export interface FooterProps extends LayoutProps {
  compact?: boolean;
}