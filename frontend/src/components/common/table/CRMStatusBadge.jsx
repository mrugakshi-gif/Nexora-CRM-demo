import React from 'react';
import Badge from '../Badge';

export default function CRMStatusBadge({ status, className = '' }) {
  if (!status) return <span className={className}>-</span>;

  let variant = 'neutral';
  const s = status.toLowerCase();
  
  if (['active customer', 'won', 'active', 'completed', 'resolved', 'closed - won', 'success'].includes(s)) {
    variant = 'success';
  } else if (['churned customer', 'lost', 'churned', 'cancelled', 'closed - lost', 'failed'].includes(s)) {
    variant = 'danger';
  } else if (['prospect', 'open', 'in progress', 'pending', 'negotiation', 'discovery'].includes(s)) {
    variant = 'warning';
  } else if (['new', 'draft', 'qualification'].includes(s)) {
    variant = 'brand';
  }

  return <Badge text={status} kind={variant} className={className} />;
}
