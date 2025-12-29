import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.jsx'
import Demo from './Demo.jsx'
import './index.css'

// Simple path-based routing
const isDemo = window.location.pathname === '/demo'

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    {isDemo ? <Demo /> : <App />}
  </React.StrictMode>,
)
