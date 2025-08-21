import React from 'react';
import LoginForm from '../components/features/LoginForm';

export default function LoginPage() {
  const handleSubmit = e => {
    e.preventDefault();
    alert('Logged in');
  };
  return <LoginForm onSubmit={handleSubmit} />;
}