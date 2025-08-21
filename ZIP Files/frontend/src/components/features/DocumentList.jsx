import React from 'react';
import Card from '../ui/Card';

export default function DocumentList({ docs, onSelect }) {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
      {docs.map(doc => (
        <Card key={doc.id} onClick={() => onSelect(doc)}>
          <h3 className="font-semibold text-lg">{doc.title}</h3>
          <p className="text-gray-600 text-sm mt-1">Uploaded on {doc.date}</p>
        </Card>
      ))}
    </div>
  );
}