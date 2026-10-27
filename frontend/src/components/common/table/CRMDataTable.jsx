import React from 'react';
import TableLoadingSkeleton from './TableLoadingSkeleton';
import TableEmptyState from './TableEmptyState';

export default function CRMDataTable({
  headers, 
  rows,    
  loading = false,
  error = null,
  emptyTitle = 'No Data Found',
  emptyDescription = 'There is no data to display.',
  onRetry = null,
  onRowClick = null,
  rightCols = [],
  centerCols = []
}) {
  const getColClass = (idx, h) => {
    let cls = '';
    if (rightCols.includes(idx) || (h && h.align === 'right')) cls = 'td-right';
    if (centerCols.includes(idx) || (h && h.align === 'center')) cls = 'td-center';
    return cls;
  };

  const getHeaderLabel = (h) => (typeof h === 'object' ? h.label : h);

  return (
    <div className="table-wrap" style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
      {error ? (
        <TableEmptyState 
          title="Failed to load" 
          description={error} 
          actionLabel={onRetry ? "Retry" : null}
          onAction={onRetry} 
        />
      ) : loading ? (
        <table style={{ width: '100%' }}>
          <thead>
            <tr>
              {headers.map((h, i) => (
                <th key={i} className={getColClass(i, h)}>{getHeaderLabel(h)}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            <TableLoadingSkeleton rows={5} cols={headers.length} />
          </tbody>
        </table>
      ) : rows.length === 0 ? (
        <TableEmptyState 
          title={emptyTitle}
          description={emptyDescription}
        />
      ) : (
        <table>
          <thead>
            <tr>
              {headers.map((h, i) => (
                <th key={i} className={getColClass(i, h)}>{getHeaderLabel(h)}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row, rIdx) => (
              <tr key={rIdx} onClick={() => onRowClick && onRowClick(row, rIdx)}>
                {row.map((cell, cIdx) => (
                  <td key={cIdx} className={getColClass(cIdx, headers[cIdx])}>
                    {cell}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
