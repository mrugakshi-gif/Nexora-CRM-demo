import React from 'react';

export default function DataTable({ headers, rows, rightCols = [], onRowClick }) {
  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            {headers.map((h, i) => (
              <th key={i} className={rightCols.includes(i) ? 'td-right' : ''}>{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, rIdx) => (
            <tr key={rIdx} onClick={() => onRowClick && onRowClick(row, rIdx)}>
              {row.map((cell, cIdx) => (
                <td key={cIdx} className={rightCols.includes(cIdx) ? 'td-right' : ''}>
                  {cell}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
