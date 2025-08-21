import React from 'react';

export default function Card({ children, ...props }) {
  return (
    <div {...props} className="bg-white rounded-lg shadow p-4 cursor-pointer hover:shadow-md">
      {children}
    </div>
  );
}
