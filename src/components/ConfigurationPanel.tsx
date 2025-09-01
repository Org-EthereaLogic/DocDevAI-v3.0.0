/**
 * DevDocAI v3.0.0 - Configuration Panel Component
 * 
 * Interface for M001 Configuration Manager module
 * Provides application settings, preferences, and module configuration.
 */

import React, { useState, useEffect } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Button,
  TextField,
  Grid,
  Switch,
  FormControl,
  FormControlLabel,
  InputLabel,
  Select,
  MenuItem,
  Alert,
  Divider,
  Tabs,
  Tab,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  ListItemSecondaryAction,
  Paper,
  Chip,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
} from '@mui/material';
import {
  Settings as SettingsIcon,
  Security as SecurityIcon,
  Speed as PerformanceIcon,
  Palette as ThemeIcon,
  Storage as StorageIcon,
  Language as LanguageIcon,
  Notifications as NotificationIcon,
  Api as ApiIcon,
  Save as SaveIcon,
  Refresh as ResetIcon,
  ExpandMore as ExpandMoreIcon,
  CheckCircle as SuccessIcon,
  Warning as WarningIcon,
  Info as InfoIcon,
} from '@mui/icons-material';

interface ConfigurationOption {
  key: string;
  label: string;
  description: string;
  type: 'boolean' | 'string' | 'number' | 'select';
  value: any;
  options?: string[];
  category: string;
  required?: boolean;
}

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

const TabPanel = ({ children, value, index, ...other }: TabPanelProps) => {
  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`config-tabpanel-${index}`}
      aria-labelledby={`config-tab-${index}`}
      {...other}
    >
      {value === index && <Box sx={{ py: 3 }}>{children}</Box>}
    </div>
  );
};

