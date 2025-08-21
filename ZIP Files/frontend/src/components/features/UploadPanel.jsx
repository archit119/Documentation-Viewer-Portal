import React from 'react';
import Button from '../ui/Button';

export default function UploadPanel({ onUpload }) {
  return (
    <div className="bg-white rounded-lg shadow p-6 mb-6">
      <h2 className="text-xl font-semibold mb-4">Upload Documents</h2>
      <input type="file" multiple className="mb-4" />
      <Button onClick={onUpload}>Upload</Button>
    </div>
  );
}