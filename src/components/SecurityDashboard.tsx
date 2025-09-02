/**
 * DevDocAI v3.0.0 - Security Dashboard Component
 * 
 * Interface for M010 Security Module
 * Provides security monitoring, threat detection, and compliance reporting.
 */

import React, { useState, useEffect } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Grid,
  Alert,
  Chip,
  LinearProgress,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  Paper,
  IconButton,
  Button,
  Divider,
  CircularProgress,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Badge,
} from '@mui/material';
import {
  Security as SecurityIcon,
  Warning as WarningIcon,
  Error as ErrorIcon,
  CheckCircle as SuccessIcon,
  Shield as ShieldIcon,
  BugReport as VulnerabilityIcon,
  Verified as ComplianceIcon,
  Refresh as RefreshIcon,
  GetApp as ExportIcon,
  ExpandMore as ExpandMoreIcon,
  Info as InfoIcon,
  Timeline as TrendIcon,
} from '@mui/icons-material';

interface SecurityMetric {
  name: string;
  value: number;
  maxValue: number;
  status: 'good' | 'warning' | 'critical';
  trend: 'up' | 'down' | 'stable';
}

interface SecurityAlert {
  id: string;
  type: 'vulnerability' | 'threat' | 'compliance' | 'pii';
  severity: 'low' | 'medium' | 'high' | 'critical';
  title: string;
  description: string;
  timestamp: Date;
  resolved: boolean;
}

interface ComplianceStatus {
  framework: string;
  score: number;
  requirements: number;
  passed: number;
  failed: number;
}

