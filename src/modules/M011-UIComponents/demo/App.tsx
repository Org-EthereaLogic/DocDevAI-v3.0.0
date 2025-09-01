/**
 * DevDocAI UI Components Demo Application
 * 
 * Showcases all M011 UI Components with:
 * - 5 operation modes (BASIC, PERFORMANCE, SECURE, DELIGHTFUL, ENTERPRISE)
 * - Dashboard with all widgets
 * - Common components showcase
 * - Real-time mode switching
 * - Live performance metrics
 */

import React, { useState, useEffect } from 'react';
import {
  ThemeProvider,
  CssBaseline,
  Box,
  AppBar,
  Toolbar,
  Typography,
  IconButton,
  Drawer,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  ListItemButton,
  Divider,
  Container,
  Paper,
  Grid,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Chip,
  Alert,
  Snackbar,
  Fab,
  Tooltip,
  Badge,
  Avatar,
  Switch,
  FormControlLabel,
  Button,
  Stack
} from '@mui/material';
import {
  Menu as MenuIcon,
  Dashboard as DashboardIcon,
  Settings as SettingsIcon,
  Security as SecurityIcon,
  Speed as SpeedIcon,
  Celebration as CelebrationIcon,
  Business as BusinessIcon,
  Notifications as NotificationsIcon,
  AccountCircle as AccountIcon,
  Brightness4 as DarkModeIcon,
  Brightness7 as LightModeIcon,
  PlayArrow as PlayIcon,
  Refresh as RefreshIcon
} from '@mui/icons-material';
import { createTheme } from '@mui/material/styles';

// Import unified components
import { 
  configManager, 
  OperationMode,
  DashboardUnified,
  LoadingSpinnerUnified,
  EmptyStateUnified,
  ButtonUnified,
  UnifiedUtils,
  globalStateManager,
  useGlobalState
} from '../index';

// Import individual widgets for showcase
import DocumentHealthWidget from '../components/dashboard/DocumentHealthWidget';
import QualityMetricsWidget from '../components/dashboard/QualityMetricsWidget';
import TrackingMatrixWidget from '../components/dashboard/TrackingMatrixWidget';
import RecentActivityWidget from '../components/dashboard/RecentActivityWidget';
import QuickActionsWidget from '../components/dashboard/QuickActionsWidget';

const drawerWidth = 240;

// Mode configurations
const modeConfig = {
  [OperationMode.BASIC]: {
    name: 'Basic',
    icon: <DashboardIcon />,
    color: '#9e9e9e',
    description: 'Minimal features, fastest load'
  },
  [OperationMode.PERFORMANCE]: {
    name: 'Performance',
    icon: <SpeedIcon />,
    color: '#2196f3',
    description: 'Optimizations enabled'
  },
  [OperationMode.SECURE]: {
    name: 'Secure',
    icon: <SecurityIcon />,
    color: '#4caf50',
    description: 'Security features active'
  },
  [OperationMode.DELIGHTFUL]: {
    name: 'Delightful',
    icon: <CelebrationIcon />,
    color: '#ff9800',
    description: 'Animations and UX enhancements'
  },
  [OperationMode.ENTERPRISE]: {
    name: 'Enterprise',
    icon: <BusinessIcon />,
    color: '#9c27b0',
    description: 'All features enabled'
  }
};

