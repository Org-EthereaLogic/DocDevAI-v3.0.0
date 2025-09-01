/**
 * RecentActivityWidget - Recent activities and updates display
 * 
 * Shows recent activities including:
 * - Document generation events
 * - Quality analysis completions
 * - Enhancement operations
 * - System updates and notifications
 */

import React, { useState } from 'react';
import {
  Box,
  Typography,
  IconButton,
  Tooltip,
  List,
  ListItem,
  ListItemAvatar,
  ListItemText,
  Avatar,
  Chip,
  Button,
  useTheme,
  Divider,
  Badge
} from '@mui/material';
import {
  Refresh,
  Add as AddIcon,
  CheckCircle,
  Analytics,
  AutoFixHigh,
  Update,
  Description,
  MoreVert,
  AccessTime
} from '@mui/icons-material';

import { WidgetProps, RecentActivityData } from './types';
import { useGlobalState } from '../../core/state-management';

/**
 * Props interface
 */
interface RecentActivityWidgetProps extends WidgetProps {
  data?: { recentActivity?: RecentActivityData };
}

/**
 * Activity type configurations
 */
const ACTIVITY_CONFIG = {
  generated: {
    icon: <AddIcon />,
    color: '#4caf50',
    label: 'Generated',
    bgColor: '#e8f5e8'
  },
  analyzed: {
    icon: <Analytics />,
    color: '#2196f3',
    label: 'Analyzed',
    bgColor: '#e3f2fd'
  },
  enhanced: {
    icon: <AutoFixHigh />,
    color: '#9c27b0',
    label: 'Enhanced',
    bgColor: '#f3e5f5'
  },
  updated: {
    icon: <Update />,
    color: '#ff9800',
    label: 'Updated',
    bgColor: '#fff3e0'
  }
};

/**
 * Format relative time
 */
const formatRelativeTime = (timestamp: string): string => {
  const now = new Date();
  const time = new Date(timestamp);
  const diffInSeconds = Math.floor((now.getTime() - time.getTime()) / 1000);

  if (diffInSeconds < 60) return 'Just now';
  if (diffInSeconds < 3600) return `${Math.floor(diffInSeconds / 60)}m ago`;
  if (diffInSeconds < 86400) return `${Math.floor(diffInSeconds / 3600)}h ago`;
  if (diffInSeconds < 604800) return `${Math.floor(diffInSeconds / 86400)}d ago`;
  
  return time.toLocaleDateString();
};

/**
 * RecentActivityWidget component
 */
