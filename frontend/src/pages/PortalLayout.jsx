import React from 'react';
import { Routes, Route, Link } from 'react-router-dom';
import ToggleSwitch from '../components/ui/ToggleSwitch';
import HomePage from './HomePage';
import AdminDashboard from './AdminDashboard';

export default function PortalLayout({ isAdmin, setIsAdmin }) {
  return (
    <div className="min-h-screen flex flex-col">
      <header className="flex justify-between items-center p-4 bg-white shadow">
        <nav>
          <Link to="/main" className="text-primary font-semibold mr-4">
            Home
          </Link>
          {isAdmin && (
            <Link to="/main/admin" className="text-primary font-semibold">
              Admin
            </Link>
          )}
        </nav>
        <div className="flex items-center space-x-2">
          <ToggleSwitch
            isOn={isAdmin}
            handleToggle={() => setIsAdmin(prev => !prev)}
          />
          <span>{isAdmin ? 'Admin' : 'User'}</span>
        </div>
      </header>
      <main className="flex-1 p-6">
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="admin" element={<AdminDashboard />} />
        </Routes>
      </main>
    </div>
  );
}