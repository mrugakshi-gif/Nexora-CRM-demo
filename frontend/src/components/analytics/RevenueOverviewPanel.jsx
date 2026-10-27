import React, { useState, useMemo } from 'react';
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer
} from 'recharts';
import Icon from '../common/Icon';

const formatINR = (val) => {
  if (val === 0 || !val) return '₹0';
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    maximumFractionDigits: 0
  }).format(val);
};

const formatMonthLabel = (monthStr) => {
  if (!monthStr) return '';
  const parts = monthStr.split('-');
  if (parts.length < 2) return monthStr;
  const year = parseInt(parts[0], 10);
  const month = parseInt(parts[1], 10) - 1;
  const date = new Date(year, month, 1);
  return date.toLocaleDateString('en-US', { month: 'short', year: '2-digit' });
};

const formatTooltipMonth = (monthStr) => {
  if (!monthStr) return '';
  const parts = monthStr.split('-');
  if (parts.length < 2) return monthStr;
  const year = parseInt(parts[0], 10);
  const month = parseInt(parts[1], 10) - 1;
  const date = new Date(year, month, 1);
  return date.toLocaleDateString('en-US', { month: 'long', year: 'numeric' });
};

const formatYAxisTick = (val) => {
  if (val === 0 || !val) return '₹0';
  if (val >= 100000) return `₹${(val / 100000).toFixed(1)}L`;
  if (val >= 1000) return `₹${(val / 1000).toFixed(0)}k`;
  return `₹${val}`;
};

const CustomTooltip = ({ active, payload, label }) => {
  if (active && payload && payload.length) {
    const val = payload[0].value || 0;
    return (
      <div style={{
        background: '#fffdfa',
        border: '1px solid var(--border)',
        padding: '10px 14px',
        borderRadius: '8px',
        boxShadow: '0 4px 16px rgba(0,0,0,0.08)'
      }}>
        <div style={{ fontSize: '12px', fontWeight: 600, color: 'var(--ink-mute)', marginBottom: '4px' }}>
          {formatTooltipMonth(label)}
        </div>
        <div style={{ fontSize: '15px', fontWeight: 700, color: 'var(--brown)' }}>
          {formatINR(val)}
        </div>
      </div>
    );
  }
  return null;
};

