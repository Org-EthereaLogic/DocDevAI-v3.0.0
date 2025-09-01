/**
 * Footer - Application footer with links and information
 * 
 * Provides application footer with:
 * - Copyright and version information
 * - Quick links
 * - Privacy-first messaging
 * - Compact mode for mobile
 */

import React from 'react';
import {
  Box,
  Container,
  Typography,
  Link,
  Divider,
  useTheme,
  useMediaQuery
} from '@mui/material';
import { styled } from '@mui/material/styles';

import { FooterProps } from './types';
import { useGlobalState } from '../../core/state-management';

/**
 * Styled footer container
 */
const FooterContainer = styled(Box)(({ theme }) => ({
  backgroundColor: theme.palette.background.paper,
  borderTop: `1px solid ${theme.palette.divider}`,
  marginTop: 'auto',
  
  // High contrast support
  '@media (prefers-contrast: high)': {
    backgroundColor: '#ffffff',
    borderTop: '2px solid #000000',
    color: '#000000'
  }
}));

/**
 * Footer links data
 */
const FOOTER_LINKS = [
  { label: 'Privacy Policy', href: '/privacy', internal: true },
  { label: 'Terms of Service', href: '/terms', internal: true },
  { label: 'Documentation', href: '/docs', internal: true },
  { label: 'GitHub', href: 'https://github.com/devdocai/devdocai', internal: false },
  { label: 'Support', href: '/support', internal: true }
];

/**
 * Footer component
 */
