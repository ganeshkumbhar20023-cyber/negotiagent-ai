/**
 * NegotiAgent AI - Main Server Entry Point
 * Educational simulation for MIDC-related procurement scenarios.
 */

const express = require('express');
const path = require('path');
require('dotenv').config();

const app = express();
const PORT = process.env.PORT || 3000;

// Middleware: parse incoming JSON requests
app.use(express.json());

// Middleware: serve static assets (HTML, CSS, JS) from the "public" folder
app.use(express.static(path.join(__dirname, 'public')));

// API Health Check Route: allows verifying server status
app.get('/api/health', (req, res) => {
  res.json({
    status: 'online',
    system: 'NegotiAgent AI',
    purpose: 'Educational Procurement Simulation',
    timestamp: new Date().toISOString()
  });
});

// Start the HTTP server
app.listen(PORT, () => {
  console.log(`====================================================`);
  console.log(` NegotiAgent AI Server running at: http://localhost:${PORT}`);
  console.log(` Health Check API available at: http://localhost:${PORT}/api/health`);
  console.log(` Environment: Educational Simulation`);
  console.log(`====================================================`);
});