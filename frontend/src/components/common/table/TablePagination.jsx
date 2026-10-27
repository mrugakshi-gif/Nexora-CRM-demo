import React from 'react';

export default function TablePagination({ page, totalPages, totalRecords, onPrev, onNext }) {
  if (totalRecords === 0) return null;
  return (
    <div className="pagination">
      <div className="page-info">
        Showing page {page} of {totalPages} ({totalRecords} total)
      </div>
      <div className="page-btns">
        <button 
          className="page-btn" 
          disabled={page <= 1} 
          onClick={onPrev}
        >
          Previous
        </button>
        <button 
          className="page-btn" 
          disabled={page >= totalPages} 
          onClick={onNext}
        >
          Next
        </button>
      </div>
    </div>
  );
}