const Footer: React.FC<FooterProps> = ({
  compact = false,
  className,
  testId,
  ...props
}) => {
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('sm'));
  const globalState = useGlobalState();
  const state = globalState.getState();

  // Use compact mode on mobile or when explicitly requested
  const useCompactMode = compact || isMobile;

  return (
    <FooterContainer
      component="footer"
      role="contentinfo"
      className={className}
      data-testid={testId}
      sx={{
        py: useCompactMode ? 2 : 3,
        
        // High contrast adjustments
        ...(state.ui.accessibility.highContrast && {
          backgroundColor: '#ffffff',
          borderTop: '2px solid #000000',
          color: '#000000'
        })
      }}
      {...props}
    >
      <Container maxWidth="lg">
        {useCompactMode ? (
          // Compact footer for mobile
          <Box
            sx={{
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              gap: 1
            }}
          >
            <Typography
              variant="caption"
              color="text.secondary"
              align="center"
              sx={{
                ...(state.ui.accessibility.highContrast && {
                  color: '#000000'
                })
              }}
            >
              © 2025 DevDocAI Team. Privacy-first documentation.
            </Typography>
            
            <Box
              sx={{
                display: 'flex',
                gap: 2,
                flexWrap: 'wrap',
                justifyContent: 'center'
              }}
            >
              {FOOTER_LINKS.slice(0, 3).map((link, index) => (
                <Link
                  key={index}
                  href={link.href}
                  target={link.internal ? '_self' : '_blank'}
                  rel={link.internal ? undefined : 'noopener noreferrer'}
                  underline="hover"
                  sx={{
                    fontSize: '0.75rem',
                    color: 'text.secondary',
                    
                    '&:hover': {
                      color: theme.palette.primary.main
                    },
                    
                    ...(state.ui.accessibility.highContrast && {
                      color: '#000000',
                      '&:hover': {
                        color: '#000000',
                        textDecoration: 'underline'
                      }
                    })
                  }}
                >
                  {link.label}
                </Link>
              ))}
            </Box>
          </Box>
        ) : (
          // Full footer for desktop
          <Box>
            {/* Main footer content */}
            <Box
              sx={{
                display: 'grid',
                gridTemplateColumns: {
                  xs: '1fr',
                  md: '2fr 1fr 1fr'
                },
                gap: 4,
                mb: 3
              }}
            >
              {/* About section */}
              <Box>
                <Typography
                  variant="h6"
                  component="h3"
                  gutterBottom
                  sx={{
                    fontWeight: 600,
                    color: theme.palette.primary.main,
                    
                    ...(state.ui.accessibility.highContrast && {
                      color: '#000000'
                    })
                  }}
                >
                  DevDocAI
                </Typography>
                <Typography
                  variant="body2"
                  color="text.secondary"
                  sx={{
                    maxWidth: 300,
                    lineHeight: 1.6,
                    
                    ...(state.ui.accessibility.highContrast && {
                      color: '#000000'
                    })
                  }}
                >
                  Privacy-first AI-powered documentation generation and analysis 
                  for solo developers. Your data stays local, your docs get better.
                </Typography>
              </Box>

              {/* Quick links */}
              <Box>
                <Typography
                  variant="subtitle2"
                  component="h4"
                  gutterBottom
                  sx={{
                    fontWeight: 600,
                    textTransform: 'uppercase',
                    letterSpacing: 1,
                    
                    ...(state.ui.accessibility.highContrast && {
                      color: '#000000'
                    })
                  }}
                >
                  Quick Links
                </Typography>
                <Box
                  component="nav"
                  aria-label="Footer navigation"
                  sx={{
                    display: 'flex',
                    flexDirection: 'column',
                    gap: 1
                  }}
                >
                  {FOOTER_LINKS.map((link, index) => (
                    <Link
                      key={index}
                      href={link.href}
                      target={link.internal ? '_self' : '_blank'}
                      rel={link.internal ? undefined : 'noopener noreferrer'}
                      underline="hover"
                      sx={{
                        color: 'text.secondary',
                        fontSize: '0.875rem',
                        
                        '&:hover': {
                          color: theme.palette.primary.main
                        },
                        
                        '&:focus-visible': {
                          outline: `2px solid ${theme.palette.primary.main}`,
                          outlineOffset: 2,
                          borderRadius: 1
                        },
                        
                        ...(state.ui.accessibility.highContrast && {
                          color: '#000000',
                          '&:hover': {
                            color: '#000000',
                            textDecoration: 'underline'
                          }
                        })
                      }}
                    >
                      {link.label}
                    </Link>
                  ))}
                </Box>
              </Box>

              {/* Privacy notice */}
              <Box>
                <Typography
                  variant="subtitle2"
                  component="h4"
                  gutterBottom
                  sx={{
                    fontWeight: 600,
                    textTransform: 'uppercase',
                    letterSpacing: 1,
                    
                    ...(state.ui.accessibility.highContrast && {
                      color: '#000000'
                    })
                  }}
                >
                  Privacy First
                </Typography>
                <Typography
                  variant="body2"
                  color="text.secondary"
                  sx={{
                    fontSize: '0.875rem',
                    lineHeight: 1.5,
                    
                    ...(state.ui.accessibility.highContrast && {
                      color: '#000000'
                    })
                  }}
                >
                  Your documents and data remain on your machine. 
                  No telemetry, no tracking, no cloud storage required.
                </Typography>
              </Box>
            </Box>

            <Divider 
              sx={{
                ...(state.ui.accessibility.highContrast && {
                  backgroundColor: '#000000',
                  height: 2
                })
              }} 
            />

            {/* Copyright */}
            <Box
              sx={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                mt: 2,
                flexWrap: 'wrap',
                gap: 2
              }}
            >
              <Typography
                variant="body2"
                color="text.secondary"
                sx={{
                  ...(state.ui.accessibility.highContrast && {
                    color: '#000000'
                  })
                }}
              >
                © 2025 DevDocAI Team. Licensed under Apache-2.0.
              </Typography>
              
              <Typography
                variant="body2"
                color="text.secondary"
                sx={{
                  fontSize: '0.75rem',
                  
                  ...(state.ui.accessibility.highContrast && {
                    color: '#000000'
                  })
                }}
              >
                Version 3.0.0 | Build {process.env.REACT_APP_BUILD_NUMBER || 'dev'}
              </Typography>
            </Box>
          </Box>
        )}
      </Container>
    </FooterContainer>
  );
};

export default Footer;