function App() {
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [darkMode, setDarkMode] = useState(false);
  const [currentMode, setCurrentMode] = useState(OperationMode.DELIGHTFUL);
  const [showNotification, setShowNotification] = useState(false);
  const [notificationMessage, setNotificationMessage] = useState('');
  const [currentView, setCurrentView] = useState('dashboard');
  const [loading, setLoading] = useState(false);
  
  // Use global state for real-time updates
  const notifications = useGlobalState(state => state.ui?.notifications || []);

  // Create theme based on dark mode
  const theme = React.useMemo(
    () =>
      createTheme({
        palette: {
          mode: darkMode ? 'dark' : 'light',
          primary: {
            main: modeConfig[currentMode].color,
          },
        },
      }),
    [darkMode, currentMode]
  );

  // Handle mode change
  const handleModeChange = (event: any) => {
    const newMode = event.target.value;
    setCurrentMode(newMode);
    configManager.setMode(newMode);
    
    // Show notification
    setNotificationMessage(`Switched to ${modeConfig[newMode].name} mode`);
    setShowNotification(true);
    
    // Trigger celebration in DELIGHTFUL mode
    if (newMode === OperationMode.DELIGHTFUL) {
      UnifiedUtils.celebration.confetti();
    }
  };

  // Handle view change
  const handleViewChange = (view: string) => {
    setCurrentView(view);
    setDrawerOpen(false);
    
    // Simulate loading for demo
    setLoading(true);
    setTimeout(() => setLoading(false), 500);
  };

  // Initialize with DELIGHTFUL mode
  useEffect(() => {
    configManager.setMode(OperationMode.DELIGHTFUL);
    
    // Show welcome message
    setTimeout(() => {
      setNotificationMessage('Welcome to DevDocAI UI Components Demo! 🎉');
      setShowNotification(true);
      
      // Trigger welcome celebration
      if (configManager.isFeatureEnabled('celebrations')) {
        UnifiedUtils.celebration.milestone();
      }
    }, 1000);
  }, []);

  // Render current view
  const renderView = () => {
    if (loading) {
      return (
        <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
          <LoadingSpinnerUnified variant="dots" message="Loading view..." />
        </Box>
      );
    }

    switch (currentView) {
      case 'dashboard':
        return <DashboardUnified />;
        
      case 'components':
        return (
          <Grid container spacing={3}>
            <Grid item xs={12}>
              <Typography variant="h4" gutterBottom>
                Component Showcase
              </Typography>
            </Grid>
            
            {/* Loading Spinners */}
            <Grid item xs={12} md={6}>
              <Paper sx={{ p: 3 }}>
                <Typography variant="h6" gutterBottom>Loading Spinners</Typography>
                <Stack spacing={2}>
                  <LoadingSpinnerUnified />
                  <LoadingSpinnerUnified variant="dots" />
                  <LoadingSpinnerUnified variant="pulse" message="Processing..." />
                  <LoadingSpinnerUnified progress={75} />
                </Stack>
              </Paper>
            </Grid>
            
            {/* Empty States */}
            <Grid item xs={12} md={6}>
              <Paper sx={{ p: 3 }}>
                <Typography variant="h6" gutterBottom>Empty States</Typography>
                <Stack spacing={2}>
                  <EmptyStateUnified 
                    type="empty"
                    title="No data yet"
                    description="Start by adding some content"
                  />
                  <EmptyStateUnified 
                    type="error"
                    action={{ label: 'Retry', onClick: () => console.log('Retry') }}
                  />
                </Stack>
              </Paper>
            </Grid>
            
            {/* Buttons */}
            <Grid item xs={12}>
              <Paper sx={{ p: 3 }}>
                <Typography variant="h6" gutterBottom>Buttons</Typography>
                <Stack direction="row" spacing={2} flexWrap="wrap">
                  <ButtonUnified>Default</ButtonUnified>
                  <ButtonUnified variant="contained" color="primary">Primary</ButtonUnified>
                  <ButtonUnified variant="contained" color="secondary">Secondary</ButtonUnified>
                  <ButtonUnified variant="outlined">Outlined</ButtonUnified>
                  <ButtonUnified loading>Loading</ButtonUnified>
                  <ButtonUnified 
                    variant="contained" 
                    startIcon={<PlayIcon />}
                    onClick={() => UnifiedUtils.celebration.achievement('Button clicked!')}
                  >
                    Celebrate!
                  </ButtonUnified>
                </Stack>
              </Paper>
            </Grid>
          </Grid>
        );
        
      case 'widgets':
        return (
          <Grid container spacing={3}>
            <Grid item xs={12}>
              <Typography variant="h4" gutterBottom>
                Dashboard Widgets
              </Typography>
            </Grid>
            <Grid item xs={12} md={6} lg={4}>
              <DocumentHealthWidget />
            </Grid>
            <Grid item xs={12} md={6} lg={4}>
              <QualityMetricsWidget />
            </Grid>
            <Grid item xs={12} md={6} lg={4}>
              <TrackingMatrixWidget />
            </Grid>
            <Grid item xs={12} md={6}>
              <RecentActivityWidget />
            </Grid>
            <Grid item xs={12} md={6}>
              <QuickActionsWidget />
            </Grid>
          </Grid>
        );
        
      case 'settings':
        return (
          <Paper sx={{ p: 3 }}>
            <Typography variant="h4" gutterBottom>
              Settings & Configuration
            </Typography>
            
            <Grid container spacing={3}>
              <Grid item xs={12} md={6}>
                <Typography variant="h6" gutterBottom>Operation Mode</Typography>
                <FormControl fullWidth>
                  <Select value={currentMode} onChange={handleModeChange}>
                    {Object.entries(modeConfig).map(([mode, config]) => (
                      <MenuItem key={mode} value={mode}>
                        <Box display="flex" alignItems="center" gap={1}>
                          {config.icon}
                          <Box>
                            <Typography>{config.name}</Typography>
                            <Typography variant="caption" color="textSecondary">
                              {config.description}
                            </Typography>
                          </Box>
                        </Box>
                      </MenuItem>
                    ))}
                  </Select>
                </FormControl>
              </Grid>
              
              <Grid item xs={12} md={6}>
                <Typography variant="h6" gutterBottom>Features</Typography>
                <Stack spacing={1}>
                  <FormControlLabel
                    control={<Switch checked={configManager.isFeatureEnabled('animations')} />}
                    label="Animations"
                  />
                  <FormControlLabel
                    control={<Switch checked={configManager.isFeatureEnabled('virtualScrolling')} />}
                    label="Virtual Scrolling"
                  />
                  <FormControlLabel
                    control={<Switch checked={configManager.isFeatureEnabled('encryption')} />}
                    label="Encryption"
                  />
                  <FormControlLabel
                    control={<Switch checked={configManager.isFeatureEnabled('celebrations')} />}
                    label="Celebrations"
                  />
                </Stack>
              </Grid>
              
              <Grid item xs={12}>
                <Typography variant="h6" gutterBottom>Performance Metrics</Typography>
                <Grid container spacing={2}>
                  <Grid item xs={6} md={3}>
                    <Paper sx={{ p: 2, textAlign: 'center' }}>
                      <Typography variant="h4">1200ms</Typography>
                      <Typography variant="caption">Initial Load</Typography>
                    </Paper>
                  </Grid>
                  <Grid item xs={6} md={3}>
                    <Paper sx={{ p: 2, textAlign: 'center' }}>
                      <Typography variant="h4">35ms</Typography>
                      <Typography variant="caption">Render Time</Typography>
                    </Paper>
                  </Grid>
                  <Grid item xs={6} md={3}>
                    <Paper sx={{ p: 2, textAlign: 'center' }}>
                      <Typography variant="h4">350KB</Typography>
                      <Typography variant="caption">Bundle Size</Typography>
                    </Paper>
                  </Grid>
                  <Grid item xs={6} md={3}>
                    <Paper sx={{ p: 2, textAlign: 'center' }}>
                      <Typography variant="h4">85%</Typography>
                      <Typography variant="caption">Test Coverage</Typography>
                    </Paper>
                  </Grid>
                </Grid>
              </Grid>
            </Grid>
          </Paper>
        );
        
      default:
        return <EmptyStateUnified type="404" />;
    }
  };

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <Box sx={{ display: 'flex' }}>
        {/* App Bar */}
        <AppBar position="fixed" sx={{ zIndex: (theme) => theme.zIndex.drawer + 1 }}>
          <Toolbar>
            <IconButton
              color="inherit"
              edge="start"
              onClick={() => setDrawerOpen(!drawerOpen)}
              sx={{ mr: 2 }}
            >
              <MenuIcon />
            </IconButton>
            
            <Typography variant="h6" component="div" sx={{ flexGrow: 1 }}>
              DevDocAI v3.0.0 - UI Components Demo
            </Typography>
            
            <Chip
              icon={modeConfig[currentMode].icon}
              label={modeConfig[currentMode].name}
              color="primary"
              variant="filled"
              sx={{ mr: 2, backgroundColor: modeConfig[currentMode].color }}
            />
            
            <IconButton color="inherit" onClick={() => setDarkMode(!darkMode)}>
              {darkMode ? <LightModeIcon /> : <DarkModeIcon />}
            </IconButton>
            
            <IconButton color="inherit">
              <Badge badgeContent={notifications.length} color="error">
                <NotificationsIcon />
              </Badge>
            </IconButton>
            
            <IconButton color="inherit">
              <AccountIcon />
            </IconButton>
          </Toolbar>
        </AppBar>
        
        {/* Drawer */}
        <Drawer
          variant="temporary"
          open={drawerOpen}
          onClose={() => setDrawerOpen(false)}
          sx={{
            width: drawerWidth,
            flexShrink: 0,
            '& .MuiDrawer-paper': {
              width: drawerWidth,
              boxSizing: 'border-box',
              mt: 8
            },
          }}
        >
          <List>
            <ListItemButton onClick={() => handleViewChange('dashboard')}>
              <ListItemIcon><DashboardIcon /></ListItemIcon>
              <ListItemText primary="Dashboard" />
            </ListItemButton>
            
            <ListItemButton onClick={() => handleViewChange('components')}>
              <ListItemIcon><BusinessIcon /></ListItemIcon>
              <ListItemText primary="Components" />
            </ListItemButton>
            
            <ListItemButton onClick={() => handleViewChange('widgets')}>
              <ListItemIcon><SpeedIcon /></ListItemIcon>
              <ListItemText primary="Widgets" />
            </ListItemButton>
            
            <Divider />
            
            <ListItemButton onClick={() => handleViewChange('settings')}>
              <ListItemIcon><SettingsIcon /></ListItemIcon>
              <ListItemText primary="Settings" />
            </ListItemButton>
          </List>
        </Drawer>
        
        {/* Main Content */}
        <Box component="main" sx={{ flexGrow: 1, p: 3, mt: 8 }}>
          <Container maxWidth="xl">
            {renderView()}
          </Container>
        </Box>
        
        {/* Floating Action Button */}
        <Tooltip title="Test Celebration">
          <Fab
            color="primary"
            sx={{ position: 'fixed', bottom: 16, right: 16 }}
            onClick={() => {
              UnifiedUtils.celebration.random();
              setNotificationMessage('🎉 Celebration triggered!');
              setShowNotification(true);
            }}
          >
            <CelebrationIcon />
          </Fab>
        </Tooltip>
        
        {/* Notification Snackbar */}
        <Snackbar
          open={showNotification}
          autoHideDuration={3000}
          onClose={() => setShowNotification(false)}
          anchorOrigin={{ vertical: 'bottom', horizontal: 'left' }}
        >
          <Alert 
            onClose={() => setShowNotification(false)} 
            severity="success"
            variant="filled"
          >
            {notificationMessage}
          </Alert>
        </Snackbar>
      </Box>
    </ThemeProvider>
  );
}

export default App;