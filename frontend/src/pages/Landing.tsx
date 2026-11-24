import { Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import { Brain, FileSearch, GitCompare, Layers, Lock, ShieldCheck, Sparkles, UserCheck } from 'lucide-react'

const features = [
  { icon: Layers, title: 'Eight detection layers', text: 'Exact, token, lexical, AST, TF-IDF, winnowing, structural and transformation analysis, combined with configurable weights.' },
  { icon: GitCompare, title: 'Side-by-side evidence', text: 'Matched blocks highlighted in a Monaco code view, with line numbers and one-click navigation between matches.' },
  { icon: Brain, title: 'Explainable results', text: 'Every score comes with plain-language reasons: renamed variables, reformatting, reordered functions and more.' },
  { icon: UserCheck, title: 'Faculty stays in control', text: 'Similarity is not a verdict. Cases are reviewed, annotated and overridden by a human before any decision.' },
  { icon: Lock, title: 'Safe by design', text: 'Uploaded code is never executed. ZIPs are scanned for traversal and bombs; access is role-based and audited.' },
  { icon: FileSearch, title: 'Reports and analytics', text: 'PDF and CSV reports, heat-maps and dashboards for administrators, faculty and students.' },
]

export default function Landing() {
  return (
    <div className="min-h-screen bg-white dark:bg-navy-950">
      <header className="absolute inset-x-0 top-0 z-10 mx-auto flex max-w-6xl items-center justify-between px-5 py-5">
        <div className="flex items-center gap-2 font-bold text-white"><div className="rounded-lg bg-brand-500 p-1.5"><GitCompare className="h-5 w-5" /></div>CodeIntegrity</div>
        <div className="flex gap-2">
          <Link to="/login" className="rounded-xl px-4 py-2 text-sm font-medium text-white hover:bg-white/10">Sign in</Link>
          <Link to="/register" className="rounded-xl bg-white px-4 py-2 text-sm font-semibold text-brand-800">Get started</Link>
        </div>
      </header>
      <section className="bg-gradient-to-br from-navy-950 via-navy-900 to-brand-800 px-5 pb-24 pt-32 text-white">
        <div className="mx-auto max-w-4xl text-center">
          <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }}>
            <span className="inline-flex items-center gap-1.5 rounded-full bg-white/10 px-3 py-1 text-xs font-medium"><Sparkles className="h-3.5 w-3.5" />Academic integrity platform</span>
            <h1 className="mt-5 text-4xl font-extrabold tracking-tight sm:text-6xl">Smart Code <span className="bg-gradient-to-r from-brand-300 to-sky-300 bg-clip-text text-transparent">Plagiarism Detection</span></h1>
            <p className="mx-auto mt-5 max-w-2xl text-base text-navy-100 sm:text-lg">Compare student programs in Python, Java, C, C++, JavaScript and TypeScript. See through renamed variables, reformatting and reordering — and keep faculty in the decision seat.</p>
            <div className="mt-8 flex flex-col justify-center gap-3 sm:flex-row">
              <Link to="/register" className="rounded-xl bg-gradient-to-r from-brand-500 to-brand-600 px-6 py-3 font-semibold shadow-lg">Create account</Link>
              <Link to="/login" className="rounded-xl border border-white/30 px-6 py-3 font-semibold hover:bg-white/10">Faculty & admin sign in</Link>
            </div>
          </motion.div>
        </div>
      </section>
      <section className="mx-auto max-w-6xl px-5 py-20">
        <h2 className="text-center text-3xl font-bold text-slate-900 dark:text-white">Built for fair, defensible review</h2>
        <div className="mt-10 grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
          {features.map((f, i) => (
            <motion.div key={f.title} initial={{ opacity: 0, y: 16 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} transition={{ delay: i * 0.05 }} className="card p-6">
              <div className="mb-3 inline-flex rounded-xl bg-brand-50 p-2.5 text-brand-600 dark:bg-brand-900/30"><f.icon className="h-5 w-5" /></div>
              <h3 className="font-semibold text-slate-900 dark:text-white">{f.title}</h3>
              <p className="mt-1.5 text-sm text-slate-600 dark:text-slate-400">{f.text}</p>
            </motion.div>
          ))}
        </div>
      </section>
      <section className="bg-slate-50 px-5 py-16 dark:bg-navy-900">
        <div className="mx-auto flex max-w-3xl items-start gap-4">
          <ShieldCheck className="mt-1 h-8 w-8 shrink-0 text-emerald-500" />
          <p className="text-sm text-slate-600 dark:text-slate-300"><strong className="text-slate-900 dark:text-white">Similarity is not confirmed plagiarism.</strong> Common algorithms, starter code and independent solutions can look alike. This system produces evidence and explanations; only a faculty member can mark a case as confirmed.</p>
        </div>
      </section>
      <footer className="px-5 py-8 text-center text-xs text-slate-500">© {new Date().getFullYear()} Smart Code Plagiarism Detection System</footer>
    </div>
  )
}
