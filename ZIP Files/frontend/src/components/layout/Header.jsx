import React from 'react';

export default function Header() {
  return (
    <header className="flex items-center justify-between bg-white p-4 shadow">
      <h1 className="text-2xl font-semibold text-primary">Documentation Portal</h1>
      <button className="px-4 py-2 bg-secondary text-white rounded hover:opacity-90">Logout</button>
    </header>
  );
}