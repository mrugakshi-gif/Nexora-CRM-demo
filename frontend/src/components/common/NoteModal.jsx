import React, { useState } from 'react';
import Modal from './Modal';
import FormInput from './FormInput';
import Button from './Button';
import { activityService } from '../../services/crmService';

export default function NoteModal({ isOpen, onClose, companyId, customerId, salesRepId, onSaved }) {
  const [subject, setSubject] = useState('');
  const [description, setDescription] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!subject.trim()) {
      setError('Subject is required');
      return;
    }

    if (!salesRepId) {
      setError('Cannot save note: This record has no assigned sales representative.');
      return;
    }

    setIsSubmitting(true);
    setError('');

    const today = new Date().toISOString().substring(0, 10);

    const payload = {
      activity_type: 'Note',
      subject: subject.trim(),
      description: description.trim() || null,
      activity_date: today,
      due_date: today,
      status: 'Completed',
      priority: 'Normal',
      company_id: companyId || null,
      customer_id: customerId || null,
      contact_id: null,
      lead_id: null,
      opportunity_id: null,
      sales_rep_id: salesRepId
    };

    try {
      await activityService.createActivity(payload);
      setSubject('');
      setDescription('');
      onSaved();
      onClose();
    } catch (err) {
      console.error('Failed to save note:', err);
      setError('Failed to save note. Please try again.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="New Note">
      <form onSubmit={handleSubmit}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          {error && (
            <div style={{ color: 'var(--danger)', fontSize: '13px', padding: '10px', background: 'rgba(217, 83, 79, 0.1)', borderRadius: '6px' }}>
              {error}
            </div>
          )}

          <FormInput
            label="Note Subject *"
            value={subject}
            onChange={(e) => setSubject(e.target.value)}
            placeholder="e.g. Check-in call summary"
            disabled={isSubmitting}
            autoFocus
          />

          <div className="form-group">
            <label className="form-label">Note Details</label>
            <textarea
              className="form-input"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Enter note details here..."
              rows={5}
              disabled={isSubmitting}
              style={{ width: '100%', resize: 'vertical' }}
            />
          </div>

          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '12px', marginTop: '8px' }}>
            <Button
              variant="secondary"
              onClick={onClose}
              disabled={isSubmitting}
              type="button"
            >
              Cancel
            </Button>
            <Button
              variant="primary"
              type="submit"
              disabled={isSubmitting}
            >
              {isSubmitting ? 'Saving...' : 'Save Note'}
            </Button>
          </div>
        </div>
      </form>
    </Modal>
  );
}
