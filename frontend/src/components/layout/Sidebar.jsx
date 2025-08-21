import React from 'react';
import { Link, useLocation } from 'react-router-dom';

export default function Sidebar() {
  const { pathname } = useLocation();
  const links = [
    { to: '/', label: 'Home' },
    { to: '/admin', label: 'Admin' }
  ];
  return (
    <aside className="w-64 bg-white shadow-lg">
      <div className="p-6 font-bold text-xl text-primary">Mashreq Docs</div>
      <nav className="flex flex-col">
        {links.map(link => (
          <Link
            key={link.to}
            to={link.to}
            className={`px-6 py-3 hover:bg-gray-100 ${pathname === link.to ? 'bg-gray-200' : ''}`}
          >
            {link.label}
          </Link>
        ))}
      </nav>
    </aside>
  );
}