import React from 'react';
import Button from '../ui/Button';
import Input from '../ui/Input';

export default function LoginForm({ onSubmit }) {
  return (
    <form onSubmit={onSubmit} className="max-w-md mx-auto bg-white p-8 rounded-lg shadow">
      <h2 className="text-2xl font-semibold mb-6 text-center">Admin Login</h2>
      <label className="block mb-2">Email</label>
      <Input type="email" placeholder="you@company.com" required />
      <label className="block mt-4 mb-2">Password</label>
      <Input type="password" placeholder="••••••••" required />
      <Button type="submit" className="mt-6 w-full">Login</Button>
    </form>
  );
}