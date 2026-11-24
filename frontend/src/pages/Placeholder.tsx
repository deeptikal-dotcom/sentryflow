import { Construction } from 'lucide-react';

export default function Placeholder({ title }: { title: string }) {
  return (
    <div className="p-8">
      <h2 className="text-2xl font-bold mb-2">{title}</h2>
      <div
        className="rounded-xl border border-white/10 p-12 text-center mt-8"
        style={{ backgroundColor: '#0F1A2E' }}
      >
        <Construction size={48} className="mx-auto mb-4" style={{ color: '#64748B' }} />
        <p className="font-medium" style={{ color: '#94A3B8' }}>Under Construction</p>
        <p className="text-sm mt-1" style={{ color: '#475569' }}>This page is being implemented</p>
      </div>
    </div>
  );
}
