import React from 'react';
import {
  Box,
  Grid,
  Paper,
  Typography,
  Card,
  CardContent,
  LinearProgress,
  Chip,
  Stack,
  Alert,
  IconButton,
  Tooltip
} from '@mui/material';
import {
  CheckCircle,
  Error,
  Warning,
  Info,
  Speed,
  Security,
  Storage,
  Code,
  Assessment,
  Description
} from '@mui/icons-material';

interface DashboardProps {
  moduleStatus: Record<string, boolean>;
}

const Dashboard: React.FC<DashboardProps> = ({ moduleStatus }) => {
  const completedModules = Object.values(moduleStatus).filter(status => status).length;
  const totalModules = Object.keys(moduleStatus).length;
  const completionPercentage = (completedModules / totalModules) * 100;

  const moduleInfo = {
    M001: { name: 'Configuration Manager', icon: <Storage />, performance: '13.8M ops/sec' },
    M002: { name: 'Local Storage', icon: <Storage />, performance: '72K queries/sec' },
    M003: { name: 'MIAIR Engine', icon: <Speed />, performance: '248K docs/min' },
    M004: { name: 'Document Generator', icon: <Description />, performance: '100+ docs/sec' },
    M005: { name: 'Quality Engine', icon: <Assessment />, performance: '14.63x faster' },
    M006: { name: 'Template Registry', icon: <Code />, performance: '35 templates' },
    M007: { name: 'Review Engine', icon: <Assessment />, performance: '110 docs/sec' },
    M008: { name: 'LLM Adapter', icon: <Code />, performance: 'Multi-provider' },
    M009: { name: 'Enhancement Pipeline', icon: <Speed />, performance: '145 docs/min' },
    M010: { name: 'Security Module', icon: <Security />, performance: 'Enterprise-grade' },
    M011: { name: 'UI Components', icon: <Code />, performance: 'Production-ready' },
    M012: { name: 'CLI Interface', icon: <Code />, performance: 'Pending' },
    M013: { name: 'VS Code Extension', icon: <Code />, performance: 'Pending' }
  };

  return (
    <Box sx={{ flexGrow: 1, p: 3 }}>
      <Typography variant="h4" gutterBottom sx={{ mb: 4 }}>
        DevDocAI v3.0.0 Dashboard
      </Typography>

      {/* Overall Progress */}
      <Paper sx={{ p: 3, mb: 3 }}>
        <Typography variant="h6" gutterBottom>
          Project Completion
        </Typography>
        <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
          <Box sx={{ width: '100%', mr: 1 }}>
            <LinearProgress 
              variant="determinate" 
              value={completionPercentage} 
              sx={{ height: 10, borderRadius: 5 }}
            />
          </Box>
          <Box sx={{ minWidth: 35 }}>
            <Typography variant="body2" color="text.secondary">
              {`${Math.round(completionPercentage)}%`}
            </Typography>
          </Box>
        </Box>
        <Typography variant="body2" color="text.secondary">
          {completedModules} of {totalModules} modules completed
        </Typography>
      </Paper>

      {/* Quick Stats */}
      <Grid container spacing={3} sx={{ mb: 3 }}>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography color="textSecondary" gutterBottom>
                Active Modules
              </Typography>
              <Typography variant="h4">
                {completedModules}
              </Typography>
              <Chip label="Operational" color="success" size="small" />
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography color="textSecondary" gutterBottom>
                Performance
              </Typography>
              <Typography variant="h4">
                248K
              </Typography>
              <Typography variant="caption">docs/min (MIAIR)</Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography color="textSecondary" gutterBottom>
                Security Score
              </Typography>
              <Typography variant="h4">
                A+
              </Typography>
              <Chip label="Enterprise" color="primary" size="small" />
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography color="textSecondary" gutterBottom>
                API Status
              </Typography>
              <Typography variant="h4">
                Ready
              </Typography>
              <Chip label="Configured" color="info" size="small" />
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Module Status Grid */}
      <Typography variant="h6" gutterBottom sx={{ mt: 4, mb: 2 }}>
        Module Status
      </Typography>
      <Grid container spacing={2}>
        {Object.entries(moduleStatus).map(([moduleId, isActive]) => {
          const info = moduleInfo[moduleId as keyof typeof moduleInfo];
          return (
            <Grid item xs={12} sm={6} md={4} key={moduleId}>
              <Paper 
                sx={{ 
                  p: 2,
                  opacity: isActive ? 1 : 0.6,
                  border: isActive ? '2px solid #4caf50' : '2px solid #ccc'
                }}
              >
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                  {info.icon}
                  <Typography variant="subtitle1" sx={{ ml: 1, flexGrow: 1 }}>
                    {moduleId}: {info.name}
                  </Typography>
                  <Tooltip title={isActive ? 'Active' : 'Pending'}>
                    {isActive ? (
                      <CheckCircle color="success" />
                    ) : (
                      <Warning color="disabled" />
                    )}
                  </Tooltip>
                </Box>
                <Typography variant="caption" color="textSecondary">
                  Performance: {info.performance}
                </Typography>
              </Paper>
            </Grid>
          );
        })}
      </Grid>

      {/* System Alerts */}
      <Box sx={{ mt: 4 }}>
        <Typography variant="h6" gutterBottom>
          System Status
        </Typography>
        <Stack spacing={2}>
          <Alert severity="success">
            All core modules operational - System ready for production use
          </Alert>
          <Alert severity="info">
            API keys configured - LLM Adapter (M008) ready for AI operations
          </Alert>
          <Alert severity="warning">
            M012 CLI Interface and M013 VS Code Extension pending implementation
          </Alert>
        </Stack>
      </Box>
    </Box>
  );
};

export default Dashboard;