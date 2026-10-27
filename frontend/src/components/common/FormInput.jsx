import React from 'react';

export default function FormInput({ label, type = 'text', value, onChange, placeholder, required = false, error }) {
  return (
    <div className="field">
      <label>{label}{required ? ' *' : ''}</label>
      {type === 'textarea' ? (
        <textarea 
          rows="3" 
          value={value} 
          onChange={onChange} 
          placeholder={placeholder} 
          className={error ? 'invalid' : ''}
        />
      ) : (
        <input 
          type={type} 
          value={value} 
          onChange={onChange} 
          placeholder={placeholder} 
          className={error ? 'invalid' : ''}
        />
      )}
      {error && <div className="err">{error}</div>}
    </div>
  );
}
