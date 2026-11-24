import { Bar, BarChart, CartesianGrid, Cell, Legend, Line, LineChart, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { LANG_LABELS } from '../utils/format'
import { useTheme } from '../contexts/ThemeContext'

const PALETTE = ['#4f46e5', '#0ea5e9', '#10b981', '#f59e0b', '#ec4899', '#8b5cf6']

function useAxis() {
  const { dark } = useTheme()
  return { tick: { fill: dark ? '#94a3b8' : '#64748b', fontSize: 12 }, grid: dark ? '#1b2c4d' : '#e2e8f0', tip: { background: dark ? '#0f1b36' : '#fff', border: `1px solid ${dark ? '#243b66' : '#e2e8f0'}`, borderRadius: 12, fontSize: 12 } }
}

export function LanguagePie({ data }: { data: { language: string; count: number }[] }) {
  const a = useAxis()
  if (!data.length) return <p className="py-10 text-center text-sm text-slate-500">No submissions in this period.</p>
  return (
    <div className="h-64" role="img" aria-label="Programming language distribution">
      <ResponsiveContainer>
        <PieChart>
          <Pie data={data.map((d) => ({ name: LANG_LABELS[d.language] ?? d.language, value: d.count }))} dataKey="value" innerRadius="55%" outerRadius="80%" paddingAngle={3}>
            {data.map((_, i) => <Cell key={i} fill={PALETTE[i % PALETTE.length]} />)}
          </Pie>
          <Tooltip contentStyle={a.tip} />
          <Legend wrapperStyle={{ fontSize: 12 }} />
        </PieChart>
      </ResponsiveContainer>
    </div>
  )
}

export function MonthlyLine({ data }: { data: { month: string; count: number }[] }) {
  const a = useAxis()
  if (!data.length) return <p className="py-10 text-center text-sm text-slate-500">No submissions in this period.</p>
  return (
    <div className="h-64" role="img" aria-label="Monthly submission trend">
      <ResponsiveContainer>
        <LineChart data={data} margin={{ left: -20, right: 8, top: 8 }}>
          <CartesianGrid stroke={a.grid} strokeDasharray="3 3" />
          <XAxis dataKey="month" tick={a.tick} /><YAxis allowDecimals={false} tick={a.tick} />
          <Tooltip contentStyle={a.tip} />
          <Line type="monotone" dataKey="count" name="Submissions" stroke="#4f46e5" strokeWidth={3} dot={{ r: 4 }} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}

export function AssignmentBars({ data }: { data: { title: string; average_similarity: number; flagged: number }[] }) {
  const a = useAxis()
  if (!data.length) return <p className="py-10 text-center text-sm text-slate-500">No analysed assignments yet.</p>
  const rows = data.map((d) => ({ name: d.title.length > 18 ? d.title.slice(0, 17) + '…' : d.title, 'Avg similarity %': Math.round(d.average_similarity * 100), Flagged: d.flagged }))
  return (
    <div className="h-72" role="img" aria-label="Assignment-wise plagiarism statistics">
      <ResponsiveContainer>
        <BarChart data={rows} margin={{ left: -20, right: 8, top: 8 }}>
          <CartesianGrid stroke={a.grid} strokeDasharray="3 3" />
          <XAxis dataKey="name" tick={a.tick} interval={0} angle={-20} textAnchor="end" height={56} /><YAxis allowDecimals={false} tick={a.tick} />
          <Tooltip contentStyle={a.tip} /><Legend wrapperStyle={{ fontSize: 12 }} />
          <Bar dataKey="Avg similarity %" fill="#6366f1" radius={[6, 6, 0, 0]} />
          <Bar dataKey="Flagged" fill="#ef4444" radius={[6, 6, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}

export function StatusPie({ data }: { data: { status: string; count: number }[] }) {
  const a = useAxis()
  if (!data.length) return <p className="py-10 text-center text-sm text-slate-500">No submissions yet.</p>
  return (
    <div className="h-56">
      <ResponsiveContainer>
        <PieChart>
          <Pie data={data.map((d) => ({ name: d.status, value: d.count }))} dataKey="value" innerRadius="55%" outerRadius="80%">{data.map((_, i) => <Cell key={i} fill={PALETTE[i % PALETTE.length]} />)}</Pie>
          <Tooltip contentStyle={a.tip} /><Legend wrapperStyle={{ fontSize: 12 }} />
        </PieChart>
      </ResponsiveContainer>
    </div>
  )
}
