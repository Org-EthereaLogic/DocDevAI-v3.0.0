/**
 * DevDocAI v3.0.0 - Main Application Layout
 * 
 * Provides the main application layout with sidebar navigation,
 * header, and content area for all views with React Router integration.
 */

import React, { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import {
  Box,
  Drawer,
  AppBar,
  Toolbar,
  List,
  Typography,
  Divider,
  IconButton,
  ListItem,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Badge,
  Tooltip,
  Switch,
  FormControlLabel,
  Alert,
  Chip,
} from '@mui/material';
import {
  Menu as MenuIcon,
  Dashboard as DashboardIcon,
  Description as DocumentIcon,
  AssessmentOutlined as QualityIcon,
  Article as TemplateIcon,
  Security as SecurityIcon,
  AutoFixHigh as EnhancementIcon,
  RateReview as ReviewIcon,
  Settings as SettingsIcon,
  Notifications as NotificationsIcon,
  LightMode,
  DarkMode,
  ChevronLeft,
} from '@mui/icons-material';

// Import route configuration
import { routeConfig, getCurrentRoute } from '../../routes/AppRoutes';

interface AppLayoutProps {
  children: React.ReactNode;
  currentView: string;
  onThemeToggle: () => void;
  theme: 'light' | 'dark';
  notifications: any[];
  moduleStatus: Record<string, boolean>;
}

const drawerWidth = 280;

// Navigation items with icons mapping
const navigationItems = [
  { id: 'dashboard', label: 'Dashboard', icon: DashboardIcon, module: 'M011', path: '/dashboard' },
  { id: 'generator', label: 'Document Generator', icon: DocumentIcon, module: 'M004', path: '/generator' },
  { id: 'quality', label: 'Quality Analyzer', icon: QualityIcon, module: 'M005', path: '/quality' },
  { id: 'templates', label: 'Template Manager', icon: TemplateIcon, module: 'M006', path: '/templates' },
  { id: 'review', label: 'Review Engine', icon: ReviewIcon, module: 'M007', path: '/review' },
  { id: 'enhancement', label: 'Enhancement Pipeline', icon: EnhancementIcon, module: 'M009', path: '/enhancement' },
  { id: 'security', label: 'Security Dashboard', icon: SecurityIcon, module: 'M010', path: '/security' },
  { id: 'config', label: 'Configuration', icon: SettingsIcon, module: 'M001', path: '/config' },
];

const AppLayout: React.FC<AppLayoutProps> = ({
  children,
  currentView,
  onThemeToggle,
  theme,
  notifications,
  moduleStatus,
}) => {
  const navigate = useNavigate();
  const location = useLocation();
  const [mobileOpen, setMobileOpen] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(true);

  // Get current route for display
  const currentRoute = getCurrentRoute(location.pathname);

  const handleDrawerToggle = () => {
    setMobileOpen(!mobileOpen);
  };

  const handleSidebarToggle = () => {
    setSidebarOpen(prev => {
      const newState = !prev;
      console.log('Sidebar toggle:', prev, '->', newState);
      
      // Clean up any body overflow styles that might block interaction
      // Material-UI Drawer sometimes leaves these behind
      requestAnimationFrame(() => {
        document.body.style.overflow = '';
        document.documentElement.style.overflow = '';
        // Remove any aria-hidden that might be blocking interaction
        const root = document.getElementById('root');
        if (root) {
          root.removeAttribute('aria-hidden');
        }
      });
      
      return newState;
    });
  };

  const getModuleStatus = (moduleId: string) => {
    return moduleStatus[moduleId] ? 'online' : 'offline';
  };

  // Prevent Material-UI Drawer from leaving blocking styles
  useEffect(() => {
    // Function to clean up any blocking styles
    const cleanupBlockingStyles = () => {
      // Remove overflow hidden from body and html
      if (document.body.style.overflow === 'hidden') {
        document.body.style.overflow = '';
        console.log('Removed overflow:hidden from body');
      }
      if (document.documentElement.style.overflow === 'hidden') {
        document.documentElement.style.overflow = '';
        console.log('Removed overflow:hidden from html');
      }
      
      // Remove aria-hidden from root element
      const root = document.getElementById('root');
      if (root && root.getAttribute('aria-hidden') === 'true') {
        root.removeAttribute('aria-hidden');
        console.log('Removed aria-hidden from root');
      }
    };

    // Clean up immediately on mount
    cleanupBlockingStyles();

    // Set up periodic cleanup to catch any Material-UI issues
    const intervalId = setInterval(cleanupBlockingStyles, 500);

    // Also clean up on any sidebar state change
    cleanupBlockingStyles();

    return () => {
      clearInterval(intervalId);
      // Final cleanup on unmount
      cleanupBlockingStyles();
    };
  }, [sidebarOpen]); // Re-run when sidebar state changes

  const drawer = (
    <Box sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      <Box sx={{ p: 2, display: 'flex', alignItems: 'center', gap: 1 }}>
        <Typography variant="h6" noWrap component="div" sx={{ fontWeight: 600 }}>
          DevDocAI
        </Typography>
        <Chip label="v3.0.0" size="small" color="primary" variant="outlined" />
      </Box>
      <Divider />
      
      <List sx={{ flex: 1, px: 1 }}>
        {navigationItems.map((item) => {
          const Icon = item.icon;
          const isActive = location.pathname === item.path || 
            (item.id === 'dashboard' && location.pathname === '/');
          const moduleOnline = getModuleStatus(item.module) === 'online';
          
          return (
            <ListItem key={item.id} disablePadding sx={{ mb: 0.5 }}>
              <Tooltip title={!moduleOnline ? `${item.module} module offline` : ''}>
                <ListItemButton
                  selected={isActive}
                  onClick={() => navigate(item.path)}
                  disabled={!moduleOnline}
                  sx={{
                    borderRadius: 2,
                    '&.Mui-selected': {
                      backgroundColor: 'primary.main',
                      color: 'primary.contrastText',
                      '&:hover': {
                        backgroundColor: 'primary.dark',
                      },
                    },
                  }}
                >
                  <ListItemIcon 
                    sx={{ 
                      color: isActive ? 'inherit' : 'text.secondary',
                      minWidth: 40 
                    }}
                  >
                    <Icon fontSize="small" />
                  </ListItemIcon>
                  <ListItemText 
                    primary={item.label}
                    primaryTypographyProps={{
                      fontSize: '0.875rem',
                      fontWeight: isActive ? 500 : 400,
                    }}
                  />
                  <Box
                    sx={{
                      width: 8,
                      height: 8,
                      borderRadius: '50%',
                      backgroundColor: moduleOnline ? 'success.main' : 'error.main',
                    }}
                  />
                </ListItemButton>
              </Tooltip>
            </ListItem>
          );
        })}
      </List>

      <Divider />
      <Box sx={{ p: 2 }}>
        <FormControlLabel
          control={
            <Switch
              checked={theme === 'dark'}
              onChange={onThemeToggle}
              size="small"
            />
          }
          label={
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              {theme === 'dark' ? <DarkMode fontSize="small" /> : <LightMode fontSize="small" />}
              <Typography variant="body2">
                {theme === 'dark' ? 'Dark' : 'Light'}
              </Typography>
            </Box>
          }
          sx={{ margin: 0 }}
        />
      </Box>
    </Box>
  );

  return (
    <Box sx={{ display: 'flex', minHeight: '100vh' }}>
      {/* App Bar */}
      <AppBar
        position="fixed"
        sx={{
          width: { sm: sidebarOpen ? `calc(100% - ${drawerWidth}px)` : '100%' },
          ml: { sm: sidebarOpen ? `${drawerWidth}px` : 0 },
          transition: theme => theme.transitions.create(['margin', 'width'], {
            easing: theme.transitions.easing.sharp,
            duration: theme.transitions.duration.leavingScreen,
          }),
        }}
      >
        <Toolbar>
          {/* Mobile menu button */}
          <IconButton
            color="inherit"
            aria-label="toggle mobile menu"
            edge="start"
            onClick={handleDrawerToggle}
            sx={{ mr: 2, display: { sm: 'none' } }}
          >
            <MenuIcon />
          </IconButton>
          
          {/* Desktop sidebar toggle button */}
          <IconButton
            color="inherit"
            aria-label={sidebarOpen ? 'collapse sidebar' : 'expand sidebar'}
            edge="start"
            onClick={handleSidebarToggle}
            sx={{ mr: 2, display: { xs: 'none', sm: 'block' } }}
          >
            {sidebarOpen ? <ChevronLeft /> : <MenuIcon />}
          </IconButton>

          <Typography variant="h6" noWrap component="div" sx={{ flexGrow: 1 }}>
            {currentRoute?.label || 'Dashboard'}
          </Typography>

          <Badge badgeContent={notifications.length} color="error">
            <IconButton color="inherit" aria-label="notifications">
              <NotificationsIcon />
            </IconButton>
          </Badge>
        </Toolbar>
      </AppBar>

      {/* Sidebar */}
      <Box
        component="nav"
        sx={{ width: { sm: sidebarOpen ? drawerWidth : 0 }, flexShrink: { sm: 0 } }}
        aria-label="navigation menu"
      >
        {/* Mobile drawer */}
        <Drawer
          variant="temporary"
          open={mobileOpen}
          onClose={handleDrawerToggle}
          ModalProps={{
            keepMounted: true, // Better open performance on mobile.
          }}
          sx={{
            display: { xs: 'block', sm: 'none' },
            '& .MuiDrawer-paper': {
              boxSizing: 'border-box',
              width: drawerWidth,
            },
          }}
        >
          {drawer}
        </Drawer>
        
        {/* Desktop drawer */}
        <Drawer
          variant="persistent"
          open={sidebarOpen}
          sx={{
            display: { xs: 'none', sm: 'block' },
            '& .MuiDrawer-paper': {
              boxSizing: 'border-box',
              width: drawerWidth,
            },
          }}
        >
          {drawer}
        </Drawer>
      </Box>

      {/* Main content */}
      <Box
        component="main"
        sx={{
          flexGrow: 1,
          p: 3,
          width: { sm: sidebarOpen ? `calc(100% - ${drawerWidth}px)` : '100%' },
          mt: '64px', // AppBar height
          transition: theme => theme.transitions.create(['margin', 'width'], {
            easing: theme.transitions.easing.sharp,
            duration: theme.transitions.duration.enteringScreen,
          }),
        }}
      >
        {/* Status notifications */}
        {Object.entries(moduleStatus).some(([, status]) => !status) && (
          <Alert severity="warning" sx={{ mb: 2 }}>
            Some modules are offline. Check your configuration and ensure all required services are running.
          </Alert>
        )}

        {children}
      </Box>
    </Box>
  );
};

export default AppLayout;