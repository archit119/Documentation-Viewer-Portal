import React, { useState } from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import LandingPage from './pages/LandingPage';
import PortalLayout from './pages/PortalLayout';

export default function App() {
  const [isAdmin, setIsAdmin] = useState(false);
  return (
    <Router>
      <Routes>
        <Route
          path="/"
          element={<LandingPage isAdmin={isAdmin} setIsAdmin={setIsAdmin} />}
        />
        <Route
          path="/main/*"
          element={<PortalLayout isAdmin={isAdmin} setIsAdmin={setIsAdmin} />}
        />
      </Routes>
    </Router>
  );
}
