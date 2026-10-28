import { FormEvent, useState } from 'react'
import { Plane } from 'lucide-react'
import { useAuth } from '../lib/auth'
import { isEmail } from '../lib/format'
import { Field } from '../components/ui'

export default function Login() {
  const { login } = useAuth()
  const [email, setEmail] = useState(''); const [password, setPassword] = useState('')
  const [errs, setErrs] = useState<{ email?: string; password?: string }>({}); const [err, setErr] = useState(''); const [busy, setBusy] = useState(false)
  const submit = async (e: FormEvent) => {
    e.preventDefault()
    const v: typeof errs = {}
    if (!isEmail(email)) v.email = 'Enter a valid email address'
    if (!password) v.password = 'Password is required'
    setErrs(v); setErr('')
    if (Object.keys(v).length) return
    setBusy(true)
    try { await login(email, password) } catch (x) { setErr(x instanceof Error ? x.message : 'Login failed') } finally { setBusy(false) }
  }
  return (
    <div className="flex min-h-screen items-center justify-center bg-navy-900 p-4">
      <form onSubmit={submit} noValidate className="card w-full max-w-sm space-y-4">
        <div className="flex items-center gap-2 text-xl font-bold"><Plane className="h-6 w-6 text-teal-500" />EstatePilot AI</div>
        <Field label="Email" htmlFor="email" error={errs.email}><input id="email" type="email" className="input" value={email} onChange={(e) => setEmail(e.target.value)} autoComplete="username" /></Field>
        <Field label="Password" htmlFor="password" error={errs.password}><input id="password" type="password" className="input" value={password} onChange={(e) => setPassword(e.target.value)} autoComplete="current-password" /></Field>
        {err && <div role="alert" className="rounded-lg bg-red-50 p-2 text-sm text-red-700 dark:bg-red-950 dark:text-red-300">{err}</div>}
        <button className="btn-primary w-full" disabled={busy}>{busy ? 'Signing in…' : 'Sign in'}</button>
        <div className="rounded-lg bg-slate-100 p-3 text-xs text-slate-600 dark:bg-slate-800 dark:text-slate-300">
          <p className="font-medium">Demo credentials (seeded data only)</p>
          <p>admin@demo.com / manager@demo.com / agent@demo.com / analyst@demo.com</p>
          <p>Password: <code>Passw0rd!demo</code></p>
          <button type="button" className="mt-2 text-teal-600 underline" onClick={() => { setEmail('admin@demo.com'); setPassword('Passw0rd!demo') }}>Fill admin demo login</button>
        </div>
      </form>
    </div>
  )
}