const RecentActivityWidget: React.FC<RecentActivityWidgetProps> = ({
  data,
  loading = false,
  error,
  onRefresh,
  title = 'Recent Activity'
}) => {
  const theme = useTheme();
  const globalState = useGlobalState();
  const state = globalState.getState();

  const activityData = data?.recentActivity;
  const [showAll, setShowAll] = useState(false);

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
          Failed to load recent activity: {error}
        </Typography>
      </Box>
    );
  }

  // Show loading or no data state
  if (loading || !activityData) {
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
            <Typography color="text.secondary">Loading recent activity...</Typography>
          </Box>
        ) : (
          <Typography color="text.secondary" sx={{ textAlign: 'center', mt: 4 }}>
            No recent activity
          </Typography>
        )}
      </Box>
    );
  }

  const activities = activityData.activities || [];
  const displayedActivities = showAll ? activities : activities.slice(0, 5);

  return (
    <Box sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      {/* Header */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <Typography variant="h6" component="h3">
            {title}
          </Typography>
          {activities.length > 0 && (
            <Badge
              badgeContent={activities.length}
              color="primary"
              sx={{
                '& .MuiBadge-badge': {
                  fontSize: '0.75rem',
                  height: 18,
                  minWidth: 18
                }
              }}
            />
          )}
        </Box>
        
        {onRefresh && (
          <Tooltip title="Refresh activity feed">
            <IconButton size="small" onClick={onRefresh} disabled={loading}>
              <Refresh />
            </IconButton>
          </Tooltip>
        )}
      </Box>

      {activities.length === 0 ? (
        // Empty state
        <Box
          sx={{
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            flexGrow: 1,
            gap: 2
          }}
        >
          <Avatar
            sx={{
              width: 64,
              height: 64,
              backgroundColor: theme.palette.grey[100],
              color: theme.palette.grey[400]
            }}
          >
            <Description fontSize="large" />
          </Avatar>
          <Box sx={{ textAlign: 'center' }}>
            <Typography variant="body2" color="text.secondary" gutterBottom>
              No recent activity
            </Typography>
            <Typography variant="caption" color="text.secondary">
              Start generating or analyzing documents to see activity here
            </Typography>
          </Box>
        </Box>
      ) : (
        // Activity list
        <>
          <List
            sx={{
              flexGrow: 1,
              overflow: 'auto',
              py: 0,
              
              // Custom scrollbar
              '&::-webkit-scrollbar': {
                width: 6
              },
              '&::-webkit-scrollbar-track': {
                backgroundColor: theme.palette.grey[100]
              },
              '&::-webkit-scrollbar-thumb': {
                backgroundColor: theme.palette.grey[400],
                borderRadius: 3,
                '&:hover': {
                  backgroundColor: theme.palette.grey[600]
                }
              }
            }}
          >
            {displayedActivities.map((activity, index) => {
              const config = ACTIVITY_CONFIG[activity.type as keyof typeof ACTIVITY_CONFIG];
              const isLast = index === displayedActivities.length - 1;

              return (
                <React.Fragment key={activity.id}>
                  <ListItem
                    sx={{
                      px: 0,
                      py: 1.5,
                      alignItems: 'flex-start',
                      
                      '&:hover': {
                        backgroundColor: theme.palette.action.hover,
                        borderRadius: 1
                      },
                      
                      ...(state.ui.accessibility.highContrast && {
                        '&:hover': {
                          backgroundColor: '#f0f0f0',
                          color: '#000000'
                        }
                      })
                    }}
                  >
                    <ListItemAvatar>
                      <Avatar
                        sx={{
                          width: 36,
                          height: 36,
                          backgroundColor: config?.bgColor || theme.palette.grey[100],
                          color: config?.color || theme.palette.text.secondary,
                          
                          ...(state.ui.accessibility.highContrast && {
                            backgroundColor: '#ffffff',
                            border: '2px solid #000000',
                            color: '#000000'
                          })
                        }}
                      >
                        {config?.icon || <Description />}
                      </Avatar>
                    </ListItemAvatar>

                    <ListItemText
                      primary={
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 0.5 }}>
                          <Typography
                            variant="body2"
                            fontWeight="medium"
                            sx={{
                              ...(state.ui.accessibility.highContrast && {
                                color: '#000000'
                              })
                            }}
                          >
                            {activity.title}
                          </Typography>
                          <Chip
                            size="small"
                            label={config?.label || activity.type}
                            sx={{
                              height: 20,
                              fontSize: '0.6875rem',
                              backgroundColor: config?.bgColor,
                              color: config?.color,
                              fontWeight: 'medium',
                              
                              ...(state.ui.accessibility.highContrast && {
                                backgroundColor: '#ffffff',
                                border: '1px solid #000000',
                                color: '#000000'
                              })
                            }}
                          />
                        </Box>
                      }
                      secondary={
                        <Box>
                          <Typography
                            variant="body2"
                            color="text.secondary"
                            sx={{
                              mb: 0.5,
                              display: '-webkit-box',
                              WebkitLineClamp: 2,
                              WebkitBoxOrient: 'vertical',
                              overflow: 'hidden',
                              
                              ...(state.ui.accessibility.highContrast && {
                                color: '#000000'
                              })
                            }}
                          >
                            {activity.description}
                          </Typography>
                          
                          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mt: 0.5 }}>
                            <AccessTime fontSize="inherit" sx={{ fontSize: 12, color: 'text.disabled' }} />
                            <Typography
                              variant="caption"
                              color="text.disabled"
                              sx={{
                                ...(state.ui.accessibility.highContrast && {
                                  color: '#000000'
                                })
                              }}
                            >
                              {formatRelativeTime(activity.timestamp)}
                            </Typography>
                            
                            {activity.documentName && (
                              <>
                                <Typography variant="caption" color="text.disabled">
                                  •
                                </Typography>
                                <Typography
                                  variant="caption"
                                  color="text.disabled"
                                  sx={{
                                    fontStyle: 'italic',
                                    
                                    ...(state.ui.accessibility.highContrast && {
                                      color: '#000000'
                                    })
                                  }}
                                >
                                  {activity.documentName}
                                </Typography>
                              </>
                            )}
                          </Box>
                        </Box>
                      }
                    />

                    <IconButton size="small" sx={{ mt: 0.5, opacity: 0.5 }}>
                      <MoreVert fontSize="small" />
                    </IconButton>
                  </ListItem>
                  
                  {!isLast && (
                    <Divider
                      sx={{
                        ml: 5,
                        
                        ...(state.ui.accessibility.highContrast && {
                          backgroundColor: '#000000',
                          height: 2
                        })
                      }}
                    />
                  )}
                </React.Fragment>
              );
            })}
          </List>

          {/* Show more/less button */}
          {activities.length > 5 && (
            <Box sx={{ textAlign: 'center', pt: 1, borderTop: `1px solid ${theme.palette.divider}` }}>
              <Button
                size="small"
                onClick={() => setShowAll(!showAll)}
                sx={{
                  ...(state.ui.accessibility.highContrast && {
                    backgroundColor: '#ffffff',
                    color: '#000000',
                    border: '2px solid #000000',
                    '&:hover': {
                      backgroundColor: '#f0f0f0'
                    }
                  })
                }}
              >
                {showAll ? 'Show Less' : `Show All (${activities.length})`}
              </Button>
            </Box>
          )}
        </>
      )}
    </Box>
  );
};

export default RecentActivityWidget;