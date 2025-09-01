/**
 * TrackingMatrixWidget - Document relationship visualization
 * 
 * Displays document tracking matrix with:
 * - Interactive force-directed graph
 * - Document nodes with status colors
 * - Relationship edges between documents
 * - Cluster visualization
 * - Navigation and filtering
 */

import React, { useMemo, useState } from 'react';
import {
  Box,
  Typography,
  IconButton,
  Tooltip,
  Chip,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  useTheme,
  Paper,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  Avatar
} from '@mui/material';
import {
  Refresh,
  FilterList,
  Fullscreen,
  Description,
  Link as LinkIcon
} from '@mui/icons-material';
import { ScatterChart, Scatter, XAxis, YAxis, ResponsiveContainer, Tooltip as RechartsTooltip } from 'recharts';

import { WidgetProps, TrackingMatrixData } from './types';
import { useGlobalState } from '../../core/state-management';

/**
 * Props interface
 */
interface TrackingMatrixWidgetProps extends WidgetProps {
  data?: { trackingMatrix?: TrackingMatrixData };
}

/**
 * Status color mapping
 */
const STATUS_COLORS = {
  ready: '#4caf50',
  draft: '#ff9800', 
  outdated: '#f44336',
  error: '#9c27b0'
};

/**
 * Document type icons
 */
const TYPE_ICONS = {
  api: '🔧',
  guide: '📖',
  spec: '📋',
  readme: '📄',
  default: '📄'
};

/**
 * TrackingMatrixWidget component
 */
