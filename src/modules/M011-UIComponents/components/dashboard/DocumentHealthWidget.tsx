/**
 * DocumentHealthWidget - Overall document health visualization
 * 
 * Displays document health metrics including:
 * - Overall health score with trend
 * - Health breakdown by document type
 * - Recent score history chart
 * - Critical issues summary
 */

import React, { useMemo } from 'react';
import {
  Box,
  Typography,
  LinearProgress,
  Chip,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  Alert,
  IconButton,
  Tooltip,
  useTheme
} from '@mui/material';
import {
  TrendingUp,
  TrendingDown,
  TrendingFlat,
  Warning,
  Error,
  Info,
  Refresh
} from '@mui/icons-material';
import { LineChart, Line, XAxis, YAxis, ResponsiveContainer, Tooltip as RechartsTooltip } from 'recharts';

import { WidgetProps, DocumentHealthData } from './types';
import { useGlobalState } from '../../core/state-management';

/**
 * Props interface
 */
interface DocumentHealthWidgetProps extends WidgetProps {
  data?: { documentHealth?: DocumentHealthData };
}

/**
 * Get health color based on score
 */
const getHealthColor = (score: number): 'success' | 'warning' | 'error' => {
  if (score >= 85) return 'success';
  if (score >= 70) return 'warning';
  return 'error';
};

/**
 * Get trend icon
 */
const getTrendIcon = (trend: 'up' | 'down' | 'stable') => {
  switch (trend) {
    case 'up':
      return <TrendingUp color="success" fontSize="small" />;
    case 'down':
      return <TrendingDown color="error" fontSize="small" />;
    case 'stable':
    default:
      return <TrendingFlat color="action" fontSize="small" />;
  }
};

/**
 * Get severity icon
 */
const getSeverityIcon = (severity: string) => {
  switch (severity) {
    case 'critical':
      return <Error color="error" fontSize="small" />;
    case 'high':
      return <Warning color="warning" fontSize="small" />;
    case 'medium':
      return <Warning color="warning" fontSize="small" />;
    case 'low':
    default:
      return <Info color="info" fontSize="small" />;
  }
};

/**
 * DocumentHealthWidget component
 */
