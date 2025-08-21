import React from 'react';

export default function Input(props) {
  return (
    <input {...props} className="w-full px-3 py-2 border rounded focus:outline-none focus:ring-2 focus:ring-primary" />
  );
}