const ConfigurationPanel: React.FC = () => {
  const [currentTab, setCurrentTab] = useState(0);
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false);
  const [resetDialog, setResetDialog] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);
  
  const [configurations, setConfigurations] = useState<ConfigurationOption[]>([
    // General Settings
    {
      key: 'app.theme',
      label: 'Application Theme',
      description: 'Choose between light and dark themes',
      type: 'select',
      value: 'light',
      options: ['light', 'dark', 'auto'],
      category: 'general',
    },
    {
      key: 'app.language',
      label: 'Language',
      description: 'Application display language',
      type: 'select',
      value: 'en',
      options: ['en', 'es', 'fr', 'de', 'ja'],
      category: 'general',
    },
    {
      key: 'app.autoSave',
      label: 'Auto Save',
      description: 'Automatically save changes',
      type: 'boolean',
      value: true,
      category: 'general',
    },
    
    // Performance Settings
    {
      key: 'performance.memoryMode',
      label: 'Memory Mode',
      description: 'Optimize for memory usage vs performance',
      type: 'select',
      value: 'standard',
      options: ['baseline', 'standard', 'enhanced', 'performance'],
      category: 'performance',
    },
    {
      key: 'performance.cacheSize',
      label: 'Cache Size (MB)',
      description: 'Maximum cache size in megabytes',
      type: 'number',
      value: 100,
      category: 'performance',
    },
    {
      key: 'performance.enableBatching',
      label: 'Enable Batch Processing',
      description: 'Process multiple documents in batches',
      type: 'boolean',
      value: true,
      category: 'performance',
    },

    // Security Settings
    {
      key: 'security.encryptionEnabled',
      label: 'Enable Encryption',
      description: 'Encrypt sensitive data at rest',
      type: 'boolean',
      value: true,
      category: 'security',
      required: true,
    },
    {
      key: 'security.sessionTimeout',
      label: 'Session Timeout (minutes)',
      description: 'Auto-logout after inactivity',
      type: 'number',
      value: 30,
      category: 'security',
    },
    {
      key: 'security.auditLogging',
      label: 'Audit Logging',
      description: 'Log all user actions for security',
      type: 'boolean',
      value: true,
      category: 'security',
    },

    // API Settings
    {
      key: 'api.openaiEnabled',
      label: 'OpenAI Integration',
      description: 'Enable OpenAI API for document generation',
      type: 'boolean',
      value: false,
      category: 'api',
    },
    {
      key: 'api.anthropicEnabled',
      label: 'Anthropic Integration',
      description: 'Enable Anthropic API for document analysis',
      type: 'boolean',
      value: false,
      category: 'api',
    },
    {
      key: 'api.rateLimit',
      label: 'API Rate Limit (requests/minute)',
      description: 'Maximum API requests per minute',
      type: 'number',
      value: 60,
      category: 'api',
    },

    // Storage Settings
    {
      key: 'storage.localPath',
      label: 'Local Storage Path',
      description: 'Directory for local document storage',
      type: 'string',
      value: './devdocai-data',
      category: 'storage',
    },
    {
      key: 'storage.backupEnabled',
      label: 'Automatic Backups',
      description: 'Create periodic backups of data',
      type: 'boolean',
      value: true,
      category: 'storage',
    },
    {
      key: 'storage.retentionDays',
      label: 'Data Retention (days)',
      description: 'Keep data for specified number of days',
      type: 'number',
      value: 365,
      category: 'storage',
    },

    // Notification Settings
    {
      key: 'notifications.enabled',
      label: 'Enable Notifications',
      description: 'Show system notifications',
      type: 'boolean',
      value: true,
      category: 'notifications',
    },
    {
      key: 'notifications.emailAlerts',
      label: 'Email Alerts',
      description: 'Send email notifications for important events',
      type: 'boolean',
      value: false,
      category: 'notifications',
    },
  ]);

  const categories = [
    { id: 'general', label: 'General', icon: SettingsIcon },
    { id: 'performance', label: 'Performance', icon: PerformanceIcon },
    { id: 'security', label: 'Security', icon: SecurityIcon },
    { id: 'api', label: 'API Keys', icon: ApiIcon },
    { id: 'storage', label: 'Storage', icon: StorageIcon },
    { id: 'notifications', label: 'Notifications', icon: NotificationIcon },
  ];

  const handleConfigChange = (key: string, value: any) => {
    setConfigurations(prev => prev.map(config =>
      config.key === key ? { ...config, value } : config
    ));
    setHasUnsavedChanges(true);
  };

  const handleSave = async () => {
    try {
      // Simulate saving configuration
      await new Promise(resolve => setTimeout(resolve, 1000));
      setHasUnsavedChanges(false);
      setSaveSuccess(true);
      setTimeout(() => setSaveSuccess(false), 3000);
    } catch (error) {
      console.error('Failed to save configuration:', error);
    }
  };

  const handleReset = () => {
    // Reset to default values (simulated)
    setConfigurations(prev => prev.map(config => ({
      ...config,
      value: getDefaultValue(config.key),
    })));
    setHasUnsavedChanges(true);
    setResetDialog(false);
  };

  const getDefaultValue = (key: string) => {
    // Default values for reset functionality
    const defaults: Record<string, any> = {
      'app.theme': 'light',
      'app.language': 'en',
      'app.autoSave': true,
      'performance.memoryMode': 'standard',
      'performance.cacheSize': 100,
      'performance.enableBatching': true,
      'security.encryptionEnabled': true,
      'security.sessionTimeout': 30,
      'security.auditLogging': true,
      'api.openaiEnabled': false,
      'api.anthropicEnabled': false,
      'api.rateLimit': 60,
      'storage.localPath': './devdocai-data',
      'storage.backupEnabled': true,
      'storage.retentionDays': 365,
      'notifications.enabled': true,
      'notifications.emailAlerts': false,
    };
    return defaults[key] || '';
  };

  const handleTabChange = (event: React.SyntheticEvent, newValue: number) => {
    setCurrentTab(newValue);
  };

  const renderConfigOption = (config: ConfigurationOption) => {
    switch (config.type) {
      case 'boolean':
        return (
          <FormControlLabel
            control={
              <Switch
                checked={config.value}
                onChange={(e) => handleConfigChange(config.key, e.target.checked)}
              />
            }
            label=""
          />
        );
      case 'select':
        return (
          <FormControl size="small" sx={{ minWidth: 120 }}>
            <Select
              value={config.value}
              onChange={(e) => handleConfigChange(config.key, e.target.value)}
            >
              {config.options?.map((option) => (
                <MenuItem key={option} value={option}>
                  {option.charAt(0).toUpperCase() + option.slice(1)}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
        );
      case 'number':
        return (
          <TextField
            type="number"
            value={config.value}
            onChange={(e) => handleConfigChange(config.key, parseInt(e.target.value) || 0)}
            size="small"
            sx={{ width: 120 }}
          />
        );
      case 'string':
        return (
          <TextField
            value={config.value}
            onChange={(e) => handleConfigChange(config.key, e.target.value)}
            size="small"
            sx={{ minWidth: 200 }}
          />
        );
      default:
        return null;
    }
  };

  const getCategoryIcon = (categoryId: string) => {
    const category = categories.find(cat => cat.id === categoryId);
    if (!category) return <SettingsIcon />;
    const Icon = category.icon;
    return <Icon />;
  };

  return (
    <Box sx={{ maxWidth: 1200, mx: 'auto' }}>
      <Typography variant="h4" component="h1" gutterBottom>
        Configuration Panel
      </Typography>
      <Typography variant="body1" color="text.secondary" sx={{ mb: 4 }}>
        Manage application settings, security preferences, and module configurations.
      </Typography>

      {/* Save Banner */}
      {hasUnsavedChanges && (
        <Alert 
          severity="warning" 
          sx={{ mb: 3 }}
          action={
            <Box sx={{ display: 'flex', gap: 1 }}>
              <Button color="inherit" size="small" onClick={handleSave}>
                Save Changes
              </Button>
              <Button color="inherit" size="small" onClick={() => window.location.reload()}>
                Discard
              </Button>
            </Box>
          }
        >
          You have unsaved changes. Don't forget to save your configuration.
        </Alert>
      )}

      {saveSuccess && (
        <Alert severity="success" sx={{ mb: 3 }}>
          Configuration saved successfully!
        </Alert>
      )}

      <Card>
        <CardContent>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
            <Tabs value={currentTab} onChange={handleTabChange}>
              {categories.map((category, index) => {
                const Icon = category.icon;
                return (
                  <Tab
                    key={category.id}
                    label={category.label}
                    icon={<Icon fontSize="small" />}
                    iconPosition="start"
                  />
                );
              })}
            </Tabs>
            <Box sx={{ display: 'flex', gap: 1 }}>
              <Button
                startIcon={<ResetIcon />}
                onClick={() => setResetDialog(true)}
                variant="outlined"
                size="small"
              >
                Reset to Defaults
              </Button>
              <Button
                startIcon={<SaveIcon />}
                onClick={handleSave}
                variant="contained"
                disabled={!hasUnsavedChanges}
                size="small"
              >
                Save Changes
              </Button>
            </Box>
          </Box>

          {categories.map((category, index) => (
            <TabPanel key={category.id} value={currentTab} index={index}>
              <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                {configurations
                  .filter(config => config.category === category.id)
                  .map((config) => (
                    <Card key={config.key} variant="outlined">
                      <CardContent>
                        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                          <Box sx={{ flexGrow: 1 }}>
                            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 0.5 }}>
                              <Typography variant="subtitle1">
                                {config.label}
                              </Typography>
                              {config.required && (
                                <Chip label="Required" size="small" color="error" variant="outlined" />
                              )}
                            </Box>
                            <Typography variant="body2" color="text.secondary">
                              {config.description}
                            </Typography>
                          </Box>
                          <Box sx={{ ml: 2 }}>
                            {renderConfigOption(config)}
                          </Box>
                        </Box>
                      </CardContent>
                    </Card>
                  ))}

                {/* Category-specific additional content */}
                {category.id === 'api' && (
                  <Alert severity="info">
                    <Typography variant="body2">
                      API keys are encrypted and stored securely. Configure your API credentials in the environment file.
                    </Typography>
                  </Alert>
                )}

                {category.id === 'security' && (
                  <Alert severity="warning">
                    <Typography variant="body2">
                      Security settings affect all modules. Changes require application restart to take effect.
                    </Typography>
                  </Alert>
                )}

                {category.id === 'performance' && (
                  <Paper sx={{ p: 2, backgroundColor: 'grey.50' }}>
                    <Typography variant="subtitle2" gutterBottom>
                      Performance Tips
                    </Typography>
                    <List dense>
                      <ListItem>
                        <ListItemText
                          primary="Memory Mode"
                          secondary="Higher modes use more RAM but provide better performance"
                        />
                      </ListItem>
                      <ListItem>
                        <ListItemText
                          primary="Cache Size"
                          secondary="Larger cache improves response times but uses more memory"
                        />
                      </ListItem>
                    </List>
                  </Paper>
                )}
              </Box>
            </TabPanel>
          ))}
        </CardContent>
      </Card>

      {/* Reset Confirmation Dialog */}
      <Dialog open={resetDialog} onClose={() => setResetDialog(false)}>
        <DialogTitle>Reset Configuration</DialogTitle>
        <DialogContent>
          <Typography>
            Are you sure you want to reset all settings to their default values? This action cannot be undone.
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setResetDialog(false)}>Cancel</Button>
          <Button onClick={handleReset} color="error" variant="contained">
            Reset to Defaults
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default ConfigurationPanel;