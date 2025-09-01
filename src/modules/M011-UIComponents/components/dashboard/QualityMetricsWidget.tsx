/**
 * QualityMetricsWidget - Quality metrics visualization
 * 
 * Displays quality analysis metrics including:
 * - Quality dimensions radar chart
 * - Dimension scores with benchmarks
 * - Trends and improvements
 * - Performance against targets
 */

import React from 'react';
import {
  Box,
  Typography,
  LinearProgress,
  IconButton,
  Tooltip,
  useTheme,
  Grid,
  Chip
} from '@mui/material';
import {
  Refresh,
  TrendingUp,
  TrendingDown,
  TrendingFlat
} from '@mui/icons-material';
import {
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Radar,
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as RechartsTooltip
} from 'recharts';

import { WidgetProps, QualityMetricsData } from './types';
import { useGlobalState } from '../../core/state-management';

/**
 * Props interface
 */
interface QualityMetricsWidgetProps extends WidgetProps {
  data?: { qualityMetrics?: QualityMetricsData };
}

/**
 * Quality dimension labels
 */
const DIMENSION_LABELS = {
  completeness: 'Completeness',
  clarity: 'Clarity',
  structure: 'Structure',
  accuracy: 'Accuracy',
  formatting: 'Formatting'
};

/**
 * Get performance color based on score vs benchmark
 */
const getPerformanceColor = (score: number, benchmark: number): 'success' | 'warning' | 'error' => {
  if (score >= benchmark) return 'success';
  if (score >= benchmark - 10) return 'warning';
  return 'error';
};

/**
 * Get trend based on recent data
 */
const getTrend = (data: Array<{ value: number }>): 'up' | 'down' | 'stable' => {
  if (data.length < 2) return 'stable';
  
  const recent = data.slice(-2);
  const change = recent[1].value - recent[0].value;
  
  if (change > 2) return 'up';
  if (change < -2) return 'down';
  return 'stable';
};

/**
 * QualityMetricsWidget component
 */
