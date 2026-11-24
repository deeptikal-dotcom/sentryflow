import type { LucideIcon } from 'lucide-react';

interface Props {
  title: string;
  value: string | number;
  subtitle?: string;
  icon: LucideIcon;
  color?: string;
}

export default function StatCard({ title, value, subtitle, icon: Icon, color = '#2DD4BF' }: Props) {
  return (
    <div
      className="rounded-xl p-5 border border-white/10"
      style={{ backgroundColor: '#0F1A2E' }}
    >
      <div className="flex items-center justify-between mb-3">
        <span className="text-sm" style={{ color: '#94A3B8' }}>{title}</span>
        <div className="p-2 rounded-lg" style={{ backgroundColor: `${color}15` }}>
          <Icon size={18} style={{ color }} />
        </div>
      </div>
      <div className="text-2xl font-bold" style={{ color }}>{value}</div>
      {subtitle && (
        <p className="text-xs mt-1" style={{ color: '#64748B' }}>{subtitle}</p>
      )}
    </div>
  );
}