export default function RevenueOverviewPanel({ data = [], loading = false, error = false }) {
  const [periodFilter, setPeriodFilter] = useState('12m');

  // Filter data based on selected range
  const chartData = useMemo(() => {
    if (!data || data.length === 0) return [];
    
    // Sort array by month ascending
    const sorted = [...data].sort((a, b) => (a.month || '').localeCompare(b.month || ''));

    if (periodFilter === '6m') return sorted.slice(-6);
    if (periodFilter === '12m') return sorted.slice(-12);
    return sorted; // 'all'
  }, [data, periodFilter]);

  // Total revenue for the selected period
  const totalRevenue = useMemo(() => {
    return chartData.reduce((sum, item) => sum + (item.revenue_inr || item.revenue || 0), 0);
  }, [chartData]);

  // Month-over-month trend calculation for the last 2 months in selected series
  const trend = useMemo(() => {
    if (chartData.length < 2) return null;
    const current = chartData[chartData.length - 1].revenue_inr || chartData[chartData.length - 1].revenue || 0;
    const previous = chartData[chartData.length - 2].revenue_inr || chartData[chartData.length - 2].revenue || 0;
    if (previous === 0) return null;
    const pct = ((current - previous) / previous) * 100;
    return { pct, current, previous };
  }, [chartData]);

  return (
    <div className="card" style={{ padding: '24px 32px' }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '20px', flexWrap: 'wrap', gap: '12px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <Icon name="trending-up" size={28} color="var(--accent-primary)" stroke={2} />
          <div>
            <h2 className="section-title" style={{ fontSize: '22px', marginBottom: '4px', color: 'var(--heading-primary)' }}>Revenue Overview</h2>
            <p style={{ color: 'var(--ink-mute)', fontSize: '14px', margin: 0 }}>Customer transaction revenue over time</p>
          </div>
        </div>

        {/* Period Selector Toggle */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '2px', background: 'var(--bg-subtle)', border: '1px solid var(--border-soft)', borderRadius: '8px', padding: '3px', boxShadow: 'var(--clay-recessed)' }}>
          {[
            { id: '6m', label: '6 Months' },
            { id: '12m', label: '12 Months' },
            { id: 'all', label: 'All Time' }
          ].map(p => (
            <button
              key={p.id}
              type="button"
              onClick={() => setPeriodFilter(p.id)}
              style={{
                padding: '5px 12px', border: 'none', borderRadius: '6px', cursor: 'pointer',
                fontSize: '12px', fontWeight: 600, transition: 'all 0.15s ease',
                background: periodFilter === p.id ? 'var(--accent-primary)' : 'transparent',
                color: periodFilter === p.id ? '#ffffff' : 'var(--ink-soft)',
                boxShadow: periodFilter === p.id ? 'var(--clay-shadow-sm)' : 'none'
              }}
            >
              {p.label}
            </button>
          ))}
        </div>
      </div>

      {error ? (
        <div style={{ padding: '40px 20px', textAlign: 'center', background: 'var(--bg-subtle)', borderRadius: '8px', border: '1px dashed var(--border)' }}>
          <p style={{ color: 'var(--danger)', fontSize: '14px', fontWeight: 500, margin: 0 }}>Unable to load revenue data.</p>
        </div>
      ) : loading ? (
        <div style={{ padding: '50px 20px', textAlign: 'center', color: 'var(--ink-mute)', fontSize: '14px' }}>
          Loading revenue overview...
        </div>
      ) : chartData.length === 0 ? (
        <div style={{ padding: '40px 20px', textAlign: 'center', background: 'var(--bg-subtle)', borderRadius: '8px', border: '1px dashed var(--border)' }}>
          <p style={{ color: 'var(--ink-mute)', fontSize: '14px', margin: 0 }}>No revenue data available for this period.</p>
        </div>
      ) : (
        <div>
          {/* Primary KPI Header */}
          <div style={{ marginBottom: '24px', display: 'flex', alignItems: 'flex-end', gap: '16px', flexWrap: 'wrap' }}>
            <div>
              <div style={{ fontSize: '12px', fontWeight: 600, color: 'var(--ink-mute)', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '4px' }}>
                Total Revenue ({periodFilter === '6m' ? '6 Months' : periodFilter === '12m' ? '12 Months' : 'All Time'})
              </div>
              <div style={{ fontSize: '32px', fontWeight: 700, color: 'var(--heading-primary)', lineHeight: 1 }}>
                {formatINR(totalRevenue)}
              </div>
            </div>

            {trend && (
              <div style={{
                display: 'inline-flex', alignItems: 'center', gap: '6px',
                padding: '6px 12px', borderRadius: '20px',
                background: trend.pct >= 0 ? 'rgba(34, 197, 94, 0.1)' : 'rgba(239, 68, 68, 0.1)',
                color: trend.pct >= 0 ? 'var(--success)' : 'var(--danger)',
                fontSize: '13px', fontWeight: 600
              }}>
                <Icon name={trend.pct >= 0 ? 'trending-up' : 'trending-down'} size={15} />
                {Math.abs(trend.pct).toFixed(1)}% {trend.pct >= 0 ? 'increase' : 'decrease'} vs prior month
              </div>
            )}
          </div>

          {/* Chart Container */}
          <div style={{ width: '100%', height: '260px' }}>
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={chartData} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
                <defs>
                  <linearGradient id="revenueGradient" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="var(--accent-primary)" stopOpacity={0.2} />
                    <stop offset="95%" stopColor="var(--accent-primary)" stopOpacity={0.0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="var(--border-light)" />
                <XAxis
                  dataKey="month"
                  axisLine={false}
                  tickLine={false}
                  tick={{ fontSize: 12, fill: 'var(--ink-soft)' }}
                  tickFormatter={formatMonthLabel}
                  minTickGap={20}
                  interval={periodFilter === 'all' ? 'preserveStartEnd' : 0}
                  dy={10}
                />
                <YAxis
                  axisLine={false}
                  tickLine={false}
                  tick={{ fontSize: 12, fill: 'var(--ink-soft)' }}
                  tickFormatter={formatYAxisTick}
                  dx={-10}
                />
                <Tooltip
                  content={<CustomTooltip />}
                  cursor={{ stroke: 'var(--border)', strokeWidth: 1, strokeDasharray: '4 4' }}
                />
                <Area
                  type="monotone"
                  dataKey="revenue_inr"
                  stroke="var(--brown)"
                  strokeWidth={3}
                  fillOpacity={1}
                  fill="url(#revenueGradient)"
                  activeDot={{ r: 6, fill: 'var(--brown)', stroke: '#ffffff', strokeWidth: 2 }}
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}
    </div>
  );
}