const DocumentHealthWidget: React.FC<DocumentHealthWidgetProps> = ({
  data,
  loading = false,
  error,
  onRefresh,
  title = 'Document Health'
}) => {
  const theme = useTheme();
  const globalState = useGlobalState();
  const state = globalState.getState();

  const healthData = data?.documentHealth;

  // Calculate health statistics
  const healthStats = useMemo(() => {
    if (!healthData) return null;

    const totalDocs = healthData.totalDocuments;
    const types = Object.entries(healthData.byType);
    const healthyDocs = types.reduce((acc, [, typeData]) => {
      return acc + (typeData.averageScore >= 85 ? typeData.count : 0);
    }, 0);

    const criticalIssues = healthData.issues.filter(issue => 
      issue.severity === 'critical' || issue.severity === 'high'
    ).length;

    return {
      totalDocs,
      healthyDocs,
      healthyPercentage: Math.round((healthyDocs / totalDocs) * 100),
      criticalIssues
    };
  }, [healthData]);

  // Show error state
  if (error) {
    return (
      <Box sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
          <Typography variant="h6" component="h3">
            {title}
          </Typography>
          {onRefresh && (
            <IconButton size="small" onClick={onRefresh} disabled={loading}>
              <Refresh />
            </IconButton>
          )}
        </Box>
        
        <Alert severity="error" sx={{ flexGrow: 1 }}>
          Failed to load document health data: {error}
        </Alert>
      </Box>
    );
  }

  // Show loading or no data state
  if (loading || !healthData || !healthStats) {
    return (
      <Box sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
          <Typography variant="h6" component="h3">
            {title}
          </Typography>
          {onRefresh && (
            <IconButton size="small" onClick={onRefresh} disabled={loading}>
              <Refresh />
            </IconButton>
          )}
        </Box>
        
        {loading ? (
          <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', flexGrow: 1 }}>
            <LinearProgress sx={{ width: '100%' }} />
          </Box>
        ) : (
          <Typography color="text.secondary" sx={{ textAlign: 'center', mt: 4 }}>
            No health data available
          </Typography>
        )}
      </Box>
    );
  }

  return (
    <Box sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      {/* Header */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
        <Typography variant="h6" component="h3">
          {title}
        </Typography>
        {onRefresh && (
          <Tooltip title="Refresh health data">
            <IconButton size="small" onClick={onRefresh} disabled={loading}>
              <Refresh />
            </IconButton>
          </Tooltip>
        )}
      </Box>

      {/* Overall Health Score */}
      <Box sx={{ mb: 3 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
          <Typography
            variant="h3"
            component="div"
            sx={{
              fontWeight: 700,
              color: theme.palette[getHealthColor(healthData.overall)].main,
              mr: 1
            }}
          >
            {healthData.overall}%
          </Typography>
          <Box sx={{ display: 'flex', flexDirection: 'column' }}>
            <Typography variant="body2" color="text.secondary">
              Overall Health
            </Typography>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
              <Typography variant="caption" color="text.secondary">
                {healthStats.healthyDocs}/{healthStats.totalDocs} healthy
              </Typography>
            </Box>
          </Box>
        </Box>

        {/* Health Progress Bar */}
        <LinearProgress
          variant="determinate"
          value={healthData.overall}
          color={getHealthColor(healthData.overall)}
          sx={{ height: 8, borderRadius: 4, mb: 1 }}
        />
      </Box>

      {/* Health by Type */}
      <Box sx={{ mb: 3, flexGrow: 1 }}>
        <Typography variant="subtitle2" gutterBottom>
          Health by Document Type
        </Typography>
        <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1, mb: 2 }}>
          {Object.entries(healthData.byType).map(([type, typeData]) => (
            <Chip
              key={type}
              label={`${type}: ${typeData.averageScore}%`}
              size="small"
              color={getHealthColor(typeData.averageScore)}
              variant="outlined"
              icon={getTrendIcon(typeData.trend)}
              sx={{
                ...(state.ui.accessibility.highContrast && {
                  backgroundColor: '#ffffff',
                  color: '#000000',
                  border: '2px solid #000000'
                })
              }}
            />
          ))}
        </Box>

        {/* Recent Trend Chart */}
        <Box sx={{ height: 120, mb: 2 }}>
          <Typography variant="caption" color="text.secondary" gutterBottom>
            7-Day Health Trend
          </Typography>
          <ResponsiveContainer width="100%" height={100}>
            <LineChart data={healthData.recentScores}>
              <XAxis 
                dataKey="date" 
                tick={{ fontSize: 10 }}
                tickFormatter={(value) => new Date(value).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
              />
              <YAxis domain={[60, 100]} tick={{ fontSize: 10 }} />
              <RechartsTooltip 
                formatter={(value) => [`${value}%`, 'Health Score']}
                labelFormatter={(value) => new Date(value).toLocaleDateString()}
              />
              <Line
                type="monotone"
                dataKey="score"
                stroke={theme.palette.primary.main}
                strokeWidth={2}
                dot={{ fill: theme.palette.primary.main, strokeWidth: 2, r: 3 }}
                activeDot={{ r: 5 }}
              />
            </LineChart>
          </ResponsiveContainer>
        </Box>
      </Box>

      {/* Critical Issues */}
      {healthData.issues.length > 0 && (
        <Box sx={{ mt: 'auto' }}>
          <Typography variant="subtitle2" gutterBottom>
            Recent Issues ({healthStats.criticalIssues} critical)
          </Typography>
          <List dense sx={{ maxHeight: 120, overflow: 'auto' }}>
            {healthData.issues.slice(0, 3).map((issue) => (
              <ListItem
                key={issue.id}
                sx={{
                  px: 0,
                  py: 0.5,
                  borderRadius: 1,
                  
                  '&:hover': {
                    backgroundColor: theme.palette.action.hover
                  }
                }}
              >
                <ListItemIcon sx={{ minWidth: 32 }}>
                  {getSeverityIcon(issue.severity)}
                </ListItemIcon>
                <ListItemText
                  primary={
                    <Typography variant="body2" noWrap>
                      {issue.message}
                    </Typography>
                  }
                  secondary={
                    <Typography variant="caption" color="text.secondary">
                      {issue.documentName}
                    </Typography>
                  }
                />
              </ListItem>
            ))}
          </List>
          
          {healthData.issues.length > 3 && (
            <Typography variant="caption" color="text.secondary" sx={{ textAlign: 'center', display: 'block', mt: 1 }}>
              +{healthData.issues.length - 3} more issues
            </Typography>
          )}
        </Box>
      )}
    </Box>
  );
};

export default DocumentHealthWidget;