import React from 'react';
import Icon from './Icon';

export default function Button({ children, variant = 'secondary', size = 'md', icon, className = '', disabled = false, ...props }) {
  const variantClass = {
    primary: 'btn-primary',
    secondary: 'btn-secondary',
    ghost: 'btn-ghost',
    danger: 'btn-danger',
    success: 'btn-success',
  }[variant] || 'btn-secondary';

  const sizeClass = (size === 'sm' || size === 'small') ? 'btn-sm' : '';
  const isSmall = size === 'sm' || size === 'small';

  return (
    <button 
      className={`btn ${variantClass} ${sizeClass} ${className}`} 
      disabled={disabled}
      {...props}
    >
      {icon && <Icon name={icon} size={isSmall ? 13 : 15} color={variant === 'primary' || variant === 'danger' || variant === 'success' ? '#ffffff' : (variant === 'secondary' ? 'var(--accent-primary)' : 'currentColor')} />}
      {children}
    </button>
  );
}