const TrackingMatrixWidget: React.FC<TrackingMatrixWidgetProps> = ({
  data,
  loading = false,
  error,
  onRefresh,
  title = 'Document Tracking Matrix'
}) => {
  const theme = useTheme();
  const globalState = useGlobalState();
  const state = globalState.getState();

  const matrixData = data?.trackingMatrix;

  // State for filtering and view
  const [selectedCluster, setSelectedCluster] = useState<string>('all');
  const [viewMode, setViewMode] = useState<'graph' | 'list'>('graph');

  // Prepare scatter plot data
  const scatterData = useMemo(() => {
    if (!matrixData) return [];
    
    return matrixData.nodes.map((node, index) => ({
      x: Math.cos(index * 0.5) * (50 + node.qualityScore),
      y: Math.sin(index * 0.5) * (50 + node.qualityScore),
      z: node.size,
      name: node.name,
      status: node.status,
      type: node.type,
      qualityScore: node.qualityScore,
      id: node.id
    }));
  }, [matrixData]);

  // Filter data based on selected cluster
  const filteredData = useMemo(() => {
    if (!matrixData || selectedCluster === 'all') return scatterData;
    
    const cluster = matrixData.clusters.find(c => c.id === selectedCluster);
    if (!cluster) return scatterData;
    
    return scatterData.filter(node => cluster.nodes.includes(node.id));
  }, [scatterData, matrixData, selectedCluster]);

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
          Failed to load tracking matrix: {error}
        </Typography>
      </Box>
    );
  }

  // Show loading or no data state
  if (loading || !matrixData) {
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
            <Typography color="text.secondary">Loading tracking matrix...</Typography>
          </Box>
        ) : (
          <Typography color="text.secondary" sx={{ textAlign: 'center', mt: 4 }}>
            No tracking data available
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
        <Box sx={{ display: 'flex', gap: 1, alignItems: 'center' }}>
          {/* Cluster filter */}
          <FormControl size="small" sx={{ minWidth: 120 }}>
            <InputLabel>Cluster</InputLabel>
            <Select
              value={selectedCluster}
              label="Cluster"
              onChange={(e) => setSelectedCluster(e.target.value)}
            >
              <MenuItem value="all">All Documents</MenuItem>
              {matrixData.clusters.map((cluster) => (
                <MenuItem key={cluster.id} value={cluster.id}>
                  {cluster.name}
                </MenuItem>
              ))}
            </Select>
          </FormControl>

          {onRefresh && (
            <Tooltip title="Refresh tracking matrix">
              <IconButton size="small" onClick={onRefresh} disabled={loading}>
                <Refresh />
              </IconButton>
            </Tooltip>
          )}

          <Tooltip title="Fullscreen view">
            <IconButton size="small">
              <Fullscreen />
            </IconButton>
          </Tooltip>
        </Box>
      </Box>

      {/* Statistics */}
      <Box sx={{ display: 'flex', gap: 1, mb: 2, flexWrap: 'wrap' }}>
        <Chip
          size="small"
          label={`${matrixData.nodes.length} Documents`}
          variant="outlined"
          icon={<Description fontSize="small" />}
        />
        <Chip
          size="small"
          label={`${matrixData.edges.length} Connections`}
          variant="outlined"
          icon={<LinkIcon fontSize="small" />}
        />
        {matrixData.clusters.map((cluster) => (
          <Chip
            key={cluster.id}
            size="small"
            label={`${cluster.name}: ${cluster.health}%`}
            variant={selectedCluster === cluster.id ? 'filled' : 'outlined'}
            color={cluster.health >= 85 ? 'success' : cluster.health >= 70 ? 'warning' : 'error'}
            onClick={() => setSelectedCluster(selectedCluster === cluster.id ? 'all' : cluster.id)}
            sx={{ cursor: 'pointer' }}
          />
        ))}
      </Box>

      {/* Visualization */}
      <Box sx={{ flexGrow: 1, position: 'relative' }}>
        {viewMode === 'graph' ? (
          <Box sx={{ height: '100%', minHeight: 200 }}>
            <ResponsiveContainer width="100%" height="100%">
              <ScatterChart
                data={filteredData}
                margin={{ top: 10, right: 10, bottom: 10, left: 10 }}
              >
                <XAxis type="number" dataKey="x" hide />
                <YAxis type="number" dataKey="y" hide />
                <RechartsTooltip
                  content={({ active, payload }) => {
                    if (active && payload && payload[0]) {
                      const data = payload[0].payload;
                      return (
                        <Paper
                          sx={{
                            p: 2,
                            backgroundColor: theme.palette.background.paper,
                            border: `1px solid ${theme.palette.divider}`,
                            borderRadius: 1,
                            boxShadow: theme.shadows[3]
                          }}
                        >
                          <Typography variant="subtitle2" gutterBottom>
                            {data.name}
                          </Typography>
                          <Typography variant="body2" color="text.secondary">
                            Type: {data.type}
                          </Typography>
                          <Typography variant="body2" color="text.secondary">
                            Status: {data.status}
                          </Typography>
                          <Typography variant="body2" color="text.secondary">
                            Quality: {data.qualityScore}%
                          </Typography>
                          <Typography variant="body2" color="text.secondary">
                            Size: {data.z} lines
                          </Typography>
                        </Paper>
                      );
                    }
                    return null;
                  }}
                />
                <Scatter
                  dataKey="z"
                  fill={(entry: any) => STATUS_COLORS[entry.status as keyof typeof STATUS_COLORS] || STATUS_COLORS.ready}
                />
              </ScatterChart>
            </ResponsiveContainer>

            {/* Legend */}
            <Box
              sx={{
                position: 'absolute',
                bottom: 8,
                right: 8,
                backgroundColor: theme.palette.background.paper,
                p: 1,
                borderRadius: 1,
                border: `1px solid ${theme.palette.divider}`,
                boxShadow: theme.shadows[1]
              }}
            >
              <Typography variant="caption" gutterBottom display="block">
                Status
              </Typography>
              {Object.entries(STATUS_COLORS).map(([status, color]) => (
                <Box key={status} sx={{ display: 'flex', alignItems: 'center', gap: 0.5, mb: 0.5 }}>
                  <Box
                    sx={{
                      width: 12,
                      height: 12,
                      backgroundColor: color,
                      borderRadius: '50%'
                    }}
                  />
                  <Typography variant="caption" sx={{ textTransform: 'capitalize' }}>
                    {status}
                  </Typography>
                </Box>
              ))}
            </Box>
          </Box>
        ) : (
          // List view
          <List sx={{ height: '100%', overflow: 'auto' }}>
            {filteredData.map((node) => (
              <ListItem
                key={node.id}
                sx={{
                  border: `1px solid ${theme.palette.divider}`,
                  borderRadius: 1,
                  mb: 1,
                  
                  ...(state.ui.accessibility.highContrast && {
                    backgroundColor: '#ffffff',
                    border: '2px solid #000000',
                    color: '#000000'
                  })
                }}
              >
                <ListItemIcon>
                  <Avatar
                    sx={{
                      width: 32,
                      height: 32,
                      backgroundColor: STATUS_COLORS[node.status as keyof typeof STATUS_COLORS],
                      fontSize: '0.875rem'
                    }}
                  >
                    {TYPE_ICONS[node.type as keyof typeof TYPE_ICONS] || TYPE_ICONS.default}
                  </Avatar>
                </ListItemIcon>
                <ListItemText
                  primary={
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <Typography variant="body2" fontWeight="medium">
                        {node.name}
                      </Typography>
                      <Chip
                        size="small"
                        label={`${node.qualityScore}%`}
                        color={node.qualityScore >= 85 ? 'success' : node.qualityScore >= 70 ? 'warning' : 'error'}
                      />
                    </Box>
                  }
                  secondary={
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', mt: 0.5 }}>
                      <Typography variant="caption" color="text.secondary">
                        {node.type} • {node.status}
                      </Typography>
                      <Typography variant="caption" color="text.secondary">
                        {node.z} lines
                      </Typography>
                    </Box>
                  }
                />
              </ListItem>
            ))}
          </List>
        )}
      </Box>

      {/* View toggle */}
      <Box sx={{ display: 'flex', justifyContent: 'center', mt: 1 }}>
        <Chip
          size="small"
          label={viewMode === 'graph' ? 'Switch to List' : 'Switch to Graph'}
          onClick={() => setViewMode(viewMode === 'graph' ? 'list' : 'graph')}
          variant="outlined"
          sx={{ cursor: 'pointer' }}
        />
      </Box>
    </Box>
  );
};

export default TrackingMatrixWidget;