const SecurityDashboard: React.FC = () => {
  const [securityMetrics, setSecurityMetrics] = useState<SecurityMetric[]>([
    { name: 'Overall Security Score', value: 85, maxValue: 100, status: 'good', trend: 'up' },
    { name: 'Vulnerability Score', value: 92, maxValue: 100, status: 'good', trend: 'stable' },
    { name: 'Compliance Score', value: 78, maxValue: 100, status: 'warning', trend: 'up' },
    { name: 'PII Protection', value: 95, maxValue: 100, status: 'good', trend: 'stable' },
  ]);

  const [alerts, setAlerts] = useState<SecurityAlert[]>([
    {
      id: '1',
      type: 'vulnerability',
      severity: 'medium',
      title: 'Outdated dependency detected',
      description: 'Package "example-lib" has known vulnerabilities',
      timestamp: new Date(Date.now() - 3600000),
      resolved: false,
    },
    {
      id: '2',
      type: 'pii',
      severity: 'high',
      title: 'PII detected in documentation',
      description: 'Email addresses found in API documentation',
      timestamp: new Date(Date.now() - 7200000),
      resolved: false,
    },
    {
      id: '3',
      type: 'compliance',
      severity: 'low',
      title: 'GDPR compliance check',
      description: 'Data retention policy needs review',
      timestamp: new Date(Date.now() - 86400000),
      resolved: true,
    },
  ]);

  const [complianceStatus, setComplianceStatus] = useState<ComplianceStatus[]>([
    { framework: 'GDPR', score: 85, requirements: 20, passed: 17, failed: 3 },
    { framework: 'OWASP Top 10', score: 90, requirements: 10, passed: 9, failed: 1 },
    { framework: 'SOC 2', score: 75, requirements: 15, passed: 11, failed: 4 },
    { framework: 'ISO 27001', score: 70, requirements: 25, passed: 17, failed: 8 },
  ]);

  const [isScanning, setIsScanning] = useState(false);
  const [expandedPanel, setExpandedPanel] = useState<string | false>(false);

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'critical': return 'error';
      case 'high': return 'error';
      case 'medium': return 'warning';
      case 'low': return 'info';
      default: return 'default';
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'good': return 'success';
      case 'warning': return 'warning';
      case 'critical': return 'error';
      default: return 'inherit';
    }
  };

  const getAlertIcon = (type: string) => {
    switch (type) {
      case 'vulnerability': return <VulnerabilityIcon />;
      case 'threat': return <ErrorIcon />;
      case 'compliance': return <ComplianceIcon />;
      case 'pii': return <InfoIcon />;
      default: return <WarningIcon />;
    }
  };

  const handleRunScan = async () => {
    setIsScanning(true);
    // Simulate security scan
    setTimeout(() => {
      setIsScanning(false);
      // Update metrics with new random values
      setSecurityMetrics(prev => prev.map(metric => ({
        ...metric,
        value: Math.max(60, Math.min(100, metric.value + (Math.random() - 0.5) * 10))
      })));
    }, 3000);
  };

  const handleAccordionChange = (panel: string) => (event: React.SyntheticEvent, isExpanded: boolean) => {
    setExpandedPanel(isExpanded ? panel : false);
  };

  const unresolvedAlerts = alerts.filter(alert => !alert.resolved);
  const criticalAlerts = unresolvedAlerts.filter(alert => alert.severity === 'critical' || alert.severity === 'high');

  return (
    <Box sx={{ maxWidth: 1200, mx: 'auto' }}>
      <Typography variant="h4" component="h1" gutterBottom>
        Security Dashboard
      </Typography>
      <Typography variant="body1" color="text.secondary" sx={{ mb: 4 }}>
        Monitor security status, detect threats, and ensure compliance across all documentation.
      </Typography>

      {/* Security Overview */}
      <Grid container spacing={3} sx={{ mb: 3 }}>
        {securityMetrics.map((metric) => (
          <Grid item xs={12} sm={6} md={3} key={metric.name}>
            <Card>
              <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                  <SecurityIcon color="primary" sx={{ mr: 1 }} />
                  <Typography variant="h6" component="div">
                    {metric.value}
                  </Typography>
                  <Typography variant="body2" color="text.secondary" sx={{ ml: 0.5 }}>
                    /{metric.maxValue}
                  </Typography>
                </Box>
                <Typography variant="body2" color="text.secondary" gutterBottom>
                  {metric.name}
                </Typography>
                <LinearProgress
                  variant="determinate"
                  value={(metric.value / metric.maxValue) * 100}
                  color={getStatusColor(metric.status)}
                  sx={{ height: 6, borderRadius: 3 }}
                />
                <Box sx={{ display: 'flex', justifyContent: 'space-between', mt: 1 }}>
                  <Chip
                    label={metric.status}
                    size="small"
                    color={getStatusColor(metric.status)}
                    variant="outlined"
                  />
                  <Box sx={{ display: 'flex', alignItems: 'center' }}>
                    <TrendIcon fontSize="small" color="action" />
                    <Typography variant="caption" sx={{ ml: 0.5 }}>
                      {metric.trend}
                    </Typography>
                  </Box>
                </Box>
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>

      <Grid container spacing={3}>
        {/* Security Alerts */}
        <Grid item xs={12} md={8}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                <Typography variant="h6">Security Alerts</Typography>
                <Box sx={{ display: 'flex', gap: 1 }}>
                  <Button
                    startIcon={<RefreshIcon />}
                    onClick={handleRunScan}
                    disabled={isScanning}
                    variant="outlined"
                    size="small"
                  >
                    {isScanning ? 'Scanning...' : 'Run Scan'}
                  </Button>
                  <IconButton size="small">
                    <ExportIcon />
                  </IconButton>
                </Box>
              </Box>

              {isScanning && (
                <Box sx={{ mb: 2 }}>
                  <LinearProgress />
                  <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                    Running comprehensive security scan...
                  </Typography>
                </Box>
              )}

              {criticalAlerts.length > 0 && (
                <Alert severity="error" sx={{ mb: 2 }}>
                  {criticalAlerts.length} critical security issue{criticalAlerts.length > 1 ? 's' : ''} require immediate attention.
                </Alert>
              )}

              <List>
                {alerts.map((alert) => (
                  <React.Fragment key={alert.id}>
                    <ListItem
                      sx={{
                        opacity: alert.resolved ? 0.7 : 1,
                        backgroundColor: alert.resolved ? 'transparent' : 'background.paper',
                      }}
                    >
                      <ListItemIcon>
                        <Badge
                          color={getSeverityColor(alert.severity)}
                          variant="dot"
                          invisible={alert.resolved}
                        >
                          {getAlertIcon(alert.type)}
                        </Badge>
                      </ListItemIcon>
                      <ListItemText
                        primary={
                          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                            <Typography variant="body1">
                              {alert.title}
                            </Typography>
                            <Chip
                              label={alert.severity}
                              size="small"
                              color={getSeverityColor(alert.severity)}
                              variant="outlined"
                            />
                            {alert.resolved && (
                              <Chip label="Resolved" size="small" color="success" variant="outlined" />
                            )}
                          </Box>
                        }
                        secondary={
                          <Box>
                            <Typography variant="body2" color="text.secondary">
                              {alert.description}
                            </Typography>
                            <Typography variant="caption" color="text.secondary">
                              {alert.timestamp.toLocaleString()}
                            </Typography>
                          </Box>
                        }
                      />
                    </ListItem>
                    <Divider component="li" />
                  </React.Fragment>
                ))}
              </List>

              {alerts.length === 0 && (
                <Box sx={{ textAlign: 'center', py: 4 }}>
                  <SuccessIcon color="success" sx={{ fontSize: 48, mb: 2 }} />
                  <Typography variant="h6" color="success.main">
                    No Security Alerts
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Your system is secure and no issues were detected.
                  </Typography>
                </Box>
              )}
            </CardContent>
          </Card>
        </Grid>

        {/* Compliance Status */}
        <Grid item xs={12} md={4}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Compliance Status
              </Typography>
              
              <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                {complianceStatus.map((compliance, index) => (
                  <Accordion
                    key={compliance.framework}
                    expanded={expandedPanel === `compliance-${index}`}
                    onChange={handleAccordionChange(`compliance-${index}`)}
                  >
                    <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, width: '100%' }}>
                        <ComplianceIcon fontSize="small" />
                        <Box sx={{ flexGrow: 1 }}>
                          <Typography variant="body2">
                            {compliance.framework}
                          </Typography>
                          <LinearProgress
                            variant="determinate"
                            value={compliance.score}
                            sx={{ height: 4, borderRadius: 2, mt: 0.5 }}
                          />
                        </Box>
                        <Typography variant="body2" fontWeight="bold">
                          {compliance.score}%
                        </Typography>
                      </Box>
                    </AccordionSummary>
                    <AccordionDetails>
                      <Grid container spacing={2}>
                        <Grid item xs={6}>
                          <Paper sx={{ p: 1, textAlign: 'center', backgroundColor: 'success.light' }}>
                            <Typography variant="h6" color="success.contrastText">
                              {compliance.passed}
                            </Typography>
                            <Typography variant="caption" color="success.contrastText">
                              Passed
                            </Typography>
                          </Paper>
                        </Grid>
                        <Grid item xs={6}>
                          <Paper sx={{ p: 1, textAlign: 'center', backgroundColor: 'error.light' }}>
                            <Typography variant="h6" color="error.contrastText">
                              {compliance.failed}
                            </Typography>
                            <Typography variant="caption" color="error.contrastText">
                              Failed
                            </Typography>
                          </Paper>
                        </Grid>
                      </Grid>
                    </AccordionDetails>
                  </Accordion>
                ))}
              </Box>
            </CardContent>
          </Card>

          {/* Quick Actions */}
          <Card sx={{ mt: 2 }}>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Security Actions
              </Typography>
              <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
                <Button
                  variant="outlined"
                  startIcon={<VulnerabilityIcon />}
                  fullWidth
                  size="small"
                >
                  Vulnerability Scan
                </Button>
                <Button
                  variant="outlined"
                  startIcon={<InfoIcon />}
                  fullWidth
                  size="small"
                >
                  PII Detection
                </Button>
                <Button
                  variant="outlined"
                  startIcon={<ComplianceIcon />}
                  fullWidth
                  size="small"
                >
                  Compliance Check
                </Button>
                <Button
                  variant="outlined"
                  startIcon={<ShieldIcon />}
                  fullWidth
                  size="small"
                >
                  Threat Assessment
                </Button>
              </Box>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
};

export default SecurityDashboard;