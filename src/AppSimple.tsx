/**
 * Simplified App Component for Testing
 */

import React from 'react';
import { 
  ThemeProvider, 
  CssBaseline, 
  createTheme,
  Container,
  Typography,
  Box,
  Alert,
  Paper
} from '@mui/material';

const theme = createTheme({
  palette: {
    mode: 'light',
    primary: {
      main: '#667eea',
    },
    secondary: {
      main: '#764ba2',
    },
  },
});

const AppSimple: React.FC = () => {
  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <Container maxWidth="lg">
        <Box sx={{ py: 4 }}>
          <Paper elevation={3} sx={{ p: 3 }}>
            <Typography variant="h3" gutterBottom>
              DevDocAI v3.0.0
            </Typography>
            <Typography variant="h6" color="text.secondary" paragraph>
              Application is loading...
            </Typography>
            <Alert severity="success" sx={{ mt: 2 }}>
              If you can see this message, React and Material-UI are working correctly!
            </Alert>
            <Alert severity="info" sx={{ mt: 2 }}>
              The white screen issue has been isolated to the main App component.
            </Alert>
            <Box sx={{ mt: 3 }}>
              <Typography variant="body2">
                Debug Information:
              </Typography>
              <ul>
                <li>React: Working ✓</li>
                <li>Material-UI: Working ✓</li>
                <li>Theme: Applied ✓</li>
                <li>Error Boundary: Active ✓</li>
              </ul>
            </Box>
          </Paper>
        </Box>
      </Container>
    </ThemeProvider>
  );
};

export default AppSimple;