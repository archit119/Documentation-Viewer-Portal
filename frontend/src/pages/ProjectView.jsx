import React from 'react';
import { useParams } from 'react-router-dom';

export default function ProjectView() {
  const { id } = useParams();
  return <div className="text-center text-xl">Viewing project {id}</div>;
}