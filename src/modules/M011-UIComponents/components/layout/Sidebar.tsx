/**
 * Sidebar - Navigation sidebar with collapsible menu items
 * 
 * Provides responsive sidebar navigation with:
 * - Hierarchical navigation menu
 * - Collapsible/expandable sections
 * - Active route highlighting
 * - Keyboard navigation support
 * - Accessibility features
 */

import React, { useState, useEffect } from 'react';
import {
  Drawer,
  List,
  ListItem,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Collapse,
  Divider,
  Box,
  Typography,
  useTheme,
  Badge,
  Tooltip
} from '@mui/material';
import {
  ExpandLess,
  ExpandMore,
  Circle as CircleIcon
} from '@mui/icons-material';
import { useLocation, useNavigate } from 'react-router-dom';

import { SidebarProps, NavigationItem } from './types';
import { useGlobalState } from '../../core/state-management';
import { accessibilityManager } from '../../core/accessibility';

/**
 * Navigation item component
 */
interface NavigationItemComponentProps {
  item: NavigationItem;
  level?: number;
  isActive?: boolean;
  onClick?: (item: NavigationItem) => void;
}

const NavigationItemComponent: React.FC<NavigationItemComponentProps> = ({
  item,
  level = 0,
  isActive = false,
  onClick
}) => {
  const theme = useTheme();
  const [expanded, setExpanded] = useState(false);
  const hasChildren = item.children && item.children.length > 0;
  const globalState = useGlobalState();
  const state = globalState.getState();

  // Handle item click
  const handleClick = () => {
    if (hasChildren) {
      setExpanded(!expanded);
      
      // Announce expansion state for screen readers
      accessibilityManager.announceToScreenReader(
        `${item.label} ${expanded ? 'collapsed' : 'expanded'}`
      );
    } else {
      onClick?.(item);
    }
  };

  // Handle keyboard navigation
  const handleKeyDown = (event: React.KeyboardEvent) => {
    switch (event.key) {
      case 'Enter':
      case ' ':
        event.preventDefault();
        handleClick();
        break;
      case 'ArrowRight':
        if (hasChildren && !expanded) {
          event.preventDefault();
          setExpanded(true);
        }
        break;
      case 'ArrowLeft':
        if (hasChildren && expanded) {
          event.preventDefault();
          setExpanded(false);
        }
        break;
    }
  };

  return (
    <>
      <ListItem
        disablePadding
        sx={{
          pl: level * 2,
          
          // High contrast support
          ...(state.ui.accessibility.highContrast && {
            '&.Mui-selected': {
              backgroundColor: '#000000',
              color: '#ffffff',
              '& .MuiListItemIcon-root': {
                color: '#ffffff'
              }
            }
          })
        }}
      >
        <Tooltip 
          title={item.disabled ? `${item.label} (disabled)` : ''} 
          placement="right"
          disableHoverListener={!item.disabled}
        >
          <ListItemButton
            selected={isActive}
            disabled={item.disabled}
            onClick={handleClick}
            onKeyDown={handleKeyDown}
            aria-expanded={hasChildren ? expanded : undefined}
            aria-label={item.label}
            sx={{
              borderRadius: 1,
              mb: 0.5,
              minHeight: 44,
              
              // Active state styles
              '&.Mui-selected': {
                backgroundColor: theme.palette.primary.main + '20',
                borderLeft: `3px solid ${theme.palette.primary.main}`,
                
                '& .MuiListItemIcon-root': {
                  color: theme.palette.primary.main
                },
                
                '& .MuiListItemText-primary': {
                  color: theme.palette.primary.main,
                  fontWeight: 600
                }
              },
              
              // Hover styles
              '&:hover': {
                backgroundColor: theme.palette.action.hover
              },
              
              // Focus styles for keyboard navigation
              '&:focus-visible': {
                outline: `2px solid ${theme.palette.primary.main}`,
                outlineOffset: 2
              },
              
              // Disabled styles
              '&.Mui-disabled': {
                opacity: 0.5
              }
            }}
          >
            {/* Icon */}
            {item.icon && (
              <ListItemIcon sx={{ minWidth: 40 }}>
                {typeof item.icon === 'string' ? (
                  <Box component="span" sx={{ fontSize: '1.2rem' }}>
                    {item.icon}
                  </Box>
                ) : (
                  item.icon
                )}
              </ListItemIcon>
            )}

            {/* Text */}
            <ListItemText
              primary={item.label}
              primaryTypographyProps={{
                variant: 'body2',
                sx: {
                  fontWeight: isActive ? 600 : 400
                }
              }}
            />

            {/* Badge */}
            {item.badge && (
              <Badge
                badgeContent={item.badge}
                color="primary"
                sx={{ mr: 1 }}
              />
            )}

            {/* Expand/collapse icon */}
            {hasChildren && (
              expanded ? <ExpandLess /> : <ExpandMore />
            )}
          </ListItemButton>
        </Tooltip>
      </ListItem>

      {/* Children */}
      {hasChildren && (
        <Collapse in={expanded} timeout="auto" unmountOnExit>
          <List component="div" disablePadding>
            {item.children!.map((child) => (
              <NavigationItemComponent
                key={child.id}
                item={child}
                level={level + 1}
                isActive={child.path === location.pathname}
                onClick={onClick}
              />
            ))}
          </List>
        </Collapse>
      )}
    </>
  );
};

