import React from 'react';
export default function ToggleSwitch({ isOn, handleToggle }) {
  return (
    <div
      onClick={handleToggle}
      className={`w-12 h-6 flex items-center bg-gray-300 rounded-full p-1 cursor-pointer ${
        isOn ? 'bg-primary' : ''
      }`}
    >
      <div
        className={`bg-white w-4 h-4 rounded-full shadow transform duration-300 ease-in-out ${
          isOn ? 'translate-x-6' : ''
        }`}
      />
    </div>
  );
}