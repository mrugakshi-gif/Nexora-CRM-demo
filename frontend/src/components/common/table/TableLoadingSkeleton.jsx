import React from 'react';

export default function TableLoadingSkeleton({ rows = 5, cols = 5 }) {
  return (
    <>
      {Array.from({ length: rows }).map((_, rIdx) => (
        <tr key={rIdx}>
          {Array.from({ length: cols }).map((_, cIdx) => (
            <td key={cIdx}>
              <div 
                className="skeleton" 
                style={{ 
                  height: '16px', 
                  width: cIdx === 0 ? '60%' : (cIdx === cols - 1 ? '40%' : '80%') 
                }}
              ></div>
            </td>
          ))}
        </tr>
      ))}
    </>
  );
}