/**
 * Sidebar component
 */
const Sidebar: React.FC<SidebarProps> = ({
  open,
  onClose,
  width,
  variant,
  navigation,
  className,
  testId,
  ...props
}) => {
  const theme = useTheme();
  const location = useLocation();
  const navigate = useNavigate();
  const globalState = useGlobalState();
  const state = globalState.getState();

  // Handle navigation item click
  const handleNavigationClick = (item: NavigationItem) => {
    if (item.external) {
      window.open(item.path, '_blank', 'noopener,noreferrer');
    } else {
      navigate(item.path);
      
      // Close sidebar on mobile after navigation
      if (variant === 'temporary') {
        onClose();
      }
      
      // Announce navigation for screen readers
      accessibilityManager.announceToScreenReader(`Navigated to ${item.label}`);
    }
  };

  // Drawer content
  const drawerContent = (
    <Box
      sx={{
        width: width,
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        backgroundColor: theme.palette.background.paper,
        
        // High contrast support
        ...(state.ui.accessibility.highContrast && {
          backgroundColor: '#ffffff',
          borderRight: '2px solid #000000'
        })
      }}
    >
      {/* Header */}
      <Box
        sx={{
          p: 2,
          borderBottom: `1px solid ${theme.palette.divider}`,
          minHeight: 64,
          display: 'flex',
          alignItems: 'center'
        }}
      >
        <Typography
          variant="h6"
          component="h2"
          sx={{
            fontWeight: 600,
            color: theme.palette.text.primary,
            
            ...(state.ui.accessibility.highContrast && {
              color: '#000000'
            })
          }}
        >
          Navigation
        </Typography>
      </Box>

      {/* Navigation items */}
      <Box
        component="nav"
        role="navigation"
        aria-label="Main navigation"
        sx={{
          flexGrow: 1,
          overflowY: 'auto',
          p: 1,
          
          // Custom scrollbar for better visibility
          '&::-webkit-scrollbar': {
            width: 8
          },
          '&::-webkit-scrollbar-track': {
            backgroundColor: theme.palette.grey[100]
          },
          '&::-webkit-scrollbar-thumb': {
            backgroundColor: theme.palette.grey[400],
            borderRadius: 4,
            '&:hover': {
              backgroundColor: theme.palette.grey[600]
            }
          }
        }}
      >
        <List>
          {navigation.map((item) => (
            <NavigationItemComponent
              key={item.id}
              item={item}
              isActive={item.path === location.pathname}
              onClick={handleNavigationClick}
            />
          ))}
        </List>
      </Box>

      {/* Footer */}
      <Box
        sx={{
          p: 2,
          borderTop: `1px solid ${theme.palette.divider}`,
          textAlign: 'center'
        }}
      >
        <Typography
          variant="caption"
          color="text.secondary"
          sx={{
            ...(state.ui.accessibility.highContrast && {
              color: '#000000'
            })
          }}
        >
          DevDocAI v3.0.0
        </Typography>
      </Box>
    </Box>
  );

  return (
    <Drawer
      variant={variant}
      open={open}
      onClose={onClose}
      className={className}
      data-testid={testId}
      ModalProps={{
        keepMounted: true, // Better mobile performance
      }}
      sx={{
        width: width,
        flexShrink: 0,
        '& .MuiDrawer-paper': {
          width: width,
          boxSizing: 'border-box',
          borderRight: `1px solid ${theme.palette.divider}`,
          
          // Ensure drawer is above other content
          zIndex: theme.zIndex.drawer
        },
        
        // Hide drawer when closed in persistent mode
        ...(variant === 'persistent' && !open && {
          width: 0,
          '& .MuiDrawer-paper': {
            width: 0,
            overflow: 'hidden'
          }
        })
      }}
      {...props}
    >
      {drawerContent}
    </Drawer>
  );
};

export default Sidebar;