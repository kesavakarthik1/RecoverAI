import { useNavigate } from 'react-router-dom'

const features = [
  {
    icon: '🔍',
    title: 'Detect Revenue at Risk',
    desc: 'Automatically identifies failed payments, abandoned checkouts, failed subscriptions, and overdue invoices from your transaction data.',
  },
  {
    icon: '🧠',
    title: 'AI-Assisted Diagnosis',
    desc: 'Categorizes failure reasons, scores recovery priority, and generates structured recovery recommendations with explainable evidence.',
  },
  {
    icon: '🛡',
    title: 'Deterministic Policy Engine',
    desc: 'Every action is validated against configurable policy rules — retry limits, consent checks, fraud blocks, and communication limits. The AI cannot override a blocked action.',
  },
  {
    icon: '⚡',
    title: 'Simulated Recovery Actions',
    desc: 'Executes retry, reminder, authentication request, escalation, and human-review workflows safely in simulation mode with full audit logging.',
  },
  {
    icon: '📊',
    title: 'Measurable Outcomes',
    desc: 'Calculates 20 evaluation metrics including recovery rate, precision, recall, false-positive rate, and net simulated recovery value across three strategies.',
  },
  {
    icon: '📋',
    title: 'Append-Only Audit Trail',
    desc: 'Every decision, policy check, action, and outcome is recorded in an immutable audit log — traceable from transaction to recovery result.',
  },
]

const steps = [
  { step: '1', title: 'Import Data', desc: 'Upload a CSV or generate a 100+ record synthetic dataset with all scenario types.' },
  { step: '2', title: 'Run Recovery Agent', desc: 'The agent detects, diagnoses, and recommends actions through a structured state machine.' },
  { step: '3', title: 'Policy Checks', desc: 'Every recommendation is validated against retry limits, consent rules, and fraud blocks before execution.' },
  { step: '4', title: 'Measure Results', desc: 'Compare three strategies on the same dataset. Export evaluation reports with all 20 metrics.' },
]

export default function Landing() {
  const nav = useNavigate()

  return (
    <div className="min-h-screen bg-gray-950 text-white">
      {/* Header */}
      <header className="border-b border-gray-800 px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="h-9 w-9 rounded-lg bg-brand-600 flex items-center justify-center font-bold text-lg">R</div>
          <div>
            <div className="font-semibold text-white">RecoverAI</div>
            <div className="text-xs text-gray-400">Razorpay AI Buildathon</div>
          </div>
        </div>
        <button onClick={() => nav('/dashboard')} className="btn-primary text-sm">
          Open Dashboard →
        </button>
      </header>

      {/* Hero */}
      <section className="px-6 py-20 text-center max-w-4xl mx-auto">
        <div className="inline-flex items-center gap-2 rounded-full bg-brand-900/50 border border-brand-800 px-4 py-1.5 text-sm text-brand-300 mb-8">
          <span className="h-2 w-2 rounded-full bg-brand-400 animate-pulse" />
          Simulation Mode — No real payments processed
        </div>
        <h1 className="text-5xl font-bold tracking-tight mb-6">
          AI-Powered{' '}
          <span className="text-transparent bg-clip-text bg-gradient-to-r from-brand-400 to-emerald-400">
            Revenue Recovery
          </span>
        </h1>
        <p className="text-xl text-gray-400 mb-10 leading-relaxed">
          Detect failed payments, abandoned checkouts, and overdue receivables.
          Apply AI-assisted recovery with deterministic policy enforcement, full audit trails,
          and measurable outcomes — all safely simulated.
        </p>
        <div className="flex flex-wrap items-center justify-center gap-4">
          <button onClick={() => nav('/dashboard')} className="btn-primary text-base px-8 py-3">
            View Dashboard
          </button>
          <button onClick={() => nav('/import')} className="btn-secondary text-base px-8 py-3 bg-gray-800 border-gray-700 text-white hover:bg-gray-700">
            Generate Sample Data
          </button>
        </div>
      </section>

      {/* 5 questions answered */}
      <section className="px-6 py-12 max-w-4xl mx-auto">
        <h2 className="text-center text-sm font-semibold uppercase tracking-widest text-gray-500 mb-8">
          For every recovery case, RecoverAI answers
        </h2>
        <div className="grid sm:grid-cols-2 lg:grid-cols-5 gap-3">
          {[
            'Why is this revenue at risk?',
            'What action is recommended and why?',
            'Is the action allowed under policy?',
            'What happened when it was executed?',
            'How much value was recovered and how was it measured?',
          ].map((q, i) => (
            <div key={i} className="rounded-xl bg-gray-900 border border-gray-800 p-4 text-center">
              <div className="text-2xl font-bold text-brand-400 mb-2">{i + 1}</div>
              <p className="text-sm text-gray-300">{q}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Features */}
      <section className="px-6 py-16 max-w-5xl mx-auto">
        <h2 className="text-center text-2xl font-bold mb-12">Complete Recovery System</h2>
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-6">
          {features.map(f => (
            <div key={f.title} className="rounded-xl bg-gray-900 border border-gray-800 p-5">
              <div className="text-2xl mb-3">{f.icon}</div>
              <h3 className="font-semibold text-white mb-2">{f.title}</h3>
              <p className="text-sm text-gray-400 leading-relaxed">{f.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* How it works */}
      <section className="px-6 py-16 bg-gray-900/50">
        <div className="max-w-4xl mx-auto">
          <h2 className="text-center text-2xl font-bold mb-12">How It Works</h2>
          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-6">
            {steps.map(s => (
              <div key={s.step} className="text-center">
                <div className="inline-flex h-12 w-12 items-center justify-center rounded-full bg-brand-600 text-white font-bold text-lg mb-4">
                  {s.step}
                </div>
                <h3 className="font-semibold text-white mb-2">{s.title}</h3>
                <p className="text-sm text-gray-400">{s.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Tech stack */}
      <section className="px-6 py-12 max-w-4xl mx-auto text-center">
        <h2 className="text-sm font-semibold uppercase tracking-widest text-gray-500 mb-6">Built With</h2>
        <div className="flex flex-wrap justify-center gap-3">
          {['Python + FastAPI', 'React + TypeScript', 'SQLite / PostgreSQL', 'Tailwind CSS',
            'Recharts', 'scikit-learn', 'OpenRouter (optional)', 'Razorpay Test (optional)',
            'Docker', 'Alembic'].map(t => (
            <span key={t} className="rounded-lg bg-gray-800 border border-gray-700 px-3 py-1.5 text-sm text-gray-300">
              {t}
            </span>
          ))}
        </div>
      </section>

      {/* CTA */}
      <section className="px-6 py-16 text-center">
        <h2 className="text-2xl font-bold mb-4">Ready to explore?</h2>
        <p className="text-gray-400 mb-8">Generate synthetic data, run the recovery agent, and view measurable outcomes in under 60 seconds.</p>
        <button onClick={() => nav('/dashboard')} className="btn-primary text-base px-10 py-3">
          Open Dashboard →
        </button>
      </section>

      {/* Footer */}
      <footer className="border-t border-gray-800 px-6 py-6 text-center text-xs text-gray-600">
        RecoverAI — Razorpay AI Buildathon · Simulation only · No real payments processed ·
        All synthetic data is fictional and does not represent real merchants or customers.
      </footer>
    </div>
  )
}