const QualityMetricsWidget: React.FC<QualityMetricsWidgetProps> = ({
  data,
  loading = false,
  error,
  onRefresh,
  title = 'Quality Metrics'
}) => {
  const theme = useTheme();
  const globalState = useGlobalState();
  const state = globalState.getState();

  const metricsData = data?.qualityMetrics;

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
        
        <Typography color="error" sx={{ textAlign: 'center', mt: 4 }}>
          Failed to load quality metrics: {error}
        </Typography>
      </Box>
    );
  }

  // Show loading or no data state
  if (loading || !metricsData) {
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
            No metrics data available
          </Typography>
        )}
      </Box>
    );
  }

  // Prepare radar chart data
  const radarData = Object.entries(metricsData.dimensions).map(([dimension, score]) => ({
    dimension: DIMENSION_LABELS[dimension as keyof typeof DIMENSION_LABELS],
    score,
    benchmark: metricsData.benchmarks[dimension] || 85,
    fullMark: 100
  }));

  // Prepare bar chart data
  const barData = Object.entries(metricsData.dimensions).map(([dimension, score]) => ({
    name: DIMENSION_LABELS[dimension as keyof typeof DIMENSION_LABELS],
    score,
    benchmark: metricsData.benchmarks[dimension] || 85,
    trend: metricsData.trends[dimension] ? getTrend(metricsData.trends[dimension]) : 'stable'
  }));

  // Calculate overall average
  const averageScore = Math.round(
    Object.values(metricsData.dimensions).reduce((sum, score) => sum + score, 0) / 
    Object.values(metricsData.dimensions).length
  );

  return (
    <Box sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      {/* Header */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
        <Typography variant="h6" component="h3">
          {title}
        </Typography>
        {onRefresh && (
          <Tooltip title="Refresh quality metrics">
            <IconButton size="small" onClick={onRefresh} disabled={loading}>
              <Refresh />
            </IconButton>
          </Tooltip>
        )}
      </Box>

      {/* Overall Score */}
      <Box sx={{ mb: 2 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 1 }}>
          <Typography
            variant="h4"
            component="div"
            sx={{
              fontWeight: 700,
              color: getPerformanceColor(averageScore, 85) === 'success' 
                ? theme.palette.success.main 
                : getPerformanceColor(averageScore, 85) === 'warning'
                ? theme.palette.warning.main
                : theme.palette.error.main
            }}
          >
            {averageScore}%
          </Typography>
          <Chip
            size="small"
            label="Average Quality"
            color={getPerformanceColor(averageScore, 85)}
            variant="outlined"
          />
        </Box>
      </Box>

      {/* Radar Chart */}
      <Box sx={{ height: 180, mb: 2 }}>
        <ResponsiveContainer width="100%" height="100%">
          <RadarChart data={radarData}>
            <PolarGrid />
            <PolarAngleAxis 
              dataKey="dimension" 
              tick={{ fontSize: 10, fill: theme.palette.text.secondary }}
            />
            <PolarRadiusAxis
              angle={90}
              domain={[0, 100]}
              tick={{ fontSize: 8, fill: theme.palette.text.secondary }}
            />
            <Radar
              name="Score"
              dataKey="score"
              stroke={theme.palette.primary.main}
              fill={theme.palette.primary.main}
              fillOpacity={0.1}
              strokeWidth={2}
            />
            <Radar
              name="Benchmark"
              dataKey="benchmark"
              stroke={theme.palette.grey[400]}
              fill="transparent"
              strokeWidth={1}
              strokeDasharray="5 5"
            />
          </RadarChart>
        </ResponsiveContainer>
      </Box>

      {/* Dimension Scores */}
      <Box sx={{ flexGrow: 1, overflow: 'auto' }}>
        <Typography variant="subtitle2" gutterBottom>
          Quality Dimensions
        </Typography>
        
        <Grid container spacing={1}>
          {barData.map((item) => {
            const performanceColor = getPerformanceColor(item.score, item.benchmark);
            const trendIcon = item.trend === 'up' ? <TrendingUp fontSize="small" color="success" />
              : item.trend === 'down' ? <TrendingDown fontSize="small" color="error" />
              : <TrendingFlat fontSize="small" color="action" />;

            return (
              <Grid item xs={12} key={item.name}>
                <Box
                  sx={{
                    p: 1.5,
                    border: `1px solid ${theme.palette.divider}`,
                    borderRadius: 1,
                    
                    ...(state.ui.accessibility.highContrast && {
                      backgroundColor: '#ffffff',
                      border: '2px solid #000000',
                      color: '#000000'
                    })
                  }}
                >
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
                    <Typography variant="body2" fontWeight="medium">
                      {item.name}
                    </Typography>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                      <Typography
                        variant="body2"
                        fontWeight="bold"
                        color={theme.palette[performanceColor].main}
                      >
                        {item.score}%
                      </Typography>
                      {trendIcon}
                    </Box>
                  </Box>
                  
                  <Box sx={{ position: 'relative' }}>
                    <LinearProgress
                      variant="determinate"
                      value={item.score}
                      color={performanceColor}
                      sx={{ height: 6, borderRadius: 3 }}
                    />
                    {/* Benchmark indicator */}
                    <Box
                      sx={{
                        position: 'absolute',
                        left: `${item.benchmark}%`,
                        top: -2,
                        width: 2,
                        height: 10,
                        backgroundColor: theme.palette.grey[600],
                        borderRadius: 1
                      }}
                    />
                  </Box>
                  
                  <Typography variant="caption" color="text.secondary" sx={{ mt: 0.5, display: 'block' }}>
                    Target: {item.benchmark}%
                  </Typography>
                </Box>
              </Grid>
            );
          })}
        </Grid>
      </Box>
    </Box>
  );
};

export default QualityMetricsWidget;