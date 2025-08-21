import React from 'react';
export default function Button({ children, ...props }) {
  return (
    <button
      {...props}
      className="px-6 py-3 bg-white text-secondary font-semibold rounded-full shadow-lg hover:opacity-90"
    >
      {children}
    </button>
  );
}